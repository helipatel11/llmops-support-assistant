from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import rag


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []

    def invoke(self, question):
        self.queries.append(question)
        return [SimpleNamespace(page_content=d) for d in self.docs]


class FakeLLM:
    def __init__(self, answer="fake answer"):
        self.answer = answer
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.answer)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_rag(monkeypatch):
    """Replace ChromaDB and Ollama so /ask tests need no external services."""
    retriever = FakeRetriever(["Users can reset passwords using the forgot password page."])
    llm = FakeLLM("Use the forgot password page.")
    monkeypatch.setattr(rag, "get_retriever", lambda: retriever)
    monkeypatch.setattr(rag, "get_llm", lambda: llm)
    return SimpleNamespace(retriever=retriever, llm=llm)
