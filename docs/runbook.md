# Runbook

How to diagnose and fix common failures. Each entry starts from what you **see** (an alert, a status, an error) and runs from cheapest check to most expensive.

**Rule one: mitigate first, diagnose later.** If a release just went out and users are failing, roll back first (see [Bad release](#bad-release-errors-rose-after-a-deploy)), then investigate.

## Quick reference

```bash
ssh -i llmops-key.pem ubuntu@<node-ip>   # the key at the repo root (not infra/terraform/)
kubectl -n llmops get pods -o wide
kubectl -n llmops rollout history deployment/support-assistant
kubectl -n llmops rollout undo deployment/support-assistant      # roll back
curl -s http://<node-ip>/version                                 # what is running
POD_IP=$(kubectl -n llmops get pod <pod> -o jsonpath='{.status.podIP}'); curl -s $POD_IP:8000/ready
# Prometheus is not exposed; from the node:
curl -s http://$(kubectl -n llmops get svc prometheus -o jsonpath='{.spec.clusterIP}'):9090/api/v1/alerts
```

`/ready` returns a JSON reason, e.g. `{"ready": false, "problems": ["ollama is missing models: llama3"], ...}`. Read it before anything else.

---

## Bad release: errors rose after a deploy

**You see:** alert `EndpointErrorRatioHigh`, or errors on the dashboard, shortly after `deploy.sh`. "Pods by image commit" shows the new SHA.

1. **Roll back now:** `kubectl -n llmops rollout undo deployment/support-assistant`.
   - It's instant if the old pods still exist (stalled rollout).
   - It takes about 85 s if the rollout had completed: new pods must ingest and load.
2. **Confirm recovery:** the alert resolves, and `/version` shows the old SHA.
3. **Then diagnose:** compare the configs and code between the two SHAs, and look at `rag_errors_total{stage, error}` for the failing stage. Drill example: `stage="generation", error="LLMDeadlineExceeded"` pointed straight at the lowered deadline.

**Caution:** the `/ask` alert can take minutes to fire at low traffic. At 3 requests per minute, a single success resets the 1-minute window, and right after a rollout there may be no completed requests to judge (RESULTS §9). Don't wait for the alert if the "Errors by endpoint" panel is already climbing.

## Rollout stuck: new pod never becomes Ready

**You see:** `kubectl rollout status` hangs, then `exceeded its progress deadline` after 240 s. The new pod is `0/1 Running`, and the old pods are still serving. Users are fine (`maxUnavailable: 0`).

1. Read the new pod's `/ready` body (quick reference), or run `kubectl describe pod`, which shows `Readiness probe failed: ... 503`.
2. Common reasons:
   - **`ollama is missing models: X`:** the release asks for a model the node doesn't have (drill A: `GENERATION_VERSION=llama3`). Either roll back, or `ollama pull X` on the node if the change is intended. Check memory first: llama3 is 8B.
   - **`index: ...`:** see [Vector index broken](#vector-index-broken).
3. To abandon the release: `kubectl rollout undo` (2 s, removes the stuck pod).

## Ollama down

**You see:**
- `/ask` returns 503 `{"stage": "retrieval" | "generation", "error": "ConnectionError" | ...}`.
- `rag_errors_total` climbs and `EndpointErrorRatioHigh{handler="/ask"}` fires.
- `/predict` keeps working, and pods stay **Ready**. That's by design ([ADR 0006](adr/0006-readiness-checks-own-faults-only.md)), and `/ready` shows `"ollama": {"reachable": false}`.

1. On the node: `systemctl status ollama`, then `journalctl -u ollama -n 50`.
2. `curl -s localhost:11434/api/tags`: is it listening, and are both models listed?
3. Restart with `sudo systemctl restart ollama`. Models persist on disk.
4. Out of memory? Check `free -m` and `dmesg | grep -i oom`. Ollama and k3s share 8 GB.

New pods can't start while Ollama is down: the ingest init container needs embeddings. Existing pods keep serving `/predict`.

## Vector index broken

**You see:** alert `VectorIndexBroken` (`min(rag_index_ok) == 0`); `/ready` 503 with `index: ...`; `/ask` 503 at the `retrieval` stage.

1. Read the reason in `/ready` or `/version` (`index.reason`, `expected` vs `found`). A mismatch means the index was built with a different embedding model, chunking or document set than the running retrieval config.
2. In k3s each pod builds its own index at startup. Check the init container: `kubectl -n llmops logs <pod> -c ingest`. Ollama unreachable during ingest is the usual cause.
3. To fix, delete the pod. Its replacement re-ingests.
4. Locally: `make ingest`.

Changing `top_k` never needs a re-ingest; it isn't part of the index identity.

## Slow `/ask` or `LLMDeadlineExceeded`

**You see:** `/ask` latency climbing, and 503 `{"stage": "generation", "error": "LLMDeadlineExceeded"}`.

- **Expected under load:** on the t3.large, `/ask` handles ~0.07 answers/s, and concurrent requests queue. Two concurrent users already reach a median of 24 s, and four reach 47.5 s (RESULTS §7). More pods or HPA scaling **don't help**: Ollama is the bottleneck, outside Kubernetes.
- **Check concurrency** on the dashboard: `/ask` rate × latency ≈ requests in flight.
- **Check the deadline in the running config** (`GET /version` → generation version, then `configs/generation_<v>.json` → `timeout_s`). The default is 60 s.
- **Real fixes are capacity decisions:** cap `/ask` concurrency, use a smaller or faster model, or move to a GPU.

## Pod OOMKilled

**You see:** restarts in `kubectl get pods`, and `Last State: Terminated, Reason: OOMKilled` in `kubectl describe pod`.

1. The app's limit is 512Mi; measured usage under load was ~160Mi. An OOM means something changed: a bigger model artifact, a bigger index, or a leak.
2. Check `kubectl top pod -n llmops` (metrics-server ships with k3s) against the limit.
3. A node-level OOM can kill Ollama instead (`dmesg | grep -i oom`): see [Ollama down](#ollama-down).

## ImagePullBackOff / ErrImagePull

**You see:** a pod stuck in `ImagePullBackOff`. `kubectl describe pod` shows the reason.

| Reason in events | Cause | Fix |
|---|---|---|
| `no basic auth credentials` / `401` | ECR pull secret expired (tokens last 12 h) | `sudo systemctl start refresh-ecr-secret` on the node (the timer runs every 6 h); check `journalctl -u refresh-ecr-secret` |
| `not found` for `...:<sha>` | That SHA was never pushed (CI push off, or a local commit) | `aws ecr describe-images --repository-name llmops-support-assistant`; push it or deploy an existing tag |
| image is just `support-assistant` | Manifests were applied without `deploy.sh`, which is what sets the tag | `infra/k8s/deploy.sh <sha>` |

## Grafana won't start

**You see:** the grafana pod in `CreateContainerConfigError`; `/grafana` returns 404.

The `grafana-admin` Secret is missing. It's created by hand so the password never reaches git. On the node:

```bash
read -rs -p "Grafana admin password: " GP; echo
kubectl -n llmops create secret generic grafana-admin --from-literal=password="$GP"; unset GP
kubectl -n llmops rollout restart deployment/grafana
```

## Can't SSH to the node

**You see:** `Permission denied (publickey)`.

1. Use `llmops-key.pem` at the **repo root**. `infra/terraform/llmops-key.pem` is an old key that doesn't match the `llmops-key` pair.
2. To check a key without logging in, compare its fingerprint with the one cloud-init printed: `aws ec2 get-console-output --instance-id <id> --latest` shows `Authorized keys ... Fingerprint (sha256)`.
3. `Connection timed out` instead: your public IP changed. Re-run `terraform apply` with the new `admin_cidr`.

## CI push failing

- **`build-and-push` skipped:** the repository variable `ECR_PUSH_ENABLED` isn't `true`. That's intended while the AWS stack is down.
- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`:** the stack is down (the role doesn't exist), or the run isn't on `main`. The role trusts only `refs/heads/main`.

## Noise you can ignore

- `AppTargetDown` goes **pending** briefly during every rollout: Prometheus still scrapes pods that are terminating. It hasn't fired in practice (`for: 1m`).
