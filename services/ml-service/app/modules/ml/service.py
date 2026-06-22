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
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Model loading ──────────────────────────────────────────────────────────────
_MODEL_PATH = "/app/models/donor_ranking_xgboost.pkl"
_COLS_PATH  = "/app/models/feature_columns.pkl"

_model = None
_feature_columns: List[str] = []

def _load_model():
    global _model, _feature_columns
    if _model is not None:
        return
    try:
        # Load from models directory inside docker context
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
    donor_city: Optional[str],
    donor_lat: Optional[float],
    donor_lon: Optional[float],
    patient_city: Optional[str],
    patient_latitude: Optional[float] = None,
    patient_longitude: Optional[float] = None,
) -> float:
    if (
        donor_lat is not None
        and donor_lon is not None
        and patient_latitude is not None
        and patient_longitude is not None
    ):
        return round(haversine_distance(patient_latitude, patient_longitude, donor_lat, donor_lon), 2)

    if not patient_city or not donor_city:
        return 100.0
    if donor_city.strip().lower() == patient_city.strip().lower():
        return 30.0
    return 150.0


def _heuristic_score(
    reliability_score: float,
    response_rate: float,
    total_donations: int,
    blood_group_match: int,
    urgency_num: int,
    distance: float
) -> float:
    """Fallback when model is unavailable."""
    score = (
        blood_group_match * 0.4 +
        reliability_score * 0.2 +
        response_rate * 0.15 +
        (1 - min(distance / 500, 1.0)) * 0.1 +
        (urgency_num / 2.0) * 0.05 +
        min(total_donations / 28.0, 1.0) * 0.1
    )
    return round(score, 4)


def rank_donors_db_free(
    patient_blood_group: str,
    urgency: str,
    units_required: int,
    patient_city: Optional[str],
    patient_latitude: Optional[float],
    patient_longitude: Optional[float],
    donors: list,
    limit: int = 20,
) -> list[dict]:
    """
    Scored candidate donors with the XGBoost model (or heuristic) without database access.
    """
    _load_model()

    urgency_num = _URGENCY_MAP.get(urgency.lower(), 1)

    results = []
    for d in donors:
        # Check compatibility: donor can donate to patient_blood_group
        compatible_patients = _COMPATIBLE.get(d.blood_group, [])
        blood_group_match = 1 if patient_blood_group in compatible_patients else 0
        eligible = 1 if d.is_available else 0
        distance = _distance_km(
            donor_city=d.city,
            donor_lat=d.latitude,
            donor_lon=d.longitude,
            patient_city=patient_city,
            patient_latitude=patient_latitude,
            patient_longitude=patient_longitude,
        )
        days_since = max(90, d.days_since_last_donation)
        engagement = round(0.7 * d.reliability_score + 0.3 * d.response_rate, 3)

        if _model is not None:
            import pandas as pd
            row = {
                "blood_group_match": blood_group_match,
                "eligible_to_donate": eligible,
                "reliability_score": d.reliability_score,
                "response_rate": d.response_rate,
                "availability_status": 1,
                "distance_km": distance,
                "no_show_count": d.no_show_count,
                "total_successful_donations": d.total_donations,
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
            prob = _heuristic_score(
                reliability_score=d.reliability_score,
                response_rate=d.response_rate,
                total_donations=d.total_donations,
                blood_group_match=blood_group_match,
                urgency_num=urgency_num,
                distance=distance,
            )

        results.append({
            "donor_id": d.donor_id,
            "user_id": d.user_id,
            "blood_group": d.blood_group,
            "city": d.city,
            "is_available": d.is_available,
            "reliability_score": d.reliability_score,
            "response_rate": d.response_rate,
            "total_donations": d.total_donations,
            "blood_group_match": bool(blood_group_match),
            "distance_km": distance,
            "engagement_score": engagement,
            "match_probability": round(prob, 4),
        })

    # Sort by match probability descending
    results.sort(key=lambda x: x["match_probability"], reverse=True)
    return results[:limit]
