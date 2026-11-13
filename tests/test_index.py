"""Index manifest: a store built with different settings or docs must be detected."""

import pytest

from app.services.index import check_index, write_manifest

BASE = {"version": "v1", "embedding_model": "nomic-embed-text",
        "chunk_size": 500, "chunk_overlap": 50, "top_k": 2}


@pytest.fixture
def built(tmp_path):
    docs, store = tmp_path / "docs", tmp_path / "store"
    docs.mkdir()
    store.mkdir()
    (docs / "vpn.txt").write_text("Restart the VPN client.")
    write_manifest(store, BASE, docs, chunks=1)
    return docs, store


def test_matching_index_is_ok(built):
    docs, store = built
    assert check_index(store, BASE, docs)["ok"]


def test_top_k_change_needs_no_reingest(built):
    docs, store = built
    assert check_index(store, {**BASE, "version": "v2", "top_k": 3}, docs)["ok"]


@pytest.mark.parametrize("change", [{"chunk_size": 300}, {"chunk_overlap": 0},
                                    {"embedding_model": "other-embedder"}])
def test_index_settings_change_is_detected(built, change):
    docs, store = built
    status = check_index(store, {**BASE, **change}, docs)
    assert not status["ok"]
    assert "re-run ingest" in status["reason"]


def test_edited_docs_are_detected(built):
    docs, store = built
    (docs / "vpn.txt").write_text("Restart the VPN client, then reboot.")
    assert not check_index(store, BASE, docs)["ok"]


def test_missing_manifest_is_reported(tmp_path):
    status = check_index(tmp_path / "empty", BASE, tmp_path)
    assert not status["ok"]
    assert status["found"] is None
