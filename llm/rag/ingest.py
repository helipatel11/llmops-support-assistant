"""Build the ChromaDB vector store from the support docs.

Run from the repo root:  python -m llm.rag.ingest
The store is rebuilt from scratch each time, so re-running never duplicates chunks.
"""

import shutil

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app import config
from app.services.index import write_manifest


def main() -> None:
    loader = DirectoryLoader(str(config.DOCS_DIR), glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    print(f"Loaded {len(documents)} documents from {config.DOCS_DIR}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    embedding = OllamaEmbeddings(
        model=config.EMBEDDING_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )

    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)

    # chromadb >= 0.4 persists automatically; no .persist() call needed.
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=str(config.CHROMA_DIR),
    )
    manifest = write_manifest(config.CHROMA_DIR, config.RETRIEVAL, config.DOCS_DIR, len(chunks))
    print(f"ChromaDB written to {config.CHROMA_DIR} "
          f"(index {manifest['index_id']}, retrieval {config.RETRIEVAL_VERSION})")


if __name__ == "__main__":
    main()
