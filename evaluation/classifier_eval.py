"""Evaluate the classifier artifacts the API serves, on the held-out test set.

Run from the repo root:  python -m evaluation.classifier_eval [--label NAME]
Writes evaluation/results/classifier_<label>.json
"""

import argparse
import csv

import joblib
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from app import config
from evaluation.common import PROJECT_ROOT, file_sha256, run_metadata, write_result

TEST_SET = PROJECT_ROOT / "training" / "data" / "tickets_test.csv"
LABELS = ["high", "medium", "low"]


def load_test_set():
    with TEST_SET.open() as f:
        rows = list(csv.DictReader(f))
    return [r["text"] for r in rows], [r["priority"] for r in rows]


def evaluate() -> dict:
    model = joblib.load(config.MODEL_PATH)
    vectorizer = joblib.load(config.VECTORIZER_PATH)
    texts, y_true = load_test_set()
    y_pred = list(model.predict(vectorizer.transform(texts)))

    report = classification_report(
        y_true, y_pred, labels=LABELS, output_dict=True, zero_division=0
    )
    return {
        "metadata": run_metadata(),
        "artifacts": {
            "model_sha256": file_sha256(config.MODEL_PATH),
            "vectorizer_sha256": file_sha256(config.VECTORIZER_PATH),
        },
        "dataset": {
            "path": str(TEST_SET.relative_to(PROJECT_ROOT)),
            "rows": len(texts),
            "sha256": file_sha256(TEST_SET),
        },
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "per_class": {
            label: {
                "precision": round(report[label]["precision"], 4),
                "recall": round(report[label]["recall"], 4),
                "f1": round(report[label]["f1-score"], 4),
                "support": int(report[label]["support"]),
            }
            for label in LABELS
        },
        "confusion_matrix": {
            "labels": LABELS,
            "rows_are": "true label",
            "columns_are": "predicted label",
            "matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        },
    }


def print_summary(result: dict) -> None:
    print(f"accuracy={result['accuracy']}  macro_f1={result['macro_f1']}  "
          f"n={result['dataset']['rows']}")
    print(f"{'class':<8}{'precision':>10}{'recall':>8}{'f1':>8}{'support':>9}")
    for label, m in result["per_class"].items():
        print(f"{label:<8}{m['precision']:>10}{m['recall']:>8}{m['f1']:>8}{m['support']:>9}")
    print("confusion matrix (rows=true, cols=pred):", LABELS)
    matrix = result["confusion_matrix"]["matrix"]
    for i, label in enumerate(LABELS):
        print(f"  {label:<7}{matrix[i]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current", help="name for the result file")
    args = parser.parse_args()

    result = evaluate()
    print_summary(result)
    path = write_result(f"classifier_{args.label}", result)
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
