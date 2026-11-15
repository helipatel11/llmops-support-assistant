"""Metrics behave as the dashboard assumes (no Ollama or ChromaDB needed)."""

from prometheus_client import REGISTRY

from app.services import rag


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_ask_records_both_stages_and_answered_outcome(client, fake_rag):
    before = {
        "answered": sample("rag_requests_total", outcome="answered"),
        "retrieval": sample("rag_stage_duration_seconds_count", stage="retrieval"),
        "generation": sample("rag_stage_duration_seconds_count", stage="generation"),
    }

    assert client.post("/ask", json={"question": "reset password?"}).status_code == 200

    assert sample("rag_requests_total", outcome="answered") == before["answered"] + 1
    for stage in ("retrieval", "generation"):
        count = sample("rag_stage_duration_seconds_count", stage=stage)
        assert count == before[stage] + 1


def test_declined_answer_is_counted_as_declined(client, fake_rag):
    fake_rag.llm.answer = "I could not find this information in the knowledge base."
    before = sample("rag_requests_total", outcome="declined")

    client.post("/ask", json={"question": "What is Terraform?"})

    assert sample("rag_requests_total", outcome="declined") == before + 1


def test_llm_down_returns_503_and_counts_generation_error(client, fake_rag, monkeypatch):
    def ollama_down(prompt):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(fake_rag.llm, "stream", ollama_down)
    before = sample("rag_errors_total", stage="generation", error="ConnectionError")

    response = client.post("/ask", json={"question": "reset password?"})

    assert response.status_code == 503
    assert response.json()["stage"] == "generation"
    assert sample("rag_errors_total", stage="generation", error="ConnectionError") == before + 1


def test_retrieval_failure_returns_503_with_retrieval_stage(client, monkeypatch):
    def broken_index():
        raise RuntimeError("ChromaDB index mismatch")

    monkeypatch.setattr(rag, "get_vectordb", broken_index)
    before = sample("rag_requests_total", outcome="error")

    response = client.post("/ask", json={"question": "anything"})

    assert response.status_code == 503
    assert response.json()["stage"] == "retrieval"
    assert sample("rag_requests_total", outcome="error") == before + 1


def test_prediction_counter_carries_model_version(client):
    before = sample("ml_predictions_total", priority="high", model_version="v1")
    client.post("/predict", json={"text": "URGENT: payment API is completely down for all users"})
    after = sum(
        sample("ml_predictions_total", priority=p, model_version="v1")
        for p in ("high", "medium", "low")
    )
    assert after >= before + 1


def test_metrics_endpoint_exposes_build_info_index_health_and_llm_buckets(client):
    client.get("/health")
    text = client.get("/metrics").text

    assert 'app_build_info{' in text and 'prompt="v1"' in text
    assert "rag_index_ok" in text
    # latency buckets reach far beyond the library default of 1 s
    assert 'http_request_duration_seconds_bucket{handler="/health",le="13.0"' in text
    # /metrics itself is not instrumented (it would dominate request counts)
    assert 'handler="/metrics"' not in text
