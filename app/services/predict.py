import joblib

from app import config
from app.logging_config import logger
from app.monitoring.metrics import prediction_counter

# Load artifacts once, at startup: a missing model should fail fast.
model = joblib.load(config.MODEL_PATH)
vectorizer = joblib.load(config.VECTORIZER_PATH)


def predict_priority(text: str) -> str:
    logger.info("Prediction request received")

    transformed_text = vectorizer.transform([text])

    prediction = str(model.predict(transformed_text)[0])

    logger.info("Prediction result: %s", prediction)

    prediction_counter.labels(priority=prediction).inc()

    return prediction
