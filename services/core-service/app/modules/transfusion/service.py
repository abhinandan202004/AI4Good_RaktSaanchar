import logging
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.transfusion.models import TransfusionPrediction
from app.modules.transfusion.schemas import TransfusionPredictionCreate

logger = logging.getLogger(__name__)


class TransfusionService:
    def __init__(self, db: Session):
        self.db = db

    def predict_and_store(self, user_id: int, data: TransfusionPredictionCreate) -> TransfusionPrediction:
        predicted_units = None
        days_until_next = None

        # 1. Try to invoke Hugging Face Space ML Service
        try:
            resp = httpx.post(
                f"{settings.ML_SERVICE_URL}/predict/transfusion",
                json=data.dict(),
                timeout=8.0
            )
            if resp.status_code == 200:
                result = resp.json()
                predicted_units = result.get("predicted_units_required")
                days_until_next = result.get("recommended_next_transfusion_in_days")
                logger.info("✅ Hugging Face transfusion prediction successful: %d units", predicted_units)
        except Exception as exc:
            logger.warning("⚠️ Hugging Face transfusion prediction failed: %s. Using local heuristic fallback.", exc)

        # 2. Heuristic Fallback (if ML service failed or timed out)
        if predicted_units is None or days_until_next is None:
            deficit = data.target_hb_level - data.current_hb_level
            base_units = deficit * 0.9 + (data.weight_kg * 0.015)
            if data.symptom_severity == "Severe":
                base_units += 0.5
            elif data.symptom_severity == "Mild":
                base_units -= 0.2
            if data.spleen_status == "Enlarged":
                base_units += 0.4
            
            predicted_units = min(max(int(round(base_units)), 1), 4)

            if predicted_units == 4:
                days_until_next = 10
            elif predicted_units == 3:
                days_until_next = 15
            elif predicted_units == 2:
                days_until_next = 21
            else:
                days_until_next = 30

        # 3. Store in local PostgreSQL database
        prediction_record = TransfusionPrediction(
            user_id=user_id,
            age=data.age,
            gender=data.gender,
            weight_kg=data.weight_kg,
            thalassemia_type=data.thalassemia_type,
            current_hb_level=data.current_hb_level,
            target_hb_level=data.target_hb_level,
            ferritin_level=data.ferritin_level,
            days_since_last_transfusion=data.days_since_last_transfusion,
            previous_units_received=data.previous_units_received,
            average_units_per_transfusion=data.average_units_per_transfusion,
            transfusions_last_12_months=data.transfusions_last_12_months,
            spleen_status=data.spleen_status,
            symptom_severity=data.symptom_severity,
            blood_group=data.blood_group,
            predicted_units_required=predicted_units,
            recommended_next_transfusion_in_days=days_until_next,
        )
        self.db.add(prediction_record)
        self.db.commit()
        self.db.refresh(prediction_record)
        return prediction_record

    def get_history(self, user_id: int) -> list[TransfusionPrediction]:
        return (
            self.db.query(TransfusionPrediction)
            .filter(TransfusionPrediction.user_id == user_id)
            .order_by(TransfusionPrediction.created_at.desc())
            .all()
        )
