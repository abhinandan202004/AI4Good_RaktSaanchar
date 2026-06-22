from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.modules.transfusion.schemas import TransfusionPredictionCreate, TransfusionPredictionOut
from app.modules.transfusion.service import TransfusionService

router = APIRouter(prefix="/transfusion", tags=["Transfusion Predictor"])


def _svc(db: Session = Depends(get_db)) -> TransfusionService:
    return TransfusionService(db)


@router.post("/predict", response_model=TransfusionPredictionOut, status_code=status.HTTP_201_CREATED)
def predict_transfusion(
    data: TransfusionPredictionCreate,
    svc: TransfusionService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.predict_and_store(current_user.id, data)


@router.get("/history", response_model=List[TransfusionPredictionOut])
def get_prediction_history(
    svc: TransfusionService = Depends(_svc),
    current_user=Depends(get_current_user),
):
    return svc.get_history(current_user.id)
