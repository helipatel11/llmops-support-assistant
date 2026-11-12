import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("llmops-app")
# One INFO line per Ollama HTTP call is noise in pod logs and eval output.
logging.getLogger("httpx").setLevel(logging.WARNING)
