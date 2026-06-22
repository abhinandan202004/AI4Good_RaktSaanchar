import math
import httpx
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.modules.donors.models import Donor
from app.modules.blood_requests.models import BloodRequest, RequestStatus
from app.modules.patients.models import Patient
from app.modules.blood_bank.models import BloodBankProfile

logger = logging.getLogger(__name__)

# Blood-type compatibility map (who can donate to whom)
_COMPATIBLE: dict[str, list[str]] = {
    "O-":  ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"],
    "O+":  ["O+", "A+", "B+", "AB+"],
    "A-":  ["A-", "A+", "AB-", "AB+"],
    "A+":  ["A+", "AB+"],
    "B-":  ["B-", "B+", "AB-", "AB+"],
    "B+":  ["B+", "AB+"],
    "AB-": ["AB-", "AB+"],
    "AB+": ["AB+"],
}

_URGENCY_MAP = {"low": 0, "medium": 1, "high": 1, "critical": 2}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates geographical distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _distance_km(
    donor: Donor,
    patient_city: Optional[str],
    patient_latitude: Optional[float] = None,
    patient_longitude: Optional[float] = None,
) -> float:
    if (
        donor.latitude is not None
        and donor.longitude is not None
        and patient_latitude is not None
        and patient_longitude is not None
    ):
        return round(haversine_distance(patient_latitude, patient_longitude, donor.latitude, donor.longitude), 2)

    if not patient_city or not donor.city:
        return 100.0
    if donor.city.strip().lower() == patient_city.strip().lower():
        return 30.0
    return 150.0


def _days_since_donation(donor: Donor) -> int:
    if donor.last_donated_at is None:
        return 365
    delta = datetime.now(timezone.utc) - donor.last_donated_at
    return max(90, delta.days)


def _local_heuristic_score(
    reliability_score: float,
    response_rate: float,
    total_donations: int,
    blood_group_match: int,
    urgency_num: int,
    distance: float
) -> float:
    score = (
        blood_group_match * 0.4 +
        reliability_score * 0.2 +
        response_rate * 0.15 +
        (1 - min(distance / 500, 1.0)) * 0.1 +
        (urgency_num / 2.0) * 0.05 +
        min(total_donations / 28.0, 1.0) * 0.1
    )
    return round(score, 4)


class MlService:
    @staticmethod
    def rank_donors(
        db: Session,
        patient_blood_group: Optional[str] = None,
        urgency: Optional[str] = None,
        units_required: int = 1,
        patient_city: Optional[str] = None,
        patient_latitude: Optional[float] = None,
        patient_longitude: Optional[float] = None,
        request_id: Optional[int] = None,
        limit: int = 20,
    ) -> list[dict]:
        # 1. Resolve patient request details if request_id is provided
        if request_id is not None:
            blood_req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
            if not blood_req:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Blood request not found")
            patient_blood_group = blood_req.blood_group.value
            urgency = blood_req.urgency
            units_required = blood_req.units_required
            if blood_req.patient:
                patient_city = blood_req.patient.city
                patient_latitude = blood_req.patient.latitude
                patient_longitude = blood_req.patient.longitude
        else:
            if not patient_blood_group or not urgency:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "Either request_id or both patient_blood_group and urgency must be provided"
                )

        # 2. Fetch eligible donors (cooldown check: 90 days, available)
        cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)
        donors: List[Donor] = (
            db.query(Donor)
            .filter(
                Donor.is_available == True,
                or_(
                    Donor.last_donated_at == None,
                    Donor.last_donated_at <= cooldown_limit
                )
            )
            .all()
        )

        urgency_num = _URGENCY_MAP.get(urgency.lower(), 1)

        # 3. Build donor payload with calculated features
        donor_features = []
        for d in donors:
            donor_features.append({
                "donor_id": d.id,
                "user_id": d.user_id,
                "blood_group": d.blood_group.value,
                "city": d.city,
                "is_available": d.is_available,
                "reliability_score": d.reliability_score,
                "response_rate": d.response_rate,
                "no_show_count": d.no_show_count or 0,
                "total_donations": d.total_donations or 0,
                "days_since_last_donation": _days_since_donation(d),
                "latitude": d.latitude,
                "longitude": d.longitude
            })

        # 4. Invoke serverless Hugging Face Space API
        results = []
        hf_success = False
        try:
            payload = {
                "patient_blood_group": patient_blood_group,
                "urgency": urgency,
                "units_required": units_required,
                "patient_city": patient_city,
                "patient_latitude": patient_latitude,
                "patient_longitude": patient_longitude,
                "donors": donor_features,
                "limit": limit
            }
            resp = httpx.post(
                f"{settings.ML_SERVICE_URL}/predict/donor-ranks",
                json=payload,
                timeout=10.0
            )
            if resp.status_code == 200:
                results = resp.json()
                hf_success = True
                logger.info("✅ Hugging Face Space rank-donors successful: %d results", len(results))
        except Exception as exc:
            logger.warning("⚠️ Hugging Face Space rank-donors failed: %s. Using local fallback.", exc)

        # 5. Local Fallback Heuristic
        if not hf_success:
            results = []
            for d in donors:
                compatible_patients = _COMPATIBLE.get(d.blood_group.value, [])
                blood_group_match = 1 if patient_blood_group in compatible_patients else 0
                distance = _distance_km(d, patient_city, patient_latitude, patient_longitude)
                prob = _local_heuristic_score(
                    reliability_score=d.reliability_score,
                    response_rate=d.response_rate,
                    total_donations=d.total_donations or 0,
                    blood_group_match=blood_group_match,
                    urgency_num=urgency_num,
                    distance=distance,
                )
                engagement = round(0.7 * d.reliability_score + 0.3 * d.response_rate, 3)

                results.append({
                    "donor_id": d.id,
                    "user_id": d.user_id,
                    "blood_group": d.blood_group.value,
                    "city": d.city,
                    "is_available": d.is_available,
                    "reliability_score": d.reliability_score,
                    "response_rate": d.response_rate,
                    "total_donations": d.total_donations or 0,
                    "blood_group_match": bool(blood_group_match),
                    "distance_km": distance,
                    "engagement_score": engagement,
                    "match_probability": round(prob, 4),
                })
            results.sort(key=lambda x: x["match_probability"], reverse=True)
            results = results[:limit]

        return results

    @staticmethod
    def get_geojson_map_data(db: Session) -> dict:
        features = []

        # 1. Fetch available and eligible donors with coordinates
        cooldown_limit = datetime.now(timezone.utc) - timedelta(days=90)
        donors = db.query(Donor).filter(
            Donor.is_available == True,
            or_(
                Donor.last_donated_at == None,
                Donor.last_donated_at <= cooldown_limit
            ),
            Donor.latitude.isnot(None),
            Donor.longitude.isnot(None)
        ).all()
        for d in donors:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [d.longitude, d.latitude]
                },
                "properties": {
                    "type": "donor",
                    "donor_id": d.id,
                    "user_id": d.user_id,
                    "blood_group": d.blood_group.value,
                    "reliability_score": d.reliability_score,
                    "name": d.user.full_name if d.user else "Donor",
                    "city": d.city,
                }
            })

        # 2. Fetch active requests with patient coordinates
        active_requests = (
            db.query(BloodRequest)
            .join(Patient)
            .filter(
                BloodRequest.status.notin_([RequestStatus.fulfilled, RequestStatus.cancelled]),
                Patient.latitude.isnot(None),
                Patient.longitude.isnot(None)
            )
            .all()
        )
        for req in active_requests:
            pat = req.patient
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pat.longitude, pat.latitude]
                },
                "properties": {
                    "type": "patient",
                    "request_id": req.id,
                    "patient_id": pat.id,
                    "blood_group": req.blood_group.value,
                    "urgency": req.urgency,
                    "units_required": req.units_required,
                    "status": req.status.value,
                    "hospital_name": pat.hospital_name,
                    "name": pat.user.full_name if pat.user else "Patient",
                }
            })

        # 3. Fetch blood bank profiles with coordinates
        banks = db.query(BloodBankProfile).filter(
            BloodBankProfile.latitude.isnot(None),
            BloodBankProfile.longitude.isnot(None)
        ).all()
        for b in banks:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [b.longitude, b.latitude]
                },
                "properties": {
                    "type": "blood_bank",
                    "blood_bank_id": b.id,
                    "user_id": b.user_id,
                    "hospital_name": b.hospital_name,
                    "contact_phone": b.contact_phone,
                    "address": b.address,
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }
