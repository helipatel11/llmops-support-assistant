# Dashboard guide: "Support Assistant"

The Grafana dashboard is code: `monitoring/grafana/dashboards/support-assistant.json`, loaded automatically by `docker compose up` (open http://localhost:3000). "Normal" values below come from a local run on 2026-11-13 (Apple M1, 8 GB, tinyllama, gentle demo traffic from `tools/traffic.py`). They are not load-test results; those are Phase 4.

**RED** = **R**ate (requests per second), **E**rrors (failed requests), **D**uration (how long requests take). Duration is shown as percentiles: **p50** is a typical request, **p95** and **p99** are the slow tail that users notice.

## Row 1: Overview

| Panel | Question it answers | Normal | Broken looks like | Check next |
|---|---|---|---|---|
| **Running versions** | Exactly what is deployed? | One row per instance: git SHA, classifier, prompt, retrieval, generation, llm | Two different rows during a rollout (expected for a moment), or the wrong SHA after a deploy | `GET /version`; the deploy pipeline |
| **Vector index OK** | Does the ChromaDB index match the retrieval config? | YES | NO: every `/ask` will fail at retrieval | Run ingest; `GET /version` gives the reason |
| **Requests / s** | Is traffic arriving? | Matches expected traffic | Drops to 0: ingress, DNS or all pods down | Ingress, pod status |
| **Error ratio (5xx)** | What share of requests fail? | 0% | Rose to **26%** in the Ollama outage drill | "Errors by endpoint", then "RAG errors by stage" |

## Row 2: RED per endpoint

| Panel | Normal | Notes |
|---|---|---|
| **Rate by endpoint** | `/predict` ~3× `/ask` (the demo traffic mix) | |
| **Errors by endpoint** | Empty | In the drill only `/ask` errored, while `/predict` stayed healthy: partly degraded, not fully down |
| **Latency p50/p95/p99** | `/predict` 12 / 24 / 25 ms; `/ask` 1.0 / 3.1 / 4.6 s | Percentiles are **estimated** from histogram buckets (…, 3, 5, 8 s…), so 3.1 s means "between 3 and 5 s". Buckets go up to 60 s; the library default stopped at 1 s and would have hidden all of `/ask`'s slowness |

## Row 3: RAG `/ask`

| Panel | Normal | What it tells you |
|---|---|---|
| **Stage latency p50/p95** | retrieval 65 / 98 ms; generation 1.0 / 2.8 s | Where a slow request spends its time. A one-off retrieval spike (1.3 s) was a cold start: the embedding model loading on first use |
| **Share of /ask time by stage** | generation **≈ 96%** | The LLM is the bottleneck, so speeding up retrieval is pointless |
| **Answer outcomes** | ~55% answered, ~45% declined, 0 errors | A rising **declined** share means the model refuses more often (e.g. a prompt change or a bad index). A rising **error** share means a dependency is failing |

## Row 4: Failures and classifier

| Panel | Normal | Broken looks like |
|---|---|---|
| **RAG errors by stage** | Empty | `retrieval: ConnectionError` in the drill. Embeddings come from Ollama too, so **an Ollama outage fails `/ask` at the first stage** |
| **Predictions by priority and model version** | Mix of high / medium / low for `v1` | A sudden shift after a rollout (e.g. far more "high") suggests the new model behaves differently, even if no errors appear |

## Lessons from the outage drill (2026-11-13)

The app was restarted with Ollama unreachable for 90 s, under demo traffic:

- **Detected in about 30 s** (error ratio, RAG errors panel); the error ratio took about 1 minute to return to 0 after recovery because of the 1-minute rate window.
- **`up` stayed 1 and `/health` kept returning 200 while 100% of `/ask` failed.** Liveness is not the same as working. Phase 5 adds a readiness check that tests the dependencies.
- **Each restart of the single container dropped in-flight requests** (8 got no response). One replica means every deploy or crash drops requests. Phase 5 uses 2+ replicas, readiness probes and rolling updates.

## Design choices

- **Versions on one info metric (`app_build_info`), not on every series:** each label combination is a separate time series, so adding five version labels to every metric multiplies storage and query cost (label cardinality). Dashboards join on the info metric.
- **503, not 500, when a dependency fails:** 503 means "temporarily unavailable, retry", which is the correct signal for clients and alerts; 500 suggests a bug in the app.
- **Dashboard in git:** reviewable, reproducible, and identical on every machine; nothing to rebuild by hand.
