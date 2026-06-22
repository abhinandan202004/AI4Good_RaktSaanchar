from fastapi import APIRouter, status
from app.modules.transfusion.schemas import TransfusionPredictionCreate, TransfusionInferenceOut
from app.modules.transfusion.service import TransfusionService

router = APIRouter(prefix="/predict", tags=["Transfusion Predictor"])


@router.post("/transfusion", response_model=TransfusionInferenceOut, status_code=status.HTTP_200_OK)
def predict_transfusion(
    data: TransfusionPredictionCreate,
):
    """
    Predicts required transfusion units and next transfusion schedule using XGBoost.
    Database-free endpoint.
    """
    svc = TransfusionService()
    return svc.predict_units(data)
