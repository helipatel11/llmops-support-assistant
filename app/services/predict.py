import joblib

from app.logging_config import logger
from app.monitoring.metrics import prediction_counter


# Load artifacts once
model = joblib.load("training/models/model.pkl")
vectorizer = joblib.load("training/models/vectorizer.pkl")


def predict_priority(text: str):

    logger.info("Prediction request received")

    transformed_text = vectorizer.transform([text])

    prediction = model.predict(transformed_text)[0]

    logger.info(f"Prediction result: {prediction}")

    prediction_counter.labels(priority=prediction).inc()

    return prediction