from fastapi import APIRouter
from app.modules.ml.schemas import ServerlessDonorRankRequest, RankedDonorOut
from app.modules.ml import service as ml_service

router = APIRouter(prefix="/predict", tags=["ML - Donor Ranking"])


@router.post("/donor-ranks", response_model=list[RankedDonorOut])
def rank_donors(
    body: ServerlessDonorRankRequest,
):
    """
    Returns a scored and ranked list of available donors.
    Uses the pre-trained XGBoost model to score each donor by match probability.
    Database-free endpoint.
    """
    return ml_service.rank_donors_db_free(
        patient_blood_group=body.patient_blood_group,
        urgency=body.urgency,
        units_required=body.units_required,
        patient_city=body.patient_city,
        patient_latitude=body.patient_latitude,
        patient_longitude=body.patient_longitude,
        donors=body.donors,
        limit=body.limit,
    )
