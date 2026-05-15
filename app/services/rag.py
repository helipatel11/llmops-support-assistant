from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
import os


# Embeddings
embedding = OllamaEmbeddings(
    model="llama3",
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
    model="llama3",
    temperature=0,
    base_url=os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434"
    )
)

def ask_question(question: str):

    docs = retriever.invoke(question)

    context = "\n\n".join(
        [doc.page_content for doc in docs]
    )

    prompt = f"""
You are an IT support assistant.

Use ONLY the provided context.

Context:
{context}

Question:
{question}
"""

    response = llm.invoke(prompt)

    return response.content