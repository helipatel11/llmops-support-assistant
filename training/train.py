"""Train one classifier version and log it to MLflow.

Run from the repo root:  python -m training.train --version v1
Reads configs/classifier_<version>.json, trains on tickets_train.csv only, and writes:
  training/models/classifier_<version>.joblib     (sklearn Pipeline: TF-IDF + LR)
  training/models/classifier_<version>.meta.json  (version, MLflow run, data hash, metrics)
Metrics come from the held-out tickets_test.csv via evaluation/classifier_eval.py.
"""

import argparse
import json

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.tracking import MlflowClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app import config
from evaluation.classifier_eval import evaluate, print_summary
from evaluation.common import PROJECT_ROOT, file_sha256, run_metadata, write_result

TRAIN_SET = PROJECT_ROOT / "training" / "data" / "tickets_train.csv"
REGISTERED_NAME = "support-ticket-classifier"


def load_config(version: str) -> dict:
    return json.loads((config.CONFIGS_DIR / f"classifier_{version}.json").read_text())


def build_pipeline(cfg: dict) -> Pipeline:
    tfidf = {**cfg["tfidf"], "ngram_range": tuple(cfg["tfidf"]["ngram_range"])}
    return Pipeline([
        ("tfidf", TfidfVectorizer(**tfidf)),
        ("logreg", LogisticRegression(**cfg["logreg"])),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    cfg = load_config(args.version)
    df = pd.read_csv(TRAIN_SET)

    mlflow.set_tracking_uri(f"file:{PROJECT_ROOT / 'mlruns'}")
    mlflow.set_experiment(REGISTERED_NAME)

    with mlflow.start_run(run_name=f"classifier-{args.version}") as run:
        # The pipeline fits TF-IDF on training data only (no test data in the vocabulary).
        pipeline = build_pipeline(cfg).fit(df["text"], df["priority"])

        artifact = config.classifier_artifact(args.version)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, artifact)

        result = evaluate(args.version)
        print_summary(result)

        mlflow.set_tag("classifier_version", args.version)
        mlflow.log_params({
            "version": args.version,
            "tfidf": json.dumps(cfg["tfidf"]),
            "logreg": json.dumps(cfg["logreg"]),
            "train_rows": len(df),
            "train_data_sha256": file_sha256(TRAIN_SET),
        })
        mlflow.log_metrics({"accuracy": result["accuracy"], "macro_f1": result["macro_f1"]})
        for label, m in result["per_class"].items():
            mlflow.log_metrics({f"{label}_{k}": m[k] for k in ("precision", "recall", "f1")})
        mlflow.sklearn.log_model(
            sk_model=pipeline, artifact_path="model", registered_model_name=REGISTERED_NAME,
        )
        versions = MlflowClient().search_model_versions(f"run_id='{run.info.run_id}'")
        registered = int(versions[0].version) if versions else None

        meta = {
            "version": args.version,
            "description": cfg.get("description", ""),
            "config": cfg,
            "mlflow_run_id": run.info.run_id,
            "mlflow_registered_model": REGISTERED_NAME,
            "mlflow_registered_version": registered,
            "train_data_sha256": file_sha256(TRAIN_SET),
            "test_accuracy": result["accuracy"],
            "test_macro_f1": result["macro_f1"],
            "trained": run_metadata(),
        }
        config.classifier_meta(args.version).write_text(json.dumps(meta, indent=2) + "\n")
        mlflow.log_artifact(str(config.classifier_meta(args.version)))

        write_result(f"classifier_{args.version}", result)
        print(f"Trained classifier {args.version}: {artifact.relative_to(PROJECT_ROOT)} "
              f"(MLflow run {run.info.run_id}, registered version {registered})")


if __name__ == "__main__":
    main()
