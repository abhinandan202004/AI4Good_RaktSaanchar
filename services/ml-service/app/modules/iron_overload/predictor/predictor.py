import pandas as pd

from app.modules.iron_overload.predictor.model_loader import ModelLoader


class IronOverloadPredictor:

    @staticmethod
    def predict(data: dict):

        model = ModelLoader.load_model()

        feature_columns = ModelLoader.load_features()

        row = {}

        for col in feature_columns:
            row[col] = data.get(col, 0)

        df = pd.DataFrame([row])

        prediction = model.predict(df)[0]

        return {
            "days_until_high_risk": int(prediction)
        }
