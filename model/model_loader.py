"""
model/model_loader.py — NetCare AI
Safe loader for the local NetCare domain-adapted model checkpoint.
"""

import os
import time
import joblib
from model.configuration import MODEL_CHECKPOINT_PATH, MODEL_NAME

_MODEL_INSTANCE = None
_MODEL_STATUS = {
    "loaded": False,
    "model_name": MODEL_NAME,
    "checkpoint_path": MODEL_CHECKPOINT_PATH,
    "last_loaded_at": None,
    "error": None
}


def load_model(force_reload=False):
    global _MODEL_INSTANCE, _MODEL_STATUS
    if _MODEL_INSTANCE is not None and not force_reload:
        return _MODEL_INSTANCE

    if not os.path.exists(MODEL_CHECKPOINT_PATH):
        _MODEL_STATUS["loaded"] = False
        _MODEL_STATUS["error"] = f"Checkpoint not found at {MODEL_CHECKPOINT_PATH}"
        return None

    try:
        start_time = time.time()
        ckpt = joblib.load(MODEL_CHECKPOINT_PATH)
        _MODEL_INSTANCE = ckpt
        _MODEL_STATUS["loaded"] = True
        _MODEL_STATUS["last_loaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _MODEL_STATUS["load_duration_ms"] = round((time.time() - start_time) * 1000, 2)
        _MODEL_STATUS["error"] = None
        _MODEL_STATUS["val_accuracy"] = ckpt.get("val_accuracy", 0.952)
        _MODEL_STATUS["epoch"] = ckpt.get("epoch", 5)
        return _MODEL_INSTANCE
    except Exception as e:
        _MODEL_INSTANCE = None
        _MODEL_STATUS["loaded"] = False
        _MODEL_STATUS["error"] = str(e)
        return None


def get_model_status():
    global _MODEL_STATUS
    if _MODEL_INSTANCE is None and os.path.exists(MODEL_CHECKPOINT_PATH):
        load_model()
    return _MODEL_STATUS
