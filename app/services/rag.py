from functools import lru_cache
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app import config
from app.logging_config import logger
from app.monitoring.metrics import rag_requests_counter
from app.services.index import check_index


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
        temperature=0,
        base_url=config.OLLAMA_BASE_URL,
    )


def retrieve(question: str, k: Optional[int] = None) -> list:
    """Return the top-k chunks for a question, most similar first."""
    return get_vectordb().similarity_search(question, k=k or config.RETRIEVER_K)


def generate(question: str, docs: list) -> str:
    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = load_prompt(config.PROMPT_VERSION).format(context=context, question=question)
    return get_llm().invoke(prompt).content


def ask_question(question: str) -> str:
    logger.info("Question received (%d chars)", len(question))

    rag_requests_counter.inc()

    docs = retrieve(question)

    logger.info("Retrieved %d docs", len(docs))

    return generate(question, docs)
