"""/ready decides whether a pod gets traffic. Only this pod's or this release's own faults
should fail it; a shared dependency being down must not empty the whole Service."""

import pytest

from app import main

INDEX_OK = {"ok": True, "expected": "x", "found": "x", "reason": None}
INDEX_BAD = {"ok": False, "expected": "x", "found": "y", "reason": "index built for chunk_size=500"}


@pytest.fixture
def state(monkeypatch):
    def set_state(index=INDEX_OK, ollama=None):
        monkeypatch.setattr(main, "check_index", lambda: index)
        monkeypatch.setattr(main, "ollama_status",
                            lambda: ollama or {"reachable": True, "missing_models": []})
    return set_state


def test_ready_when_index_ok_and_models_present(client, state):
    state()
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_not_ready_when_index_is_broken(client, state):
    state(index=INDEX_BAD)
    response = client.get("/ready")
    assert response.status_code == 503
    assert "index" in response.json()["problems"][0]


def test_not_ready_when_configured_model_is_missing(client, state):
    """A model-name typo is this release's fault: block it so a rollout stalls safely."""
    state(ollama={"reachable": True, "missing_models": ["tinyllamaa"]})
    response = client.get("/ready")
    assert response.status_code == 503
    assert "tinyllamaa" in response.json()["problems"][0]


def test_still_ready_when_ollama_is_unreachable(client, state):
    """Ollama is shared by all pods; failing here would take /predict down with /ask."""
    state(ollama={"reachable": False, "error": "URLError"})
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ollama"]["reachable"] is False


def test_ollama_status_handles_tag_suffix(monkeypatch):
    """Ollama lists 'tinyllama:latest'; the config says 'tinyllama'."""
    import io
    import json

    payload = {"models": [{"name": "tinyllama:latest"}, {"name": "nomic-embed-text:latest"}]}
    monkeypatch.setattr(main.urllib.request, "urlopen",
                        lambda url, timeout: io.BytesIO(json.dumps(payload).encode()))
    assert main.ollama_status() == {"reachable": True, "missing_models": []}


def test_ollama_status_unreachable(monkeypatch):
    def refuse(url, timeout):
        raise ConnectionRefusedError()
    monkeypatch.setattr(main.urllib.request, "urlopen", refuse)
    assert main.ollama_status() == {"reachable": False, "error": "ConnectionRefusedError"}
