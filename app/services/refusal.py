"""Detect when an answer declines to answer (used by live metrics and by evaluation)."""

import re

# The exact refusal sentence the prompt asks for (product-facing format).
REFUSAL_MARKER = "could not find this information"
# Paraphrased refusals: small models often decline in their own words. Added after the
# tinyllama baseline, where every unanswerable question was declined but none used the
# exact sentence. Both views are reported: exact format, and declined in any wording.
DECLINE_PATTERNS = [
    REFUSAL_MARKER,
    r"\b(does|do|did) not (mention|contain|include|provide|say|specify)\b",
    r"\bdoesn'?t (mention|contain|include|provide|say|specify)\b",
    r"\bnot (mentioned|present|available|provided|included|specified) in\b",
    r"\bno information (about|on|regarding)\b",
]


def is_exact_refusal(answer: str) -> bool:
    return REFUSAL_MARKER in answer.lower()


def is_refusal(answer: str) -> bool:
    """True if the answer declines to answer, in the exact format or in its own words."""
    text = answer.lower()
    return any(re.search(pattern, text) for pattern in DECLINE_PATTERNS)
