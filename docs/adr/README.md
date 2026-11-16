# Architecture Decision Records

Short records of decisions that shape the system: the context, what was decided, the alternatives, and the consequences, including what went wrong. Results cited are in [RESULTS.md](../RESULTS.md).

| # | Decision | Status |
|---|---|---|
| [0001](0001-tfidf-logistic-regression-classifier.md) | TF-IDF + logistic regression for ticket priority | Accepted |
| [0002](0002-chromadb-built-per-pod.md) | ChromaDB, built inside each pod at startup | Accepted |
| [0003](0003-k3s-on-single-ec2.md) | k3s on a single EC2 instance, rebuilt per session | Accepted |
| [0004](0004-local-ollama-tinyllama.md) | Local Ollama serving tinyllama on CPU | Accepted, with known limits |
| [0005](0005-image-tag-chosen-at-deploy-time.md) | Immutable git-SHA images; tag chosen at deploy time | Accepted |
| [0006](0006-readiness-checks-own-faults-only.md) | Readiness fails only on a pod's own faults | Accepted |
| [0007](0007-ci-oidc-and-admin-deploys.md) | CI pushes via GitHub OIDC; deploys from the admin machine | Accepted |
