import logging
import pandas as pd

from app.modules.iron_overload.predictor.model_loader import ModelLoader

logger = logging.getLogger(__name__)


class IronOverloadPredictor:

    @staticmethod
    def predict(data: dict) -> dict:
        """
        Predict days until high iron overload risk.
        Uses the trained model when available; falls back to a clinical
        heuristic so the endpoint never crashes.
        """
        try:
            model = ModelLoader.load_model()
            feature_columns = ModelLoader.load_features()

            row = {col: data.get(col, 0) for col in feature_columns}
            df = pd.DataFrame([row])
            prediction = model.predict(df)[0]
            return {"days_until_high_risk": int(prediction)}

        except Exception as exc:
            logger.warning(
                "Iron overload model unavailable (%s). Using heuristic fallback.", exc
            )
            return {"days_until_high_risk": IronOverloadPredictor._heuristic(data)}

    @staticmethod
    def _heuristic(data: dict) -> int:
        """
        Clinical heuristic: estimate days until high risk from extracted values.
        Based on standard MRI iron overload progression guidelines.
        """
        heart_t2 = data.get("heart_t2_star_ms")
        lic = data.get("liver_iron_concentration_mg_g")
        ferritin = data.get("serum_ferritin")

        # Score risk level (higher = more urgent)
        risk_points = 0

        if heart_t2 is not None:
            if heart_t2 < 6:
                risk_points += 5   # Severe cardiac iron
            elif heart_t2 < 10:
                risk_points += 3   # Significant
            elif heart_t2 < 20:
                risk_points += 1   # Mild

        if lic is not None:
            if lic > 15:
                risk_points += 5   # Severe
            elif lic > 7:
                risk_points += 3   # Significant
            elif lic > 3:
                risk_points += 1   # Mild

        if ferritin is not None:
            if ferritin > 5000:
                risk_points += 3
            elif ferritin > 2500:
                risk_points += 2
            elif ferritin > 1000:
                risk_points += 1

        # Map risk points to estimated days
        if risk_points >= 10:
            return 30    # Already at high risk
        elif risk_points >= 7:
            return 90
        elif risk_points >= 5:
            return 180
        elif risk_points >= 3:
            return 365
        elif risk_points >= 1:
            return 548   # ~18 months
        else:
            return 730   # ~2 years (low/no data)
