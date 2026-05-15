import joblib


# Load artifacts once
model = joblib.load("training/models/model.pkl")
vectorizer = joblib.load("training/models/vectorizer.pkl")


def predict_priority(text: str):

    transformed_text = vectorizer.transform([text])

    prediction = model.predict(transformed_text)[0]

    return prediction