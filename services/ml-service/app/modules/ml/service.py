"""
ML module — Donor Ranking Service
===================================
Loads the pre-trained XGBoost model from the .pkl file at startup and exposes
inference logic. The model predicts the probability that a donor will successfully
donate for a given blood request (binary classifier: target = 0/1).

Model features (same order as training):
  blood_group_match, eligible_to_donate, reliability_score, response_rate,
  availability_status, distance_km, no_show_count, total_successful_donations,
  patient_urgency, days_since_last_donation, required_units, engagement_score
"""
import os
import math
import joblib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.donors.models import Donor, BloodGroup

logger = logging.getLogger(__name__)

# ── Model loading ──────────────────────────────────────────────────────────────
# Look for the .pkl files in the app directory (where they were placed)
_MODEL_PATH = "/app/models/donor_ranking_xgboost.pkl"
_COLS_PATH  = "/app/models/feature_columns.pkl"

_model = None
_feature_columns: List[str] = []

def _load_model():
    global _model, _feature_columns
    if _model is not None:
        return
    try:
        _model = joblib.load(_MODEL_PATH)
        _feature_columns = joblib.load(_COLS_PATH)
        logger.info("✅ Donor ranking model loaded from %s", _MODEL_PATH)
    except Exception as exc:
        logger.warning("⚠️  Could not load ML model: %s. Falling back to heuristic scoring.", exc)
        _model = None
        _feature_columns = []


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


def _engagement_score(donor: Donor) -> float:
    """Simple composite engagement score matching the training data definition."""
    return round(
        0.7 * donor.reliability_score +
        0.3 * donor.response_rate,
        3,
    )


def _days_since_donation(donor: Donor) -> int:
    if donor.last_donated_at is None:
        return 365  # never donated → treat as max gap
    delta = datetime.now(timezone.utc) - donor.last_donated_at
    return max(90, delta.days)  # model was trained with min 90


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
    """
    Returns exact distance using Haversine formula if coordinates are available.
    Falls back to rough distance: 30 km if in same city, 150 km otherwise.
    """
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


def _heuristic_score(donor: Donor, blood_group_match: int, urgency_num: int,
                     distance: float, required_units: int) -> float:
    """Fallback when model is unavailable."""
    score = (
        blood_group_match * 0.4 +
        donor.reliability_score * 0.2 +
        donor.response_rate * 0.15 +
        (1 - min(distance / 500, 1.0)) * 0.1 +
        (urgency_num / 2.0) * 0.05 +
        min(donor.total_donations / 28.0, 1.0) * 0.1
    )
    return round(score, 4)


def rank_donors(
    db: Session,
    patient_blood_group: Optional[str] = None,   # e.g. "A+"
    urgency: Optional[str] = None,                # "low"/"medium"/"high"/"critical"
    units_required: int = 1,
    patient_city: Optional[str] = None,
    patient_latitude: Optional[float] = None,
    patient_longitude: Optional[float] = None,
    request_id: Optional[int] = None,
    limit: int = 20,
) -> list[dict]:
    """
    Query all available donors, score them with the XGBoost model (or heuristic),
    and return a ranked list sorted by match_probability descending.
    """
    _load_model()

    if request_id is not None:
        from app.modules.blood_requests.models import BloodRequest
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

    # Fetch all available and eligible donors (cooldown check)
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import or_
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

    results = []
    for donor in donors:
        # Check compatibility: donor can donate to patient_blood_group
        compatible_patients = _COMPATIBLE.get(donor.blood_group.value, [])
        blood_group_match = 1 if patient_blood_group in compatible_patients else 0
        eligible = 1 if donor.is_available else 0
        distance = _distance_km(donor, patient_city, patient_latitude, patient_longitude)
        days_since = _days_since_donation(donor)
        engagement = _engagement_score(donor)

        if _model is not None:
            import pandas as pd
            row = {
                "blood_group_match": blood_group_match,
                "eligible_to_donate": eligible,
                "reliability_score": donor.reliability_score,
                "response_rate": donor.response_rate,
                "availability_status": 1,
                "distance_km": distance,
                "no_show_count": donor.no_show_count,
                "total_successful_donations": donor.total_donations,
                "patient_urgency": urgency_num,
                "days_since_last_donation": days_since,
                "required_units": min(units_required, 4),
                "engagement_score": engagement,
            }
            # Ensure column order matches training
            if _feature_columns:
                X = pd.DataFrame([[row[c] for c in _feature_columns]], columns=_feature_columns)
            else:
                X = pd.DataFrame([row])
            prob = float(_model.predict_proba(X)[0][1])
        else:
            prob = _heuristic_score(donor, blood_group_match, urgency_num, distance, units_required)

        results.append({
            "donor_id": donor.id,
            "user_id": donor.user_id,
            "blood_group": donor.blood_group.value,
            "city": donor.city,
            "is_available": donor.is_available,
            "reliability_score": donor.reliability_score,
            "response_rate": donor.response_rate,
            "total_donations": donor.total_donations,
            "blood_group_match": bool(blood_group_match),
            "distance_km": distance,
            "engagement_score": engagement,
            "match_probability": round(prob, 4),
        })

    # Sort by match probability descending
    results.sort(key=lambda x: x["match_probability"], reverse=True)
    return results[:limit]


def get_geojson_map_data(db: Session) -> dict:
    """
    Returns a GeoJSON FeatureCollection of active requests, available donors, and blood banks.
    """
    features = []

    # 1. Fetch available and eligible donors with coordinates (cooldown check)
    from app.modules.donors.models import Donor
    from sqlalchemy import or_
    from datetime import datetime, timedelta, timezone
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
    from app.modules.blood_requests.models import BloodRequest, RequestStatus
    from app.modules.patients.models import Patient
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
    from app.modules.blood_bank.models import BloodBankProfile
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
