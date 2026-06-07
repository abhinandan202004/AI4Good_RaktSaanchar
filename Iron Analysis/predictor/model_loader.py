import joblib
from pathlib import Path

MODEL_PATH = Path("models/thalassemia_high_risk_model.pkl")
FEATURES_PATH = Path("models/feature_columns (2).pkl")


class ModelLoader:

    _model = None
    _features = None

    @classmethod
    def load_model(cls):

        if cls._model is None:
            cls._model = joblib.load(MODEL_PATH)

        return cls._model

    @classmethod
    def load_features(cls):

        if cls._features is None:
            cls._features = joblib.load(FEATURES_PATH)

        return cls._features
