"""Evaluate answer quality on the golden set with a local LLM judge.

Run from the repo root (needs Ollama with the serving model and the judge model):
    python -m evaluation.answer_eval [--label NAME] [--judge-model llama3] [--rejudge]
Writes evaluation/results/answers_<label>.json and spot_check_<label>.csv

Pass 1: the serving pipeline answers every question (retrieve top-k + generate).
Pass 2: the judge (evaluation/judge.py) scores each answer for groundedness and
correctness. Passes are separate so the two models are not swapped in and out of
memory for every question. --rejudge skips pass 1 and re-scores saved answers.

Unanswerable questions are scored by rule: success = the exact refusal sentence.
"""

import argparse
import csv
import json
import random
import time
from statistics import mean, median

from app import config
from app.services.rag import generate, retrieve
from evaluation.common import PROJECT_ROOT, RESULTS_DIR, file_sha256, run_metadata, write_result
from evaluation.judge import Judge, is_refusal
from evaluation.retrieval_eval import GOLDEN, load_golden

SPOT_CHECK_SIZE = 10


def answer_all(golden: list[dict]) -> list[dict]:
    rows = []
    for i, q in enumerate(golden, 1):
        t0 = time.perf_counter()
        docs = retrieve(q["question"])
        t1 = time.perf_counter()
        answer = generate(q["question"], docs).strip()
        t2 = time.perf_counter()
        rows.append({
            **q,
            "context": "\n\n".join(d.page_content for d in docs),
            "answer": answer,
            "retrieval_s": round(t1 - t0, 3),
            "generation_s": round(t2 - t1, 3),
        })
        print(f"[answer {i}/{len(golden)}] {q['id']} {t2 - t0:.1f}s")
    return rows


def judge_all(rows: list[dict], judge: Judge) -> None:
    for i, r in enumerate(rows, 1):
        r["refused"] = is_refusal(r["answer"])
        if r["answerable"]:
            r["judge"] = judge.score(r["context"], r["key_facts"], r["answer"])
        else:
            r["judge"] = None  # success = refusal, checked by rule
        print(f"[judge {i}/{len(rows)}] {r['id']} refused={r['refused']} "
              f"g={(r['judge'] or {}).get('grounded')} c={(r['judge'] or {}).get('correct')}")


def summarise(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"]]
    unans = [r for r in rows if not r["answerable"]]
    judged = [r for r in ans if r["judge"].get("correct") is not None
              and r["judge"].get("grounded") is not None]
    return {
        "answerable": {
            "n": len(ans),
            "judged": len(judged),
            "fully_correct_rate": round(mean(r["judge"]["correct"] == 2 for r in judged), 4),
            "mean_correct_score_0_to_2": round(mean(r["judge"]["correct"] for r in judged), 4),
            "grounded_rate": round(mean(r["judge"]["grounded"] for r in judged), 4),
            "false_refusal_rate": round(mean(r["refused"] for r in ans), 4),
        },
        "unanswerable": {
            "n": len(unans),
            "correct_refusal_rate": round(mean(r["refused"] for r in unans), 4),
        },
        "latency_s_informal": {
            "note": "Single sequential run on the dev laptop; not a load test (see Phase 4).",
            "retrieval_median": round(median(r["retrieval_s"] for r in rows), 3),
            "generation_median": round(median(r["generation_s"] for r in rows), 3),
            "generation_max": round(max(r["generation_s"] for r in rows), 3),
        },
    }


def write_spot_check(rows: list[dict], label: str) -> str:
    """Seeded sample of answerable questions for a human to score with the same rubric."""
    sample = random.Random(42).sample([r for r in rows if r["answerable"]], SPOT_CHECK_SIZE)
    path = RESULTS_DIR / f"spot_check_{label}.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "question", "key_facts", "context", "answer",
                    "judge_grounded", "judge_correct", "human_grounded", "human_correct"])
        for r in sorted(sample, key=lambda r: r["id"]):
            w.writerow([r["id"], r["question"], " | ".join(r["key_facts"]), r["context"],
                        r["answer"], r["judge"].get("grounded"), r["judge"].get("correct"),
                        "", ""])
    return str(path.relative_to(PROJECT_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current")
    parser.add_argument("--judge-model", default="llama3")
    parser.add_argument("--rejudge", action="store_true",
                        help="re-score the answers saved in answers_<label>.json")
    args = parser.parse_args()

    out_path = RESULTS_DIR / f"answers_{args.label}.json"
    if args.rejudge:
        saved = json.loads(out_path.read_text())
        rows, serving = saved["per_question"], saved["config"]
        golden = {q["id"]: q for q in load_golden()}
        for r in rows:  # pick up golden-set edits (e.g. key_facts) without regenerating
            r.update({k: v for k, v in golden[r["id"]].items() if k != "question"})
    else:
        rows = answer_all(load_golden())
        serving = {
            "serving_model": config.OLLAMA_MODEL,
            "embedding_model": config.EMBEDDING_MODEL,
            "serving_top_k": config.RETRIEVER_K,
            "temperature": 0,
        }

    judge_all(rows, Judge(args.judge_model))
    summary = summarise(rows)

    result = {
        "metadata": run_metadata(),
        "config": {**serving, "judge_model": args.judge_model},
        "dataset": {"path": str(GOLDEN.relative_to(PROJECT_ROOT)), "sha256": file_sha256(GOLDEN)},
        **summary,
        "per_question": rows,
    }
    print(json.dumps(summary, indent=2))
    write_result(f"answers_{args.label}", result)
    print(f"wrote {out_path.relative_to(PROJECT_ROOT)} and {write_spot_check(rows, args.label)}")


if __name__ == "__main__":
    main()
