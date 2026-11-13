"""Application metrics, exposed at /metrics for Prometheus.

HTTP RED metrics (rate, errors, duration per endpoint) come from
prometheus-fastapi-instrumentator in app/main.py. The metrics here add what HTTP
metrics cannot see: where time goes inside /ask, how answers end, index health,
and which versions are running.

Label cardinality: every label combination is a separate time series. Versions are
therefore NOT added to every metric; they live on one info metric (app_build_info)
that dashboards join on. Only the classifier version is on the prediction counter,
so a rollout can be compared by prediction mix (3 priorities x a few versions).
"""

from prometheus_client import Counter, Gauge, Histogram, Info

# /ask takes ~0.05 s (retrieval) to 10+ s (generation on CPU); the library default
# (0.1, 0.5, 1) would put every LLM request in the "> 1 s" bucket.
LATENCY_BUCKETS = (0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 3, 5, 8, 13, 20, 30, 60)

prediction_counter = Counter(
    "ml_predictions_total",
    "Classifier predictions, by predicted priority and model version",
    ["priority", "model_version"],
)

rag_requests_counter = Counter(
    "rag_requests_total",
    "RAG /ask requests by outcome: answered, declined (refused to answer) or error",
    ["outcome"],
)

rag_stage_seconds = Histogram(
    "rag_stage_duration_seconds",
    "Time spent in each /ask stage: retrieval (embed + vector search) or generation (LLM)",
    ["stage"],
    buckets=LATENCY_BUCKETS,
)

rag_errors_counter = Counter(
    "rag_errors_total",
    "RAG failures by stage (retrieval or generation) and exception type",
    ["stage", "error"],
)

rag_index_ok = Gauge(
    "rag_index_ok",
    "1 if the on-disk ChromaDB index matches the running retrieval config, else 0",
)

build_info = Info(
    "app_build",
    "Running build and model/prompt/retrieval/generation versions (value is always 1)",
)
