import logging
from pathlib import Path
import joblib
import pandas as pd
from app.modules.transfusion.schemas import TransfusionPredictionCreate

logger = logging.getLogger(__name__)

# Model and columns paths
_MODEL_PATH = Path("/app/models/thalassemia_units_xgboost.pkl")
_COLS_PATH = Path("/app/models/thalassemia_feature_columns.pkl")

_model = None
_feature_columns = []

def _load_thalassemia_model():
    global _model, _feature_columns
    if _model is not None:
        return
    try:
        _model = joblib.load(_MODEL_PATH)
        _feature_columns = joblib.load(_COLS_PATH)
        logger.info("✅ Thalassemia prediction model loaded successfully from %s", _MODEL_PATH)
    except Exception as exc:
        logger.error("❌ Failed to load Thalassemia prediction model: %s", exc)
        _model = None
        _feature_columns = []


class TransfusionService:
    def predict_units(self, data: TransfusionPredictionCreate) -> dict:
        # Load the model if not loaded yet
        _load_thalassemia_model()

        if _model is not None:
            try:
                # Construct input dict matching feature columns names before dummy encoding
                input_dict = {
                    "age": data.age,
                    "weight_kg": data.weight_kg,
                    "current_hb_level": data.current_hb_level,
                    "target_hb_level": data.target_hb_level,
                    "ferritin_level": data.ferritin_level,
                    "days_since_last_transfusion": data.days_since_last_transfusion,
                    "previous_units_received": data.previous_units_received,
                    "average_units_per_transfusion": data.average_units_per_transfusion,
                    "transfusions_last_12_months": data.transfusions_last_12_months,
                    "gender": data.gender,
                    "thalassemia_type": data.thalassemia_type,
                    "spleen_status": data.spleen_status,
                    "symptom_severity": data.symptom_severity,
                    "blood_group": data.blood_group
                }

                # Create DataFrame
                df = pd.DataFrame([input_dict])

                # Set explicit categories for categorical fields to ensure pd.get_dummies outputs correct structure
                categorical_categories = {
                    "gender": ["Female", "Male"],
                    "thalassemia_type": ["Intermedia", "Major"],
                    "spleen_status": ["Enlarged", "Normal", "Removed"],
                    "symptom_severity": ["Mild", "Moderate", "Severe"],
                    "blood_group": ["A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-"]
                }

                for col, categories in categorical_categories.items():
                    df[col] = pd.Categorical(df[col], categories=categories)

                # Apply pd.get_dummies matching the training preprocessing (drop_first=True)
                df_encoded = pd.get_dummies(
                    df,
                    columns=[
                        "gender",
                        "thalassemia_type",
                        "spleen_status",
                        "symptom_severity",
                        "blood_group"
                    ],
                    drop_first=True,
                    dtype=int
                )

                # Reindex to ensure feature columns match training exactly (both order and presence)
                df_final = df_encoded.reindex(columns=_feature_columns, fill_value=0)

                # Perform prediction
                prediction = _model.predict(df_final)

                # Convert predicted class to units (predicted class is in 0, 1, 2, 3; add 1 to get units 1, 2, 3, 4)
                predicted_units = int(prediction[0]) + 1

            except Exception as exc:
                logger.error("❌ Inference failed: %s. Falling back to heuristic.", exc)
                # Fallback to heuristic if prediction fails
                deficit = data.target_hb_level - data.current_hb_level
                base_units = deficit * 0.9 + (data.weight_kg * 0.015)
                if data.symptom_severity == "Severe":
                    base_units += 0.5
                elif data.symptom_severity == "Mild":
                    base_units -= 0.2
                if data.spleen_status == "Enlarged":
                    base_units += 0.4
                predicted_units = min(max(int(round(base_units)), 1), 4)
        else:
            # Fallback heuristic if model is not loaded
            deficit = data.target_hb_level - data.current_hb_level
            base_units = deficit * 0.9 + (data.weight_kg * 0.015)
            if data.symptom_severity == "Severe":
                base_units += 0.5
            elif data.symptom_severity == "Mild":
                base_units -= 0.2
            if data.spleen_status == "Enlarged":
                base_units += 0.4
            predicted_units = min(max(int(round(base_units)), 1), 4)

        # Recommendation calculation (according to approved rule)
        if predicted_units == 4:
            days_until_next = 10
        elif predicted_units == 3:
            days_until_next = 15
        elif predicted_units == 2:
            days_until_next = 21
        else:
            days_until_next = 30

        return {
            "predicted_units_required": predicted_units,
            "recommended_next_transfusion_in_days": days_until_next,
        }
