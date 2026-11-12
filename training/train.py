"""Train the ticket-priority classifier and log the run to MLflow.

Run from the repo root:  python -m training.train
Trains on tickets_train.csv only; metrics come from the held-out tickets_test.csv,
computed by the same code as evaluation/classifier_eval.py.
"""

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app import config
from evaluation.classifier_eval import evaluate, print_summary
from evaluation.common import PROJECT_ROOT, write_result

TRAIN_SET = PROJECT_ROOT / "training" / "data" / "tickets_train.csv"

PARAMS = {
    "model_type": "LogisticRegression",
    "max_iter": 1000,
    "tfidf_ngram_range": "(1, 1)",
}


def main() -> None:
    mlflow.set_tracking_uri(f"file:{PROJECT_ROOT / 'mlruns'}")
    mlflow.set_experiment("support-ticket-classifier")

    df = pd.read_csv(TRAIN_SET)

    with mlflow.start_run():
        # Fit the vectorizer on training data only (no test data leaks into the vocabulary).
        vectorizer = TfidfVectorizer()
        X_train = vectorizer.fit_transform(df["text"])

        model = LogisticRegression(max_iter=PARAMS["max_iter"])
        model.fit(X_train, df["priority"])

        config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, config.MODEL_PATH)
        joblib.dump(vectorizer, config.VECTORIZER_PATH)

        result = evaluate()
        print_summary(result)

        mlflow.log_params({**PARAMS, "train_rows": len(df)})
        mlflow.log_metrics({"accuracy": result["accuracy"], "macro_f1": result["macro_f1"]})
        for label, m in result["per_class"].items():
            mlflow.log_metrics({f"{label}_{k}": m[k] for k in ("precision", "recall", "f1")})

        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name="support-ticket-classifier",
        )
        mlflow.log_artifact(str(config.MODEL_PATH))
        mlflow.log_artifact(str(config.VECTORIZER_PATH))

        path = write_result("classifier_current", result)
        print(f"Training complete. Eval written to {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
