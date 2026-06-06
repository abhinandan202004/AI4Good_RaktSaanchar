from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user, require_roles
from app.modules.ml.schemas import DonorRankRequest, RankedDonorOut
from app.modules.ml import service as ml_service

router = APIRouter(prefix="/ml", tags=["ML - Donor Ranking"])


@router.post("/rank-donors", response_model=list[RankedDonorOut])
def rank_donors(
    body: DonorRankRequest,
    db: Session = Depends(get_db),
    _current_user=Depends(get_current_user),
):
    """
    Returns a ranked list of available donors for a blood request.
    Uses the pre-trained XGBoost model to score each donor by match probability.
    Requires authentication (any role).
    """
    return ml_service.rank_donors(
        db=db,
        patient_blood_group=body.patient_blood_group,
        urgency=body.urgency,
        units_required=body.units_required,
        patient_city=body.patient_city,
        patient_latitude=body.patient_latitude,
        patient_longitude=body.patient_longitude,
        request_id=body.request_id,
        limit=body.limit,
    )


@router.get("/map-data")
def get_map_data(
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("admin", "coordinator")),
):
    """
    Returns a GeoJSON FeatureCollection of active requests, available donors, and blood banks.
    """
    return ml_service.get_geojson_map_data(db)
