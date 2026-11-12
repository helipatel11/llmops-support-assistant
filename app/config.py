"""Runtime settings, read once from environment variables (or a local .env file)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ollama (LLM + embeddings)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

# Retrieval
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / "llm" / "chroma_db"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "llm" / "docs"))
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "2"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Classifier artifacts
MODEL_DIR = Path(os.getenv("MODEL_DIR", PROJECT_ROOT / "training" / "models"))
MODEL_PATH = MODEL_DIR / "model.pkl"
VECTORIZER_PATH = MODEL_DIR / "vectorizer.pkl"
