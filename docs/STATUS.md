# Project Status

## Current status (2026-11-16, all phases complete)

| Area | Done | Open (planned, not done) |
|---|---|---|
| **Evaluation** | Classifier, retrieval (hit@k, MRR), answer quality with a calibrated LLM judge + human spot check; `make eval` | Bigger and real-world datasets; more multi-fact judge calibration cases; prompt v2 |
| **Versioning** | Model, prompt, retrieval and generation configs as files; MLflow registry; index fingerprint; versions in every response and `/version` | |
| **Observability** | RED metrics per endpoint, RAG stage timing, version info-metric, dashboard as code, alert rules (`monitoring/alerts.yml`) | `/ask` alert is slow at low traffic (count-based rule + synthetic probe); no Alertmanager routing |
| **Performance** | k6 load tests on M1 and EC2; bottleneck analysis; SLO proposals | Ollama tuning; `/ask` concurrency cap |
| **Deployment** | Immutable SHA images; tag chosen at deploy time (`deploy.sh`); zero-downtime rollouts; readiness on own faults; whole-answer LLM deadline; rollback drill documented | Automated rollback (canary analysis); GitOps; pod-shutdown behaviour under load (5 client-only `/predict` failures in the drill, unexplained) |
| **Infrastructure** | Terraform: VPC, SG locked to admin IP, IMDSv2, instance role, ECR (immutable, lifecycle), CI OIDC role; cloud-init bootstrap (2 min 12 s) | Remote Terraform state; `terraform destroy` took 510 s once (not investigated) |
| **CI/CD** | ruff + pytest gate; build/push on main via OIDC, switched by `ECR_PUSH_ENABLED` | CD disabled by design (node closed to the internet); delete the old static-key secrets |
| **Docs** | README, [architecture](architecture.md), [ADRs](adr/), [runbook](runbook.md), [case study](case-study.md), [RESULTS](RESULTS.md) | |

---

## Phase 0 audit (historical, 2026-11-12)

Baseline commit: `d23f9d1` (main). The rest of this file records the state of the repo **before** any of the work above. Kept as the "before" picture for the case study; it is not updated.

## How it ran then

```
Offline:  tickets.csv ──► train.py (TF-IDF + LogisticRegression) ──► model.pkl / vectorizer.pkl (committed) + MLflow (local ./mlruns)
          support_docs.txt ──► ingest.py (chunk 500/50, nomic-embed-text) ──► llm/chroma_db (local only, gitignored)

Online:   client ──► Traefik Ingress ──► Service ──► 2× FastAPI pods (k3s on one EC2 t3.large)
                                                     │
                                  /predict ──► in-process sklearn model
                                  /ask     ──► ChromaDB (inside the pod) ──► Ollama (systemd on the EC2 host, :11434)

Build/deploy: push to main ──► GitHub Actions builds image ──► ECR tag `v1` (overwritten every build)
              ──► CD job SSHes to EC2 ──► kubectl rollout restart
```

The EC2 host was set up by hand: Docker, k3s, AWS CLI with static keys, and Ollama with `OLLAMA_HOST=0.0.0.0`. Manifests were edited with `vi` on the server and applied from there. The ECR pull secret was created manually from a 12-hour token.

## Status by area

| Area | Done | Partial | Missing |
|---|---|---|---|
| **API** | `/`, `/health`, `/predict`, `/ask`; Pydantic request models | `config.py` is unused, so the model name and Ollama URL are hardcoded in `rag.py`; every question is logged verbatim; artifacts load at import time from relative paths | Error handling and timeouts for Ollama; response models; version metadata; a readiness check of dependencies |
| **Classifier** | TF-IDF + LR training script; MLflow run and registered model | Only accuracy is logged: **0.333 on a 6-row test split** (chance level for 3 classes). The vectorizer is fitted before the split, which leaks test data. MLflow registers the LR model without its vectorizer | A dataset large enough to evaluate (only 29 rows today); stratified held-out test set; per-class P/R/F1; confusion matrix |
| **RAG** | Ingest script; retriever k=2; grounded prompt with a refusal line | Prompt is an inline f-string; `ingest.py` ignores `OLLAMA_BASE_URL` and needs `unstructured`, which isn't installed | **No vector store in the deployed image**: `chroma_db/` is gitignored and CI builds from git, so `/ask` in k3s gets 0 documents. Also missing: golden question set, hit@k/MRR, groundedness check, versioned prompts and retrieval config |
| **Docker** | `python:3.11-slim` image | Runs as root; image ships unused packages (sentence-transformers with torch, pytest, httpx, boto3); `app/Dockerfile` is a broken duplicate | **No `.dockerignore` at the repo root**: a local build copies `.env`, `*.pem`, tfstate, `mlruns/`, and `venv/` into the image. Also missing: pinned dependencies |
| **Kubernetes** | Namespace, Deployment (2 replicas, RollingUpdate), readiness/liveness probes, requests/limits, Service, Ingress, HPA, ConfigMap, Secret | `/health` always returns 200, even if a dependency is broken; Prometheus scrapes the Service (one random pod per scrape); Prometheus/Grafana images use `latest`; Grafana keeps default credentials and is exposed via Ingress; Ollama URL is a hardcoded node IP in a Secret | Immutable image tags; storage for Prometheus/Grafana; a fix for the ECR token expiring after 12h (`ImagePullBackOff`) |
| **CI/CD** | CI builds and pushes to ECR; CD runs after CI succeeds | CD restarts a mutable tag, so you can't tell what's running or roll back; static AWS keys; `StrictHostKeyChecking=no` | Tests and lint in CI, gating the push; SHA tags |
| **Tests** | One `/health` test | File is named `tests_health.py`, so pytest collects **0 tests** | Tests for `/predict` and `/ask`; any tests in CI |
| **Monitoring** | HTTP metrics via instrumentator; `ml_predictions_total{priority}`; `rag_requests_total` | Duplicate `monitoring/` folder | Separate retrieval vs. LLM latency; error counters; version labels; Grafana dashboard JSON |
| **Infrastructure (Terraform)** | VPC, subnet, IGW, route table, SG, EC2 | SG has SSH open to `0.0.0.0/0` (which overrides the `/32` rule) and ports 8000/3000/9090 open to the internet; local state | Bootstrap script / `user_data`; IAM instance profile (instead of `aws configure` on the host) |
| **Docs** | README with architecture and screenshots | README links a missing `mlflow.png`; says Python 3.11+, but the local venv is 3.9 | `RESULTS.md`, `architecture.md`, ADRs, runbook, case study |

## Top risks

1. **Secrets in images.** Without a root `.dockerignore`, any local `docker build` bakes `.env`, SSH keys, and tfstate into the image.
2. **Open security group.** SSH, Grafana (default login), Prometheus, and port 8000 are reachable from anywhere.
3. **`/ask` doesn't work in k3s.** The image has no vector store, and the empty store fails silently.
4. **No rollback possible.** The mutable `v1` tag plus `rollout restart` means you can't redeploy a previous image.
5. **ECR pull secret expires after 12 hours**, so later deploys fail with `ImagePullBackOff`.
6. **Classifier numbers can't be defended.** 29 rows, data leakage, accuracy at chance level.
7. **Tests don't run.** 0 collected, and none in CI.
8. **Manual server setup.** About 40 hand-typed commands per rebuild; manifests on the server can drift from the repo; the admin kubeconfig is readable by every user.

## Phase 0.5 changes (completed 2026-11-12, branch `chore/phase0-audit`)

| Risk / gap above | What changed | How it was verified |
|---|---|---|
| Secrets in images | Allowlist `.dockerignore` at the repo root | Probe build listed the context: no `.env`, `*.pem`, tfstate, `mlruns/`, `venv/` |
| Tests don't run | Test file renamed; 6 tests for `/health`, `/predict`, `/ask` (Ollama/Chroma faked), validation, `/metrics` | pytest: 0 collected → 6 passed (Python 3.9 venv and clean 3.11 container) |
| Unused packages in the image | Runtime deps pinned in `requirements.txt`; tooling in `requirements-dev.txt` | Image 3.69 GB → 254 MB (`docker image inspect`, linux/arm64, local build) |
| Hardcoded config | All settings in `app/config.py`; `OLLAMA_MODEL` now honoured; RAG clients created on first use | Tests + container smoke test (`/health`, `/predict`, `/metrics`) |
| Ingest broken / duplicates | `TextLoader`, honours `OLLAMA_BASE_URL`, rebuilds the store each run | Two runs → still 2 chunks |
| No tests in CI; mutable tag | CI: ruff + pytest gate the push; images tagged with the commit SHA; CD uses `kubectl set image` to that SHA, only for pushes to main | actionlint 1.7.7 clean. **Not yet run on GitHub.** |

New finding: the local vector store was also empty (0 chunks) before re-ingest. The knowledge base is only 2 chunks with k=2, so retrieval can't be evaluated until it grows (Phase 1).

## Planned (not done)

Phase 5 items found in the audit: `deployment.yaml` still references `:v1`; Ollama URL via `status.hostIP`; ECR credential refresh; IAM instance profile; GitHub OIDC; security group tightening; bootstrap script; ECR lifecycle policy. See `CLAUDE.md` for the full phase list.
