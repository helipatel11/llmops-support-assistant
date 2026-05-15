from fastapi import FastAPI
from pydantic import BaseModel

from app.services.predict import predict_priority
from app.services.rag import ask_question


app = FastAPI(title="LLMOps Support Assistant")


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


@app.post("/predict")
def predict(request: TicketRequest):

    prediction = predict_priority(request.text)

    return {
        "text": request.text,
        "prediction": prediction
    }


@app.post("/ask")
def ask(request: QuestionRequest):

    answer = ask_question(request.question)

    return {
        "question": request.question,
        "answer": answer
    }