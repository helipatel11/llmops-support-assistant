"""Local LLM-as-judge for answer quality, with evidence that is checked in code.

History (see docs/RESULTS.md): a single holistic prompt collapsed groundedness and
correctness into one impression; a "list unsupported claims" prompt just echoed the
answer back. This version makes the judge cite evidence, and code verifies it:

- Groundedness: the judge splits the answer into claims and, for each, copies the
  supporting sentence from the context. A claim counts as supported only if the judge
  says so AND the quote is actually found in the context.
- Correctness: key facts are fixed per question in the golden set (the judge does not
  choose them). For each fact the judge says present/absent and quotes the answer;
  a fact counts only if that quote is actually found in the answer.
- Scores are computed in code. Refusals are scored by rule and never judged.
- Check the judge with evaluation/judge_calibration.py before trusting its scores.
"""

import json
import re
from difflib import SequenceMatcher

from langchain_ollama import ChatOllama

from app import config

REFUSAL_MARKER = "could not find this information"

GROUNDEDNESS_PROMPT = """You verify an answer against a source text, claim by claim.

SOURCE TEXT:
{context}

ANSWER:
{answer}

Split the ANSWER into its separate factual claims. For each claim:
- "evidence": copy, word for word, the sentence from the SOURCE TEXT that states it,
  or "" if no sentence in the SOURCE TEXT states it.
- "supported": true only if that evidence says the same thing as the claim
  (same numbers, same meaning). Otherwise false.

Reply with JSON only:
{{"claims": [{{"claim": "...", "evidence": "...", "supported": true}}]}}"""

CORRECTNESS_PROMPT = """You check whether an answer states each of a list of required facts.

ANSWER:
{answer}

REQUIRED FACTS:
{facts}

For each required fact, in order:
- "present": true if the ANSWER states this fact (wording may differ, meaning and
  numbers must match; "five" equals "5"), otherwise false.
- "quote": the words from the ANSWER that state it, copied exactly, or "" if absent.
Also set "contradiction" to true if the ANSWER says anything that contradicts a required fact.

Reply with JSON only, filling in every one of the {n} entries below:
{skeleton}"""


def _facts_skeleton(n: int) -> str:
    """JSON template with exactly n entries; small models copy the shape of the example."""
    items = ", ".join(f'{{"id": {i}, "present": ?, "quote": "?"}}' for i in range(1, n + 1))
    return f'{{"facts": [{items}], "contradiction": ?}}'


def is_refusal(answer: str) -> bool:
    return REFUSAL_MARKER in answer.lower()


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9%]+", " ", text.lower()).strip()


def _fragment_found(fragment: str, source: str, min_cover: float = 0.8) -> bool:
    """True if `fragment` (or at least 80% of it, contiguously) appears in `source`."""
    if fragment in source:
        return True
    match = SequenceMatcher(None, fragment, source, autojunk=False).find_longest_match(
        0, len(fragment), 0, len(source)
    )
    return match.size >= min_cover * len(fragment)


def quote_found(quote: str, source: str) -> bool:
    """True if every sentence/bullet fragment of `quote` appears in `source`.

    Judges often stitch a list heading to a bullet further down, or join sentences
    from two chunks. Each piece is real text, so each piece is checked separately;
    an invented fragment still fails. Fragments under 3 words are ignored.
    """
    source_n = _norm(source)
    fragments = [_norm(f) for f in re.split(r"[\n:;]|(?<=[.!?])\s+|\s-\s", quote)]
    fragments = [f for f in fragments if len(f.split()) >= 3]
    return bool(fragments) and all(_fragment_found(f, source_n) for f in fragments)


class Judge:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.llm = ChatOllama(
            model=model, temperature=0, seed=42, format="json",
            base_url=config.OLLAMA_BASE_URL,
        )

    def _ask(self, prompt: str) -> dict:
        return json.loads(self.llm.invoke(prompt).content)

    def groundedness(self, context: str, answer: str) -> dict:
        out = self._ask(GROUNDEDNESS_PROMPT.format(context=context, answer=answer))
        claims = [c for c in out.get("claims", []) if isinstance(c, dict)]
        unsupported = [
            str(c.get("claim", ""))
            for c in claims
            if not (c.get("supported") is True and quote_found(str(c.get("evidence", "")), context))
        ]
        if not claims:
            return {"grounded": None, "error": "judge returned no claims"}
        return {"grounded": 0 if unsupported else 1, "claims": len(claims),
                "unsupported_claims": unsupported}

    def correctness(self, key_facts: list[str], answer: str) -> dict:
        facts_text = "\n".join(f"{i}. {f}" for i, f in enumerate(key_facts, 1))
        out = self._ask(CORRECTNESS_PROMPT.format(
            answer=answer, facts=facts_text, n=len(key_facts),
            skeleton=_facts_skeleton(len(key_facts)),
        ))
        verdicts = [v for v in out.get("facts", []) if isinstance(v, dict)]
        present = sum(
            1 for v in verdicts[: len(key_facts)]
            if v.get("present") is True and quote_found(str(v.get("quote", "")), answer)
        )
        contradiction = out.get("contradiction") is True
        total = len(key_facts)
        if contradiction or present == 0:
            score = 0
        elif present == total:
            score = 2
        else:
            score = 1
        return {"correct": score, "facts_present": present, "facts_total": total,
                "contradiction": contradiction}

    def score(self, context: str, key_facts: list[str], answer: str) -> dict:
        if is_refusal(answer):
            return {"grounded": 1, "correct": 0, "rule": "refusal"}
        try:
            return {**self.groundedness(context, answer), **self.correctness(key_facts, answer)}
        except (ValueError, TypeError, AttributeError) as exc:
            return {"grounded": None, "correct": None, "error": f"unparseable judge output: {exc}"}
