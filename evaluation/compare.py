"""Compare two evaluation results side by side (markdown table).

Run from the repo root:
    python -m evaluation.compare classifier v1 v2
    python -m evaluation.compare retrieval v1 v2
    python -m evaluation.compare answers v1 gen-llama3
Reads evaluation/results/<kind>_<label>.json for both labels.
"""

import argparse
import json

from evaluation.common import RESULTS_DIR


def classifier_metrics(r: dict) -> dict:
    m = {"accuracy": r["accuracy"], "macro F1": r["macro_f1"]}
    for label, pc in r["per_class"].items():
        m[f"{label} recall"] = pc["recall"]
        m[f"{label} precision"] = pc["precision"]
    return m


def retrieval_metrics(r: dict) -> dict:
    keys = [k for k in r if k.startswith("hit@") or k.startswith("mrr@")]
    m = {k: r[k] for k in keys}
    m["misses at serving k"] = len(r["misses_at_serving_k"])
    return m


def answers_metrics(r: dict) -> dict:
    a, u, lat = r["answerable"], r["unanswerable"], r["latency_s_informal"]
    return {
        "fully correct": a["fully_correct_rate"],
        "mean correctness (0-2)": a["mean_correct_score_0_to_2"],
        "grounded": a["grounded_rate"],
        "false refusals": a["false_refusal_rate"],
        "correct refusals (unanswerable)": u["correct_refusal_rate"],
        "generation median s (informal)": lat["generation_median"],
    }


EXTRACT = {"classifier": classifier_metrics, "retrieval": retrieval_metrics,
           "answers": answers_metrics}


def describe(kind: str, r: dict) -> str:
    if kind == "classifier":
        return f"classifier {r.get('classifier_version', '?')}"
    if kind == "retrieval":
        v = r.get("versions", {})
        return f"retrieval {v.get('retrieval', '?')}, k={r['config']['serving_top_k']}"
    c = r["config"]
    return (f"prompt {c.get('prompt_version', '?')}, retrieval {c.get('retrieval_version', '?')}, "
            f"LLM {c.get('serving_model', '?')}, judge {c.get('judge_model', '?')}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=sorted(EXTRACT))
    parser.add_argument("a")
    parser.add_argument("b")
    args = parser.parse_args()

    ra, rb = (json.loads((RESULTS_DIR / f"{args.kind}_{x}.json").read_text())
              for x in (args.a, args.b))
    ma, mb = EXTRACT[args.kind](ra), EXTRACT[args.kind](rb)

    print(f"A = {args.a}: {describe(args.kind, ra)} (commit {ra['metadata']['git_commit']})")
    print(f"B = {args.b}: {describe(args.kind, rb)} (commit {rb['metadata']['git_commit']})")
    print()
    print(f"| metric | {args.a} | {args.b} | change |")
    print("|---|---|---|---|")
    for key in ma:
        a, b = ma[key], mb.get(key)
        numeric = isinstance(a, (int, float)) and isinstance(b, (int, float))
        delta = f"{b - a:+.4g}" if numeric else ""
        print(f"| {key} | {a} | {b} | {delta} |")


if __name__ == "__main__":
    main()
