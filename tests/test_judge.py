"""Unit tests for the judge's deterministic parts (no Ollama needed)."""

import pytest

from evaluation.judge import _facts_skeleton, is_exact_refusal, is_refusal, quote_found

CONTEXT = (
    "Office Wi-Fi\n\nIf a company laptop cannot join Corp:\n"
    "- toggle Wi-Fi off and on\n"
    "- forget the Corp network and reconnect\n"
    "- restart the laptop so the certificate is renewed"
)


@pytest.mark.parametrize(
    "quote, expected",
    [
        ("restart the laptop so the certificate is renewed", True),
        # heading stitched to a bullet further down: each piece is real text
        ("If a company laptop cannot join Corp: - forget the Corp network and reconnect", True),
        ("RESTART the laptop, so the certificate is renewed!", True),  # case/punctuation
        # real heading + invented bullet must fail
        ("If a company laptop cannot join Corp: - call the vendor hotline", False),
        ("Restart your router and call your internet provider.", False),
        ("", False),
        ("Corp", False),  # too short to count as evidence
    ],
)
def test_quote_found(quote, expected):
    assert quote_found(quote, CONTEXT) is expected


@pytest.mark.parametrize(
    "answer, declined, exact",
    [
        ("I could not find this information in the knowledge base.", True, True),
        # real tinyllama paraphrases from the v1 baseline run
        ("The provided context does not contain information about Terraform.", True, False),
        ("The CEO's phone number is not mentioned in the given context.", True, False),
        ("The guest Wi-Fi password today is not available in the knowledge base.", True, False),
        # real answers must not be mistaken for refusals
        ("Restart the VPN client.", False, False),
        ("The VPN disconnects automatically after 12 hours. Reconnect to continue.", False, False),
        ("You cannot get access without manager approval.", False, False),
    ],
)
def test_refusal_detection(answer, declined, exact):
    assert is_refusal(answer) is declined
    assert is_exact_refusal(answer) is exact


def test_facts_skeleton_has_one_entry_per_fact():
    skeleton = _facts_skeleton(3)
    assert skeleton.count('"id":') == 3
    assert '"id": 3' in skeleton
