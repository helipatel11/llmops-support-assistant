"""Runtime settings, read once from environment variables (or a local .env file)."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Versioned configs (configs/<kind>_<version>.json) and prompts (prompts/rag_<version>.txt).
# Env vars only SELECT a version; the settings themselves live in versioned files.
CONFIGS_DIR = Path(os.getenv("CONFIGS_DIR", PROJECT_ROOT / "configs"))
PROMPTS_DIR = Path(os.getenv("PROMPTS_DIR", PROJECT_ROOT / "prompts"))

# Ollama (generation model)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")

# Prompt
PROMPT_VERSION = os.getenv("PROMPT_VERSION", "v1")

# Retrieval: embedding model, chunking and top-k are versioned together.
RETRIEVAL_VERSION = os.getenv("RETRIEVAL_VERSION", "v1")
RETRIEVAL = json.loads((CONFIGS_DIR / f"retrieval_{RETRIEVAL_VERSION}.json").read_text())
EMBEDDING_MODEL = RETRIEVAL["embedding_model"]
CHUNK_SIZE = RETRIEVAL["chunk_size"]
CHUNK_OVERLAP = RETRIEVAL["chunk_overlap"]
RETRIEVER_K = RETRIEVAL["top_k"]
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", PROJECT_ROOT / "llm" / "chroma_db"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", PROJECT_ROOT / "llm" / "docs"))

# Classifier: one sklearn Pipeline file + metadata per version; pick with MODEL_VERSION.
MODEL_DIR = Path(os.getenv("MODEL_DIR", PROJECT_ROOT / "training" / "models"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1")


def classifier_artifact(version: str) -> Path:
    return MODEL_DIR / f"classifier_{version}.joblib"


def classifier_meta(version: str) -> Path:
    return MODEL_DIR / f"classifier_{version}.meta.json"
