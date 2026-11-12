"""Test the LLM judge on constructed cases with known labels.

Run from the repo root:  python -m evaluation.judge_calibration [--judge-model llama3]
Writes evaluation/results/judge_calibration_<model>.json

Each case pairs a real knowledge-base doc (as context) with an answer whose correct
grounded/correct labels are known by construction (paraphrase, wrong number, partial
answer, invented extra fact, contradiction, ...). The judge's scores on the golden set
are only as trustworthy as its agreement here.
"""

import argparse
import json

from app import config
from evaluation.common import PROJECT_ROOT, file_sha256, run_metadata, write_result
from evaluation.judge import Judge

CASES = PROJECT_ROOT / "evaluation" / "judge_calibration.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-model", default="llama3")
    args = parser.parse_args()

    judge = Judge(args.judge_model)
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    rows = []
    for c in cases:
        context = (config.DOCS_DIR / c["context_doc"]).read_text()
        got = judge.score(context, c["key_facts"], c["answer"])
        row = {
            "id": c["id"], "case": c["case"],
            "expected": {"grounded": c["expected_grounded"], "correct": c["expected_correct"]},
            "got": got,
            "grounded_ok": got.get("grounded") == c["expected_grounded"],
            "correct_ok": got.get("correct") == c["expected_correct"],
        }
        rows.append(row)
        flag = "ok " if row["grounded_ok"] and row["correct_ok"] else "BAD"
        print(f"{flag} {c['id']} {c['case']:<38} expected g={c['expected_grounded']} "
              f"c={c['expected_correct']}  got g={got.get('grounded')} c={got.get('correct')}")

    n = len(rows)
    summary = {
        "grounded_agreement": round(sum(r["grounded_ok"] for r in rows) / n, 4),
        "correct_agreement": round(sum(r["correct_ok"] for r in rows) / n, 4),
        "both_agreement": round(sum(r["grounded_ok"] and r["correct_ok"] for r in rows) / n, 4),
    }
    print(summary)
    path = write_result(f"judge_calibration_{args.judge_model}", {
        "metadata": run_metadata(),
        "judge_model": args.judge_model,
        "dataset": {"path": str(CASES.relative_to(PROJECT_ROOT)), "cases": n,
                    "sha256": file_sha256(CASES)},
        **summary,
        "per_case": rows,
    })
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
