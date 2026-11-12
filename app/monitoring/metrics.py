from prometheus_client import Counter

prediction_counter = Counter(
    "ml_predictions_total",
    "Total ML predictions",
    ["priority"]
)

rag_requests_counter = Counter(
    "rag_requests_total",
    "Total RAG requests"
)