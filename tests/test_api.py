def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_predict_returns_a_known_priority(client):
    response = client.post("/predict", json={"text": "Production server is completely down"})

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "Production server is completely down"
    assert body["prediction"] in {"high", "medium", "low"}


def test_predict_rejects_missing_text(client):
    response = client.post("/predict", json={})

    assert response.status_code == 422


def test_ask_builds_prompt_from_retrieved_context(client, fake_rag):
    response = client.post("/ask", json={"question": "How do I reset my password?"})

    assert response.status_code == 200
    assert response.json() == {
        "question": "How do I reset my password?",
        "answer": "Use the forgot password page.",
    }
    assert fake_rag.retriever.queries == ["How do I reset my password?"]
    prompt = fake_rag.llm.prompts[0]
    assert "forgot password page" in prompt
    assert "How do I reset my password?" in prompt


def test_ask_rejects_missing_question(client, fake_rag):
    response = client.post("/ask", json={})

    assert response.status_code == 422
    assert fake_rag.llm.prompts == []


def test_metrics_exposes_custom_counters(client, fake_rag):
    client.post("/predict", json={"text": "Users cannot access the payment page"})
    client.post("/ask", json={"question": "anything"})

    metrics = client.get("/metrics").text

    assert "ml_predictions_total" in metrics
    assert "rag_requests_total" in metrics
