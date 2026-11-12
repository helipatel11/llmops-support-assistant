from functools import lru_cache
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app import config
from app.logging_config import logger
from app.monitoring.metrics import rag_requests_counter

PROMPT_TEMPLATE = """
You are an IT support assistant.

Answer ONLY from the provided context.

If the answer is not present in the context, reply:

"I could not find this information in the knowledge base."

Context:
{context}

Question:
{question}

Answer:
"""


@lru_cache(maxsize=1)
def get_vectordb():
    """Open the persisted ChromaDB collection on first use, not at import time."""
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
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)
    return get_llm().invoke(prompt).content


def ask_question(question: str) -> str:
    logger.info("Question received (%d chars)", len(question))

    rag_requests_counter.inc()

    docs = retrieve(question)

    logger.info("Retrieved %d docs", len(docs))

    return generate(question, docs)
