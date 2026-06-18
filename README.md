# LLMOps Support Assistant

An end-to-end LLMOps + MLOps project that combines:

- Traditional ML ticket classification
- RAG-based support assistant
- Ollama local LLM inference
- ChromaDB vector search
- FastAPI APIs
- Dockerized deployment

This project demonstrates production-oriented MLOps and LLMOps practices including model serving, retrieval-augmented generation (RAG), observability, containerization, and cloud-native architecture.

---

# Features

## ML Endpoint (`/predict`)
Classifies support tickets into priority levels.

Example:
```json
{
  "text": "VPN is not working"
}
```

Response:
```json
{
  "prediction": "high"
}
```

---

## RAG Endpoint (`/ask`)
Answers support-related questions using retrieved documentation and Ollama LLM inference.

Example:
```json
{
  "question": "How do I reset my password?"
}
```

Response:
```json
{
  "answer": "Users can reset passwords using the forgot password page..."
}
```

---

# Architecture

```text
User
 ↓
FastAPI API
 ├── ML Classifier (/predict)
 └── RAG Pipeline (/ask)
         ↓
     ChromaDB
         ↓
      Ollama
```

---

# Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI |
| ML | scikit-learn |
| LLM | Ollama (llama3) |
| Vector DB | ChromaDB |
| Embeddings | Ollama Embeddings |
| Containerization | Docker |
| Monitoring | Prometheus |
| Language | Python |

---

# Project Structure

```text
llmops-support-assistant/
│
├── app/
│   ├── main.py
│   ├── services/
│   └── logging_config.py
│
├── llm/
│   ├── docs/
│   ├── rag/
│   └── chroma_db/
│
├── models/
├── training/
├── tests/
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# Running Locally

## 1. Clone repository

```bash
git clone https://github.com/YOUR_USERNAME/llmops-support-assistant.git
cd llmops-support-assistant
```

---

## 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Start Ollama

```bash
ollama serve
```

Pull model:

```bash
ollama pull llama3
```

---

## 5. Run ingestion

```bash
python llm/rag/ingest.py
```

---

## 6. Start API

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000/docs
```

---

# Running with Docker

Build image:

```bash
docker build -t llmops-support-assistant .
```

Run container:

```bash
docker run -p 8000:8000 \
-e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
llmops-support-assistant
```

---

# Current Status

- [x] ML inference endpoint
- [x] RAG pipeline
- [x] Ollama integration
- [x] ChromaDB vector store
- [x] Dockerized application
- [x] Prometheus metrics

---

# Upcoming Improvements

- Kubernetes deployment
- Terraform infrastructure
- GitHub Actions CI/CD
- MLflow tracking
- Grafana dashboards
- EKS deployment
- Structured logging
- Model monitoring

---

# License

MIT