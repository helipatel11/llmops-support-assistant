import json

import joblib

from app import config
from app.logging_config import logger
from app.monitoring.metrics import prediction_counter

# Load the selected model version once, at startup: a missing artifact should fail fast.
pipeline = joblib.load(config.classifier_artifact(config.MODEL_VERSION))
model_meta = json.loads(config.classifier_meta(config.MODEL_VERSION).read_text())
logger.info("Loaded classifier %s (mlflow run %s)",
            model_meta["version"], model_meta.get("mlflow_run_id"))


def predict_priority(text: str) -> str:
    logger.info("Prediction request received")

    prediction = str(pipeline.predict([text])[0])

    logger.info("Prediction result: %s", prediction)

    prediction_counter.labels(priority=prediction, model_version=model_meta["version"]).inc()

    return prediction
