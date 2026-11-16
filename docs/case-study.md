# Case study: making a working ML/LLM app operable

*Draft for the portfolio. Every number is from [RESULTS.md](RESULTS.md), with method and date.*

## The problem

I had a working app: a FastAPI service that classifies support tickets and answers IT questions with retrieval-augmented generation on a local LLM. It was deployed on Kubernetes on AWS. It "worked", but I couldn't answer the questions someone who owns a production system gets asked:

- **How good is it?**
- **What exactly is running right now?**
- **Is it healthy, and where does the time go?**
- **How much load can it take?**
- **What happens when a bad release ships?**

The goal was to be able to answer each of those with evidence, on a hobby budget.

## Where it started

An audit ([STATUS.md](STATUS.md)) found the app looked finished but was hollow underneath:

- **The deployed RAG retrieved zero documents.** The vector store was gitignored, and CI built the image from git.
- **The classifier's only metric was 0.33 accuracy on a 6-row test split,** with the vectorizer fitted before the split.
- **The test suite collected 0 tests,** because of a filename typo.
- **Every image was pushed as `:v1`,** so nobody could tell what was running or roll back.
- **SSH was open to the internet,** static AWS keys were on the server, and there was no `.dockerignore`, so a local build would bake `.env` and SSH keys into the image.

## What I built, and what each part proved

| Phase | What changed | Evidence it produced |
|---|---|---|
| Evaluation | Held-out synthetic test set; golden questions with expected docs; an LLM judge whose quotes are verified in code, calibrated on known cases and checked against my own scoring | Classifier macro F1 0.50; retrieval hit@2 0.96; tinyllama fully correct on 28% |
| Versioning | Every component (model, prompt, retrieval, generation) is a committed file selected by an env var; an index fingerprint refuses stale vector stores; MLflow registry | "Change one thing, re-run, compare": retrieval v2 *improved* its own metric but made answers *worse*, so I rejected it |
| Observability | RED metrics per endpoint, retrieval vs generation timing, a version info-metric, dashboard as code | Generation is ~96% of `/ask` time; an Ollama outage was visible in ~30 s while `/health` stayed green |
| Load testing | k6 open-model (arrival rate) and closed-model (concurrency) tests on the real deployment | `/predict` p95 8 ms at 100 req/s; `/ask` capped at ~0.07 answers/s by the LLM on one CPU core |
| Safe deployment | Immutable SHA images with the tag chosen at deploy time; readiness that fails only on a pod's own faults; alert rules; CI on GitHub OIDC; a rollback drill | A bad config was blocked with 0 user errors; a bad image was detected in 3 min 39 s and rolled back in 83 s |

## What broke (the most useful part)

- **The rollback drill found a bug in my own fix.** I added an LLM timeout, then simulated a bad release by lowering it to 5 s. Answers take ~13 s on this hardware, so almost every request should have failed. Instead most succeeded, and the alert never fired.
  - The HTTP client's timeout limits each *read*. The LLM response streams token by token, so the clock reset on every token.
  - My "60 s timeout" had never limited anything.
  - I fixed it with a deadline across the whole streamed answer, re-ran the drill, and it was caught.
  - Lesson: **a drill tests your assumptions, not just your rollback button.**
- **The autoscaler worked perfectly and achieved nothing.** Under load it scaled 2 → 5 pods with no throughput gain. The CPU was consumed by the LLM server running on the node *outside* Kubernetes, on a machine with one physical core. Pod-CPU autoscaling watched the wrong signal, and more pods on one node can't add capacity.
- **A metric improved while the product got worse.** Retrieving 3 chunks instead of 2 fixed the only retrieval miss, but the small model then wrote longer, invented step lists and answered questions it should have refused. Component metrics need an end-to-end check.
- **The judge needed three designs.** A single "score this answer" prompt scored correct answers 0. A "list unsupported claims" prompt echoed the answer back. What worked was asking for evidence *quotes* and verifying them in code. A human spot check then showed it still under-scores correct answers, and I documented that rather than hiding it.
- **My first evaluation scored a perfect 1.0.** The synthetic test set shared phrases with training, so the label leaked. I caught it before recording any number, because a perfect score on a hard problem is a bug until proven otherwise.
- **An early run was silently served by the wrong model.** A leftover `.env` swapped the model, and the first results document was wrong. I recorded the correction publicly. Now the model is set only in versioned files, and stray env vars are ignored with a warning.

## Decisions I'd defend in an interview

- **Readiness must not check shared dependencies.** If the shared LLM server is down, failing readiness would remove *every* pod and take down the endpoint that doesn't need the LLM. [ADR 0006](adr/0006-readiness-checks-own-faults-only.md)
- **Choose the image tag at deploy time, never in the manifest.** A committed `:v1` silently rolls everything back on the next `kubectl apply`. [ADR 0005](adr/0005-image-tag-chosen-at-deploy-time.md)
- **Stay on a small CPU model on purpose, and say what it costs.** The honest `/ask` SLO on this hardware is p95 ≤ 30 s, which is too slow for chat. Fixing that is a cost decision (GPU or hosted model), not a tuning fix. [ADR 0004](adr/0004-local-ollama-tinyllama.md)
- **No AWS keys anywhere.** The node uses an instance role, and CI uses OIDC restricted to `main`. Deploys come from the admin machine, because the node accepts no inbound traffic from the internet. [ADR 0007](adr/0007-ci-oidc-and-admin-deploys.md)

## Cost

One t3.large, created per working session and destroyed afterwards. A clean rebuild takes 39 s of Terraform plus 2 min 12 s of bootstrap. Each AWS session cost about $0.11–0.16 of instance time.

## What I'd do next

1. **Alerting that works at low traffic:** a count-based `/ask` alert plus a synthetic probe, then **automated rollback** with canary analysis (e.g. Argo Rollouts) instead of a human running `rollout undo`.
2. **GitOps (Argo CD or Flux),** so git is the record of what's deployed and the cluster pulls, with no inbound access.
3. **A concurrency cap on `/ask`** (fail fast with 503 + Retry-After instead of queueing for 50 s), and Ollama tuning, which is the next capacity experiment.
4. **Better models where they matter:** prompt v2 for refusals, an embedding-based classifier for outage recall, and a measured llama3 or GPU option with its cost attached.
