"""Human spot check of the LLM judge.

    python -m evaluation.spot_check sheet --label v1   # write the worksheet + blank score file
    python -m evaluation.spot_check agree --label v1   # compare your scores with the judge

The worksheet (spot_check_<label>.md) is for reading; scores go in the small
spot_check_<label>_scores.csv. Judge scores are not shown, so the human scores blind.
"""

import argparse
import csv
import json
import random

from evaluation.common import PROJECT_ROOT, RESULTS_DIR
from evaluation.judge import is_refusal

SAMPLE_SIZE = 10

RUBRIC = """\
# Spot check: {label}

You are checking whether the automatic judge scores answers the way a person would.
For each question below, read it, then write two numbers in
`evaluation/results/spot_check_{label}_scores.csv` on the line with the same id.

**grounded**: is everything the answer says supported by the "Context given to the model"?
- `1` = every claim can be found in the context (missing things is fine here)
- `0` = it says at least one thing the context does not support (invented step, wrong number)

**correct**: does the answer contain the "Facts a correct answer must contain"?
- `2` = all of them, nothing contradicting
- `1` = some of them
- `0` = none of them, a contradiction, or it declined to answer

**If the answer declines** ("the context does not mention...", "I could not find..."),
write `1` for grounded and `0` for correct.

Example line in the scores file, for an answer that is supported but misses a fact:
`q12,1,1`

Score on your own first; the judge's scores are not in this file on purpose.

---
"""


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line.strip() else ">" for line in text.strip().splitlines())


def make_sheet(label: str) -> tuple[str, str]:
    result = json.loads((RESULTS_DIR / f"answers_{label}.json").read_text())
    answerable = [r for r in result["per_question"] if r["answerable"]]
    sample = sorted(random.Random(42).sample(answerable, SAMPLE_SIZE), key=lambda r: r["id"])

    parts = [RUBRIC.format(label=label)]
    for r in sample:
        facts = "\n".join(f"- {f}" for f in r["key_facts"])
        parts.append(
            f"\n## {r['id']}: {r['question']}\n\n"
            f"**Facts a correct answer must contain:**\n{facts}\n\n"
            f"**Context given to the model:**\n\n{_quote(r['context'])}\n\n"
            f"**Model's answer:**\n\n{_quote(r['answer'])}\n\n"
            f"Write in the scores file: `{r['id']},<grounded>,<correct>`\n\n---\n"
        )
    sheet = RESULTS_DIR / f"spot_check_{label}.md"
    sheet.write_text("".join(parts))

    scores = RESULTS_DIR / f"spot_check_{label}_scores.csv"
    if not scores.exists():  # never overwrite scores someone has started
        scores.write_text("id,grounded,correct\n" + "".join(f"{r['id']},,\n" for r in sample))
    return (str(sheet.relative_to(PROJECT_ROOT)), str(scores.relative_to(PROJECT_ROOT)))


def agree(label: str) -> None:
    result = json.loads((RESULTS_DIR / f"answers_{label}.json").read_text())
    by_id = {r["id"]: r for r in result["per_question"]}
    path = RESULTS_DIR / f"spot_check_{label}_scores.csv"
    rows = [r for r in csv.DictReader(path.open()) if r["correct"].strip()]
    if not rows:
        raise SystemExit(f"No scores yet in {path.relative_to(PROJECT_ROOT)}")

    def compare(name, subset):
        if not subset:
            return
        print(f"{name} ({len(subset)} rows):")
        for field in ("grounded", "correct"):
            ok = sum(str(by_id[r["id"]]["judge"][field]) == r[field].strip() for r in subset)
            n = len(subset)
            print(f"  {field}: judge agrees with you on {ok}/{n} ({ok / n:.0%})")

    judged = [r for r in rows if not is_refusal(by_id[r["id"]]["answer"])]
    ruled = [r for r in rows if is_refusal(by_id[r["id"]]["answer"])]
    compare("LLM-judged answers (this measures the judge)", judged)
    compare("Declined answers (scored by a fixed rule, agree by construction)", ruled)
    for r in judged:
        j = by_id[r["id"]]["judge"]
        if (str(j["grounded"]), str(j["correct"])) != (r["grounded"].strip(), r["correct"].strip()):
            print(f"  disagree {r['id']}: judge grounded={j['grounded']} correct={j['correct']}"
                  f" | you grounded={r['grounded']} correct={r['correct']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["sheet", "agree"])
    parser.add_argument("--label", default="v1")
    args = parser.parse_args()
    if args.command == "sheet":
        sheet, scores = make_sheet(args.label)
        print(f"read {sheet}\nwrite scores in {scores}")
    else:
        agree(args.label)


if __name__ == "__main__":
    main()
