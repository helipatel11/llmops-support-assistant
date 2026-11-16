# 0002. ChromaDB, built inside each pod at startup

**Status:** Accepted

## Context

The knowledge base is small (18 docs → 36 chunks). The original setup kept the ChromaDB directory on a laptop: it was gitignored and missing from the image, so `/ask` in k3s retrieved **zero documents** (Phase 0 audit). An index can also go stale silently, when it was built with a different embedding model, chunking or document set than the running config.

## Decision

- An init container (`python -m llm.rag.ingest`) builds the index into an `emptyDir` each time a pod starts.
- Ingest writes a manifest that fingerprints the embedding model, chunk size and overlap, and the documents.
- The API checks the manifest against its retrieval config. It refuses `/ask` on a mismatch, reports `rag_index_ok`, and fails `/ready`.

## Alternatives

- **Bake the index into the image:** the build would need Ollama for embeddings, and the CI runners don't have it.
- **A shared ChromaDB server or a managed vector DB:** another service to run, secure and pay for. That's justified for millions of chunks, not 36.
- **A persistent volume:** pods would share state, and the index could drift from the image's docs.

## Consequences

- The index always matches the image's documents and config. A broken index is visible before the first `/ask` fails.
- Each pod pays a few seconds of embedding calls at startup, and needs Ollama reachable to start. It also slows rollbacks after a completed rollout: 83–88 s in the drill (RESULTS §9).
- It doesn't scale to a large corpus. The fix then is a shared vector store with the same manifest check.
