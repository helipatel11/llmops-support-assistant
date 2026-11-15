import json
import os
import urllib.request

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from app import config
from app.logging_config import logger
from app.monitoring.metrics import LATENCY_BUCKETS, build_info, rag_index_ok
from app.services.index import check_index
from app.services.predict import model_meta, predict_priority
from app.services.rag import RAGUnavailable, ask_question

app = FastAPI(title="LLMOps Support Assistant")

# RED metrics per endpoint. Buckets sized for LLM latency (default stops at 1 s).
Instrumentator(excluded_handlers=["/metrics"]).instrument(
    app, latency_lowr_buckets=LATENCY_BUCKETS
).expose(app)

RAG_VERSIONS = {
    "prompt": config.PROMPT_VERSION,
    "retrieval": config.RETRIEVAL_VERSION,
    "generation": config.GENERATION_VERSION,
    "llm": config.OLLAMA_MODEL,
}

build_info.info({
    "git_sha": os.getenv("GIT_SHA", "unknown"),
    "classifier": model_meta["version"],
    **{k: str(v) for k, v in RAG_VERSIONS.items()},
})
# Known at startup, so the dashboard shows a broken index before the first /ask fails.
rag_index_ok.set(1 if check_index()["ok"] else 0)

for name in config.IGNORED_ENV:
    logger.warning("%s is set but ignored; the LLM comes from configs/generation_%s.json "
                   "(select another version with GENERATION_VERSION)",
                   name, config.GENERATION_VERSION)


@app.exception_handler(RAGUnavailable)
def rag_unavailable(request: Request, exc: RAGUnavailable):
    """A dependency is down: answer 503 (retryable, alertable), not an unhandled 500."""
    return JSONResponse(
        status_code=503,
        content={"detail": "RAG assistant temporarily unavailable",
                 "stage": exc.stage, "error": exc.error_type},
    )


class TicketRequest(BaseModel):
    text: str


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def root():
    return {"message": "running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


def ollama_status() -> dict:
    """Is Ollama reachable, and does it have the models this release is configured for?"""
    url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            names = {m["name"] for m in json.load(resp).get("models", [])}
    except (OSError, ValueError) as exc:
        return {"reachable": False, "error": type(exc).__name__}
    available = names | {n.removesuffix(":latest") for n in names}
    wanted = [config.OLLAMA_MODEL, config.EMBEDDING_MODEL]
    return {"reachable": True, "missing_models": [m for m in wanted if m not in available]}


@app.get("/ready")
def ready():
    """Readiness: should this pod receive traffic?

    Fails only for problems that are this pod's (or this release's) own fault: a broken
    index, or an LLM/embedding model that Ollama doesn't have (a config typo in this
    release). Ollama being unreachable does NOT fail readiness: it is shared by every pod,
    so failing would remove all pods from the Service and take /predict down with /ask.
    """
    index = check_index()
    rag_index_ok.set(1 if index["ok"] else 0)
    ollama = ollama_status()
    problems = []
    if not index["ok"]:
        problems.append(f"index: {index['reason']}")
    if ollama.get("missing_models"):
        problems.append(f"ollama is missing models: {', '.join(ollama['missing_models'])}")
    body = {"ready": not problems, "problems": problems, "index_ok": index["ok"],
            "ollama": ollama}
    return JSONResponse(status_code=200 if not problems else 503, content=body)


@app.get("/version")
def version():
    """What exactly is running: image commit, model/prompt/retrieval versions, index state."""
    index = check_index()
    rag_index_ok.set(1 if index["ok"] else 0)
    return {
        "git_sha": os.getenv("GIT_SHA", "unknown"),
        "classifier": {
            "version": model_meta["version"],
            "mlflow_run_id": model_meta.get("mlflow_run_id"),
            "mlflow_registered_version": model_meta.get("mlflow_registered_version"),
        },
        "rag": {**RAG_VERSIONS, "embedding_model": config.EMBEDDING_MODEL,
                "top_k": config.RETRIEVER_K},
        "index": {"ok": index["ok"], "index_id": index["found"], "expected": index["expected"],
                  "reason": index["reason"]},
    }


@app.post("/predict")
def predict(request: TicketRequest):
    prediction = predict_priority(request.text)

    return {
        "text": request.text,
        "prediction": prediction,
        "versions": {"classifier": model_meta["version"]},
    }


@app.post("/ask")
def ask(request: QuestionRequest):
    answer = ask_question(request.question)

    return {
        "question": request.question,
        "answer": answer,
        "versions": RAG_VERSIONS,
    }
