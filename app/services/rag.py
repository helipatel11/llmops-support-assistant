from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
import os
from app.monitoring.metrics import rag_requests_counter
from app.logging_config import logger

# Embeddings
embedding = OllamaEmbeddings(
    
    model="nomic-embed-text",

    base_url=os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )
)


# Vector DB
vectordb = Chroma(
    persist_directory="llm/chroma_db",
    embedding_function=embedding
)

retriever = vectordb.as_retriever(
    search_kwargs={"k": 2}
)
# Local LLM

llm = ChatOllama(
    # model="llama3",
    model="tinyllama",
    temperature=0,
    base_url=os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )
)

def ask_question(question: str):
    logger.info(f"Question received: {question}")

    rag_requests_counter.inc()   
    
    docs = retriever.invoke(question)

    logger.info(f"Retrieved {len(docs)} docs")

    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    prompt = f"""
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

    response = llm.invoke(prompt)

    return response.content