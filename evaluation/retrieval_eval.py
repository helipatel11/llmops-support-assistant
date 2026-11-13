"""Evaluate retrieval on the golden question set: hit@k and MRR.

Run from the repo root (needs Ollama for embeddings and an ingested ChromaDB):
    python -m evaluation.retrieval_eval [--label NAME]
Writes evaluation/results/retrieval_<label>.json

A question is a hit@k if any of the top-k chunks comes from its expected doc.
Reciprocal rank = 1 / rank of the first chunk from the expected doc (0 if not in top MAX_K).
"""

import argparse
import json
from pathlib import Path
from statistics import mean

from app import config
from app.services.index import check_index
from app.services.rag import get_vectordb
from evaluation.common import PROJECT_ROOT, file_sha256, run_metadata, write_result

GOLDEN = PROJECT_ROOT / "evaluation" / "golden_questions.jsonl"
KS = [1, 2, 3, 5]
MAX_K = max(KS)


def load_golden() -> list[dict]:
    return [json.loads(line) for line in GOLDEN.read_text().splitlines() if line.strip()]


def evaluate() -> dict:
    db = get_vectordb()
    chunk_count = db._collection.count()
    if chunk_count == 0:
        raise SystemExit("ChromaDB is empty. Run: python -m llm.rag.ingest")

    rows = []
    for q in load_golden():
        results = db.similarity_search_with_score(q["question"], k=MAX_K)
        sources = [Path(doc.metadata.get("source", "")).name for doc, _ in results]
        row = {
            "id": q["id"],
            "answerable": q["answerable"],
            "expected_doc": q["expected_doc"],
            "retrieved": sources,
            "top1_distance": round(float(results[0][1]), 4) if results else None,
        }
        if q["answerable"]:
            rank = next(
                (i + 1 for i, s in enumerate(sources) if s == q["expected_doc"]), None
            )
            row["rank"] = rank
            row["reciprocal_rank"] = round(1 / rank, 4) if rank else 0.0
        rows.append(row)

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    hit_at = {
        f"hit@{k}": round(mean(1 if r["rank"] and r["rank"] <= k else 0 for r in answerable), 4)
        for k in KS
    }

    return {
        "metadata": run_metadata(),
        "versions": {
            "retrieval": config.RETRIEVAL_VERSION,
            "index_id": check_index()["found"],
        },
        "config": {
            "embedding_model": config.EMBEDDING_MODEL,
            "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP,
            "serving_top_k": config.RETRIEVER_K,
            "chunks_in_collection": chunk_count,
        },
        "dataset": {
            "path": str(GOLDEN.relative_to(PROJECT_ROOT)),
            "answerable": len(answerable),
            "unanswerable": len(unanswerable),
            "sha256": file_sha256(GOLDEN),
        },
        **hit_at,
        f"mrr@{MAX_K}": round(mean(r["reciprocal_rank"] for r in answerable), 4),
        "top1_distance": {
            "note": "Chroma L2 distance, lower = more similar",
            "answerable_mean": round(mean(r["top1_distance"] for r in answerable), 4),
            "answerable_max": max(r["top1_distance"] for r in answerable),
            "unanswerable_mean": round(mean(r["top1_distance"] for r in unanswerable), 4),
            "unanswerable_min": min(r["top1_distance"] for r in unanswerable),
        },
        "misses_at_serving_k": [
            r for r in answerable if not r["rank"] or r["rank"] > config.RETRIEVER_K
        ],
        "per_question": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current")
    args = parser.parse_args()

    result = evaluate()
    print("  ".join(f"{k}={result[k]}" for k in [f"hit@{k}" for k in KS] + [f"mrr@{MAX_K}"]))
    print("top-1 distance:", {k: v for k, v in result["top1_distance"].items() if k != "note"})
    for r in result["misses_at_serving_k"]:
        print(f"  miss {r['id']}: expected {r['expected_doc']}, got {r['retrieved'][:3]}")
    path = write_result(f"retrieval_{args.label}", result)
    print(f"wrote {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
