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
    assert body["versions"] == {"classifier": "v1"}


def test_predict_rejects_missing_text(client):
    response = client.post("/predict", json={})

    assert response.status_code == 422


def test_ask_builds_prompt_from_retrieved_context(client, fake_rag):
    response = client.post("/ask", json={"question": "How do I reset my password?"})

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "How do I reset my password?"
    assert body["answer"] == "Use the forgot password page."
    assert body["versions"] == {
        "prompt": "v1", "retrieval": "v1", "generation": "v1", "llm": "tinyllama",
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


def test_version_reports_what_is_running(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc1234")

    body = client.get("/version").json()

    assert body["git_sha"] == "abc1234"
    assert body["classifier"]["version"] == "v1"
    assert body["classifier"]["mlflow_run_id"]
    assert body["rag"]["prompt"] == "v1"
    assert body["rag"]["retrieval"] == "v1"
    assert set(body["index"]) == {"ok", "index_id", "expected", "reason"}


def test_llm_call_has_the_configured_timeout():
    from app import config
    from app.services import rag

    llm = rag.get_llm()
    assert llm.client_kwargs == {"timeout": config.LLM_TIMEOUT_S}
