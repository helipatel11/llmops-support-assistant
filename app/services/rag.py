from functools import lru_cache

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
def get_retriever():
    """Open the persisted ChromaDB collection on first use, not at import time."""
    embedding = OllamaEmbeddings(
        model=config.EMBEDDING_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )
    vectordb = Chroma(
        persist_directory=str(config.CHROMA_DIR),
        embedding_function=embedding,
    )
    return vectordb.as_retriever(search_kwargs={"k": config.RETRIEVER_K})


@lru_cache(maxsize=1)
def get_llm():
    return ChatOllama(
        model=config.OLLAMA_MODEL,
        temperature=0,
        base_url=config.OLLAMA_BASE_URL,
    )


def ask_question(question: str) -> str:
    logger.info("Question received (%d chars)", len(question))

    rag_requests_counter.inc()

    docs = get_retriever().invoke(question)

    logger.info("Retrieved %d docs", len(docs))

    context = "\n\n".join(doc.page_content for doc in docs)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    response = get_llm().invoke(prompt)

    return response.content
