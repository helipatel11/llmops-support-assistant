# Uses ./venv if present, otherwise the python on PATH (e.g. in CI).
PYTHON ?= $(if $(wildcard venv/bin/python),venv/bin/python,python)
# Name for result files: evaluation/results/<kind>_$(LABEL).json
LABEL ?= current

.PHONY: help install lint test data train ingest \
        eval eval-classifier eval-retrieval eval-judge eval-answers spot-check

help:
	@echo "install          install runtime + dev dependencies"
	@echo "lint / test      ruff / pytest"
	@echo "data             regenerate the synthetic ticket dataset (seeded)"
	@echo "train            train the classifier, log to MLflow"
	@echo "ingest           rebuild ChromaDB from llm/docs (needs Ollama)"
	@echo "eval             all evaluations (needs Ollama: tinyllama, nomic-embed-text, llama3)"
	@echo "eval-classifier  classifier only (no Ollama needed)"
	@echo "eval-judge       test the LLM judge on cases with known labels"
	@echo "spot-check       judge vs human agreement, after filling the spot-check CSV"
	@echo "Set LABEL=v2 to name result files, e.g. make eval LABEL=v2"

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest -q

data:
	$(PYTHON) -m training.generate_data

train:
	$(PYTHON) -m training.train

ingest:
	$(PYTHON) -m llm.rag.ingest

eval-classifier:
	$(PYTHON) -m evaluation.classifier_eval --label $(LABEL)

eval-retrieval:
	$(PYTHON) -m evaluation.retrieval_eval --label $(LABEL)

eval-judge:
	$(PYTHON) -m evaluation.judge_calibration

eval-answers:
	$(PYTHON) -m evaluation.answer_eval --label $(LABEL)

eval: eval-classifier ingest eval-retrieval eval-judge eval-answers

spot-check:
	$(PYTHON) -m evaluation.spot_check_agreement --label $(LABEL)
