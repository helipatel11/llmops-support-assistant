"""Identify which ChromaDB index is on disk, and whether it matches the running config.

ingest writes llm/chroma_db/index_manifest.json. The app compares it with the current
retrieval config and docs before serving, so a store built with a different embedding
model, chunking or document set is caught instead of silently returning wrong chunks.

top_k is deliberately NOT part of the index identity: changing it needs no re-ingest.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app import config

INDEX_FIELDS = ("embedding_model", "chunk_size", "chunk_overlap")
MANIFEST_NAME = "index_manifest.json"


def docs_fingerprint(docs_dir: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(docs_dir.glob("**/*.txt")):
        h.update(path.relative_to(docs_dir).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def index_id(retrieval: dict, docs_sha: str) -> str:
    """Short hash of everything that determines the index contents."""
    identity = {field: retrieval[field] for field in INDEX_FIELDS}
    identity["docs_sha256"] = docs_sha
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]


def manifest_path(chroma_dir: Path) -> Path:
    return chroma_dir / MANIFEST_NAME


def write_manifest(chroma_dir: Path, retrieval: dict, docs_dir: Path, chunks: int) -> dict:
    docs_sha = docs_fingerprint(docs_dir)
    manifest = {
        "index_id": index_id(retrieval, docs_sha),
        "built_with_retrieval_version": retrieval["version"],
        **{field: retrieval[field] for field in INDEX_FIELDS},
        "docs_sha256": docs_sha,
        "chunks": chunks,
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path(chroma_dir).write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def check_index(
    chroma_dir: Path = config.CHROMA_DIR,
    retrieval: dict = config.RETRIEVAL,
    docs_dir: Path = config.DOCS_DIR,
) -> dict:
    """Return {"ok": bool, "expected": id, "found": id or None, "reason": str}."""
    expected = index_id(retrieval, docs_fingerprint(docs_dir))
    path = manifest_path(chroma_dir)
    if not path.exists():
        return {"ok": False, "expected": expected, "found": None,
                "reason": f"no index manifest at {path}; run: python -m llm.rag.ingest"}
    found = json.loads(path.read_text())
    if found.get("index_id") != expected:
        return {"ok": False, "expected": expected, "found": found.get("index_id"),
                "reason": "index was built with a different embedding model, chunking or docs "
                          f"(built for retrieval {found.get('built_with_retrieval_version')}); "
                          "re-run ingest"}
    return {"ok": True, "expected": expected, "found": expected, "reason": ""}
