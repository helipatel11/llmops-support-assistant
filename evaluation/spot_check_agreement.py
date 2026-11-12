"""Compare the LLM judge with a human on the spot-check sample.

1. Open evaluation/results/spot_check_<label>.csv and fill in human_grounded (0/1)
   and human_correct (0/1/2) using the rubric in evaluation/judge.py.
   Refusals are scored grounded=1, correct=0.
2. Run:  python -m evaluation.spot_check_agreement [--label NAME]

Rows whose answer is a refusal are scored by a fixed rule, not by the LLM judge, so
they agree with a human by construction. Agreement is reported for LLM-judged rows
separately; that is the number that measures the judge.
"""

import argparse
import csv

from evaluation.common import PROJECT_ROOT
from evaluation.judge import is_refusal


def report(name: str, rows: list[dict]) -> None:
    if not rows:
        print(f"{name}: no rows")
        return
    print(f"{name} ({len(rows)} rows):")
    for field in ("grounded", "correct"):
        agree = sum(r[f"judge_{field}"] == r[f"human_{field}"].strip() for r in rows)
        n = len(rows)
        print(f"  {field}: judge agrees with human on {agree}/{n} ({agree / n:.0%})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current")
    args = parser.parse_args()

    path = PROJECT_ROOT / "evaluation" / "results" / f"spot_check_{args.label}.csv"
    rows = [r for r in csv.DictReader(path.open()) if r["human_correct"].strip()]
    if not rows:
        raise SystemExit(f"No human scores yet in {path.relative_to(PROJECT_ROOT)}")

    judged = [r for r in rows if not is_refusal(r["answer"])]
    ruled = [r for r in rows if is_refusal(r["answer"])]
    report("LLM-judged rows (measures the judge)", judged)
    report("Rule-scored refusals (agree by construction)", ruled)
    for r in judged:
        if (r["judge_correct"], r["judge_grounded"]) != (r["human_correct"].strip(),
                                                          r["human_grounded"].strip()):
            print(f"  disagree {r['id']}: judge g={r['judge_grounded']} c={r['judge_correct']}"
                  f"  human g={r['human_grounded']} c={r['human_correct']}")


if __name__ == "__main__":
    main()
