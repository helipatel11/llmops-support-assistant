import os

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

from app import config
from app.logging_config import logger
from app.services.index import check_index
from app.services.predict import model_meta, predict_priority
from app.services.rag import ask_question

app = FastAPI(title="LLMOps Support Assistant")

Instrumentator().instrument(app).expose(app)

RAG_VERSIONS = {
    "prompt": config.PROMPT_VERSION,
    "retrieval": config.RETRIEVAL_VERSION,
    "generation": config.GENERATION_VERSION,
    "llm": config.OLLAMA_MODEL,
}

for name in config.IGNORED_ENV:
    logger.warning("%s is set but ignored; the LLM comes from configs/generation_%s.json "
                   "(select another version with GENERATION_VERSION)",
                   name, config.GENERATION_VERSION)


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


@app.get("/version")
def version():
    """What exactly is running: image commit, model/prompt/retrieval versions, index state."""
    index = check_index()
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
