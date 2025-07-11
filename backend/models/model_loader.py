from tensorflow.keras.models import load_model
import os

MODEL_PATH = os.path.join("saved_models", "latest_model.h5")
_model = None

def load_model_once():
    global _model
    if _model is None:
        _model = load_model(MODEL_PATH)
    return _model
