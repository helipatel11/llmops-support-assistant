# 0001. TF-IDF + logistic regression for ticket priority

**Status:** Accepted

## Context

Tickets need a priority (high / medium / low) fast and cheaply, on the same small CPU node that also runs the LLM. There is no real labelled data, so the evaluation set is synthetic (600 train / 150 test, held-out templates and phrases, 5% label noise in train).

## Decision

A scikit-learn Pipeline: TF-IDF features and logistic regression. It is trained by `training/train.py`, versioned by `configs/classifier_<v>.json`, and tracked in MLflow. v1 uses word unigrams.

## Alternatives

- **Character n-grams (v2):** evaluated; it's a trade-off, not a win. High recall rose 0.27 → 0.40, but medium recall fell 0.60 → 0.43. Kept as an option (`MODEL_VERSION=v2`).
- **Sentence embeddings + classifier:** would likely link unseen phrasings better. It needs an embedding call per ticket (Ollama or a model in the image). Not evaluated.
- **Ask the LLM to classify:** on this node an LLM call takes ~13 s and is the bottleneck (RESULTS §7). It would turn a 4 ms endpoint into a 13 s one.

## Consequences

- `/predict` is fast and cheap: p95 8 ms at 100 req/s on the t3.large, and it saturates around 150–200 req/s.
- **Weakness, measured:** macro F1 0.50; 33 of 45 outages are labelled medium. Unigram TF-IDF can't connect "hard down" or "throwing 503s" to its training vocabulary. That makes it the most valuable thing to improve, and v1 vs v2 shows the choice is a product decision (missed outages vs misrouted tickets), not just a metric.
