import time
from functools import lru_cache
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app import config
from app.logging_config import logger
from app.monitoring.metrics import (
    rag_errors_counter,
    rag_index_ok,
    rag_requests_counter,
    rag_stage_seconds,
)
from app.services.index import check_index
from app.services.refusal import is_refusal


class RAGUnavailable(Exception):
    """A dependency of /ask failed (index, embeddings or LLM); the API returns 503."""

    def __init__(self, stage: str, error: Exception):
        super().__init__(f"{stage} failed: {type(error).__name__}: {error}")
        self.stage = stage
        self.error_type = type(error).__name__


@lru_cache(maxsize=None)
def load_prompt(version: str) -> str:
    """Prompt templates live in prompts/rag_<version>.txt, with {context} and {question}."""
    return (config.PROMPTS_DIR / f"rag_{version}.txt").read_text()


@lru_cache(maxsize=1)
def get_vectordb():
    """Open the persisted ChromaDB collection on first use, not at import time.

    Refuses to serve from an index built with a different embedding model, chunking
    or document set than the running retrieval config (see app/services/index.py).
    """
    status = check_index()
    rag_index_ok.set(1 if status["ok"] else 0)
    if not status["ok"]:
        raise RuntimeError(f"ChromaDB index mismatch: {status['reason']}")
    embedding = OllamaEmbeddings(
        model=config.EMBEDDING_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )
    return Chroma(
        persist_directory=str(config.CHROMA_DIR),
        embedding_function=embedding,
    )


@lru_cache(maxsize=1)
def get_llm():
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        temperature=config.LLM_TEMPERATURE,
        base_url=config.OLLAMA_BASE_URL,
        client_kwargs={"timeout": config.LLM_TIMEOUT_S},
    )


def retrieve(question: str, k: Optional[int] = None) -> list:
    """Return the top-k chunks for a question, most similar first."""
    return get_vectordb().similarity_search(question, k=k or config.RETRIEVER_K)


class LLMDeadlineExceeded(TimeoutError):
    pass


def generate(question: str, docs: list) -> str:
    """Stream the answer and enforce a deadline on the WHOLE call.

    The HTTP client's timeout only limits each wait for the next chunk; with a streamed
    answer it resets on every token, so a 12 s answer passed a "5 s timeout" (found in
    the Phase 5 rollback drill). Closing the stream at the deadline drops the connection,
    so Ollama stops generating instead of burning CPU on an answer nobody receives.
    """
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = load_prompt(config.PROMPT_VERSION).format(context=context, question=question)
    deadline = time.monotonic() + config.LLM_TIMEOUT_S
    parts = []
    stream = get_llm().stream(prompt)
    try:
        for chunk in stream:
            parts.append(chunk.content)
            if time.monotonic() > deadline:
                raise LLMDeadlineExceeded(f"no complete answer within {config.LLM_TIMEOUT_S} s")
    finally:
        stream.close()
    return "".join(parts)


def _timed(stage: str, fn, *args):
    """Run one /ask stage, record its duration, and turn failures into RAGUnavailable."""
    start = time.perf_counter()
    try:
        return fn(*args)
    except Exception as exc:  # any dependency failure: index, Ollama, network
        rag_errors_counter.labels(stage=stage, error=type(exc).__name__).inc()
        rag_requests_counter.labels(outcome="error").inc()
        logger.error("RAG %s failed: %s: %s", stage, type(exc).__name__, exc)
        raise RAGUnavailable(stage, exc) from exc
    finally:
        rag_stage_seconds.labels(stage=stage).observe(time.perf_counter() - start)


def ask_question(question: str) -> str:
    logger.info("Question received (%d chars)", len(question))

    docs = _timed("retrieval", retrieve, question)
    logger.info("Retrieved %d docs", len(docs))

    answer = _timed("generation", generate, question, docs)

    rag_requests_counter.labels(outcome="declined" if is_refusal(answer) else "answered").inc()
    return answer
