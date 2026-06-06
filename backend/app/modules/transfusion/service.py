from sqlalchemy.orm import Session
from app.modules.transfusion.models import TransfusionPrediction
from app.modules.transfusion.schemas import TransfusionPredictionCreate


class TransfusionService:
    def __init__(self, db: Session):
        self.db = db

    def predict_and_store(self, user_id: int, data: TransfusionPredictionCreate) -> TransfusionPrediction:
        # Medically realistic black-box inference simulation
        # Deficit represents target Hb minus current Hb
        deficit = data.target_hb_level - data.current_hb_level
        
        # Base units is proportional to deficit, and scaled by body weight
        # More units are needed for larger deficit and weight
        base_units = deficit * 0.9 + (data.weight_kg * 0.015)
        
        # Modify based on symptom severity and spleen status
        if data.symptom_severity == "Severe":
            base_units += 0.5
        elif data.symptom_severity == "Mild":
            base_units -= 0.2
            
        if data.spleen_status == "Enlarged":
            # Enlarged spleen destroys RBCs faster, requiring more units
            base_units += 0.4
            
        # Round and clip between 1 and 4
        predicted_units = min(max(int(round(base_units)), 1), 4)

        # Recommendation calculation
        if predicted_units == 4:
            days_until_next = 10
        elif predicted_units == 3:
            days_until_next = 15
        elif predicted_units == 2:
            days_until_next = 21
        else:
            days_until_next = 30

        # Save to database
        prediction = TransfusionPrediction(
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
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def get_history(self, user_id: int) -> list[TransfusionPrediction]:
        return (
            self.db.query(TransfusionPrediction)
            .filter(TransfusionPrediction.user_id == user_id)
            .order_by(TransfusionPrediction.created_at.desc())
            .all()
        )
