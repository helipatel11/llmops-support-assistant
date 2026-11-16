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


def test_generation_deadline_covers_the_whole_streamed_answer(client, fake_rag, monkeypatch):
    """Each chunk arrives quickly, but the whole answer takes longer than the deadline:
    must fail (503), not pass because no single read was slow (Phase 5 drill finding)."""
    from app import config
    from app.services import rag

    clock = iter(range(0, 100, 2))  # every chunk "takes" 2 s
    monkeypatch.setattr(rag.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(config, "LLM_TIMEOUT_S", 3)
    closed = []

    class SlowStreamLLM:
        def stream(self, prompt):
            def chunks():
                try:
                    for word in ["a", " b", " c", " d"]:
                        yield type("C", (), {"content": word})()
                finally:
                    closed.append(True)
            return chunks()

    monkeypatch.setattr(rag, "get_llm", lambda: SlowStreamLLM())
    response = client.post("/ask", json={"question": "anything"})

    assert response.status_code == 503
    assert response.json() == {"detail": "RAG assistant temporarily unavailable",
                               "stage": "generation", "error": "LLMDeadlineExceeded"}
    assert closed  # stream closed: Ollama connection dropped, generation stops
