import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

mlflow.set_tracking_uri("file:./mlruns")

# MLflow experiment
mlflow.set_experiment("support-ticket-classifier")


# Load dataset
df = pd.read_csv("training/data/tickets.csv")

X = df["text"]
y = df["priority"]


with mlflow.start_run():

    # Vectorization
    vectorizer = TfidfVectorizer()

    X_vectorized = vectorizer.fit_transform(X)

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_vectorized,
        y,
        test_size=0.2,
        random_state=42
    )

    # Model
    model = LogisticRegression()

    # Train
    model.fit(X_train, y_train)

    # Predict
    predictions = model.predict(X_test)

    # Accuracy
    accuracy = accuracy_score(y_test, predictions)

    print(f"Accuracy: {accuracy}")

    # Log params
    mlflow.log_param("model_type", "LogisticRegression")

    # Log metrics
    mlflow.log_metric("accuracy", accuracy)

    # Log model
    
    # mlflow.sklearn.log_model(
    #     model,
    #     "model"
    # )

    mlflow.sklearn.log_model(
    sk_model=model,
    artifact_path="model",
    registered_model_name="support-ticket-classifier"
)

    # Save artifacts locally
    joblib.dump(model, "training/models/model.pkl")
    joblib.dump(vectorizer, "training/models/vectorizer.pkl")

    # Log artifacts
    mlflow.log_artifact("training/models/model.pkl")
    mlflow.log_artifact("training/models/vectorizer.pkl")

    print("Training complete.")