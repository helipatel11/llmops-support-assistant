"""Compare the LLM judge with a human on the spot-check sample.

1. Open evaluation/results/spot_check_<label>.csv and fill in human_grounded (0/1)
   and human_correct (0/1/2) using the rubric in evaluation/answer_eval.py.
2. Run:  python -m evaluation.spot_check_agreement [--label NAME]
"""

import argparse
import csv

from evaluation.common import PROJECT_ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current")
    args = parser.parse_args()

    path = PROJECT_ROOT / "evaluation" / "results" / f"spot_check_{args.label}.csv"
    rows = [r for r in csv.DictReader(path.open()) if r["human_correct"].strip()]
    if not rows:
        raise SystemExit(f"No human scores yet in {path.relative_to(PROJECT_ROOT)}")

    for field in ("grounded", "correct"):
        agree = sum(r[f"judge_{field}"] == r[f"human_{field}"].strip() for r in rows)
        print(f"{field}: judge agrees with human on {agree}/{len(rows)} ({agree / len(rows):.0%})")
    for r in rows:
        if r["judge_correct"] != r["human_correct"].strip():
            print(f"  disagree {r['id']}: judge={r['judge_correct']} human={r['human_correct']}")


if __name__ == "__main__":
    main()
