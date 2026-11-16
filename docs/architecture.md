# Architecture

How the system is put together, how a request flows through it, and where it runs. Why it is built this way is in the [ADRs](adr/); what it measures is in [RESULTS.md](RESULTS.md).

## Components

| Component | What it is | Where it runs |
|---|---|---|
| **API** (`app/main.py`) | FastAPI: `/predict`, `/ask`, `/ready`, `/health`, `/version`, `/metrics` | k3s pods (HPA 2–5) |
| **Classifier** (`app/services/predict.py`) | scikit-learn Pipeline (TF-IDF + logistic regression), loaded once per pod from `training/models/classifier_<v>.joblib` | in-process |
| **RAG pipeline** (`app/services/rag.py`) | Retrieve top-k chunks from ChromaDB, fill a versioned prompt, generate with Ollama under a whole-answer deadline | in-process |
| **Vector index** (`llm/rag/ingest.py`, `app/services/index.py`) | ChromaDB built from `llm/docs/` (18 docs → 36 chunks), plus a manifest that fingerprints the embedding model, chunking and documents | one per pod, in an `emptyDir`, built by an init container |
| **LLM server** | Ollama 0.40.16 with `tinyllama` (generation) and `nomic-embed-text` (embeddings) | systemd on the EC2 node, **outside** Kubernetes |
| **Monitoring** | Prometheus (scrapes each pod via Kubernetes service discovery; alert rules), Grafana (dashboard as code) | k3s pods |
| **Training and evaluation** | `training/`, `evaluation/`, MLflow (local file store) | dev machine |

## Request flow

**`POST /predict`**: text → Pipeline → priority. Each prediction is counted in `ml_predictions_total{priority, model_version}`. The response includes `versions.classifier`.

**`POST /ask`**:

1. **Retrieval:** embed the question with `nomic-embed-text` via Ollama, then fetch the top-k chunks from the pod's ChromaDB (`k` comes from `configs/retrieval_<v>.json`).
2. **Generation:** fill `prompts/rag_<v>.txt` with the chunks and the question. Stream the answer from Ollama, and stop when the deadline (`timeout_s` from `configs/generation_<v>.json`) passes. Stopping closes the connection, so Ollama stops generating.
3. **Recording:**
   - Each stage's duration goes into `rag_stage_duration_seconds{stage}`.
   - The outcome (answered, declined, or error) goes into `rag_requests_total{outcome}`. Declines are detected by `app/services/refusal.py`.
4. **Errors:** any dependency failure in a stage becomes **503** `{"stage", "error"}`, which is retryable and can be alerted on, and increments `rag_errors_total{stage, error}`.

**Pod startup:**

1. The `ingest` init container builds the index into the shared `emptyDir`. It needs Ollama for the embeddings.
2. The API starts, loads the classifier, and checks the index manifest against the running retrieval config (`rag_index_ok`).
3. `/ready` then gates traffic.

## Versioning

Each component's version is a committed file, selected by an environment variable:

| Component | File | Selector | Default |
|---|---|---|---|
| Classifier | `configs/classifier_<v>.json` → `training/models/classifier_<v>.joblib` (+ MLflow run and registry version in `.meta.json`) | `MODEL_VERSION` | v1 |
| Retrieval (embedding model, chunking, top-k) | `configs/retrieval_<v>.json` | `RETRIEVAL_VERSION` | v1 |
| Generation (model, temperature, deadline) | `configs/generation_<v>.json` | `GENERATION_VERSION` | v1 |
| Prompt | `prompts/rag_<v>.txt` | `PROMPT_VERSION` | v1 |
| Code | git SHA, baked into the image as `GIT_SHA` | image tag | |

`GET /version`, the `versions` field of every response, and the `app_build_info` metric all report what is actually running.

The index manifest catches a stale index: a pod won't serve `/ask` from an index built with a different embedding model, chunking or document set. Top-k is deliberately left out of the index identity, since changing it needs no re-ingest.

## Deployment topology

```
Internet ──(admin IP only: 22, 80)──► EC2 t3.large (Ubuntu 22.04, IMDSv2, instance role)
                                       ├─ Ollama :11434 (systemd)  ◄── pods reach it via the node IP (downward API)
                                       └─ k3s v1.30.4
                                           ├─ Traefik ingress:  /  /health → support-assistant   /grafana → grafana
                                           ├─ support-assistant Deployment (HPA 2–5) + Service
                                           ├─ prometheus (ClusterIP only, not exposed)
                                           └─ grafana (admin password from a hand-made Secret)
```

- **Provisioning:** Terraform creates the VPC, subnet, internet gateway, security group, EC2 instance, ECR repository (immutable tags, keeps 10 images) and IAM roles. The cloud-init bootstrap (`infra/terraform/bootstrap.sh.tftpl`) installs k3s, Ollama and the models. It also installs a systemd timer that refreshes the ECR pull secret every 6 h using the instance role; ECR tokens expire after 12 h.
- **Releases:**
  - CI builds `:<git-sha>` images.
  - `infra/k8s/deploy.sh <sha>` applies all manifests with that tag via kustomize, records a change-cause, and waits for the rollout.
  - Rollouts are zero-downtime: `maxUnavailable: 0`, `maxSurge: 1`, readiness-gated, and failed after 240 s without progress.
  - Rollback: `kubectl rollout undo`.
- **CI/CD:**
  - **CI:** ruff and pytest on every PR. On `main`, build and push to ECR, logging in to AWS through GitHub OIDC (no stored keys).
  - **CD workflow:** exists but is disabled. GitHub-hosted runners can't reach a node whose security group admits only the admin IP ([ADR 0007](adr/0007-ci-oidc-and-admin-deploys.md)).

## Health signals

| Signal | Question it answers | Fails when |
|---|---|---|
| Liveness `/health` | Is the process alive? | the process hangs. Deliberately checks no dependencies |
| Readiness `/ready` | Should this pod get traffic? | its index is broken, or Ollama lacks this release's models. **Not** when Ollama is unreachable: that is shared by every pod ([ADR 0006](adr/0006-readiness-checks-own-faults-only.md)) |
| `rag_index_ok` | Does the pod's index match its config? | the manifest doesn't match |
| Alert `EndpointErrorRatioHigh` | Are users getting 5xx? | > 5% of `/predict` or `/ask` (each separately) fail for 1 min |
| Alert `VectorIndexBroken` / `AppTargetDown` | Broken index / pod not scrapable | for 1 min |

## Security boundaries

- **Network:** the security group admits SSH and HTTP only from `admin_cidr`, and Prometheus is not exposed.
- **AWS credentials:** there are no long-lived AWS keys anywhere.
  - The node pulls images with its instance role. IMDSv2 with hop limit 1 keeps pods from reading the node's credentials.
  - CI uses a role it can only assume from `main` of this repository, scoped to pushing to this one ECR repository.
- **Secrets:** the Grafana admin password and the ECR pull secret exist only in the cluster. `.pem`, `.env`, tfstate and kubeconfigs are gitignored and excluded from the image by `.dockerignore`.
