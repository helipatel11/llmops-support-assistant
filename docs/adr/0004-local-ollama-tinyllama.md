# 0004. Local Ollama serving tinyllama on CPU

**Status:** Accepted, with known limits

## Context

- **Hardware:** `/ask` needs an LLM and an embedding model, and the deployment target is a CPU-only t3.large.
- **Cost and privacy:** support questions shouldn't leave the system, and there's no budget for per-token API costs or a GPU instance.

## Decision

- **Serving:** Ollama, installed by systemd on the node, outside Kubernetes. It serves `tinyllama` for generation and `nomic-embed-text` for embeddings. Pods reach it through the node IP (downward API).
- **Model choice:** a versioned generation config (`configs/generation_v1.json`) pins the model, temperature and answer deadline.

## Alternatives

- **llama3 (8B):** much better answers (64% fully correct vs 28%, grounded 0.96 vs 0.52; RESULTS §5) at about 2× the generation time on the laptop. Its latency and memory on the t3.large weren't measured. Given tinyllama's ~13 s per answer there, it would likely miss any useful latency target.
- **A hosted API (e.g. Claude or OpenAI):** far better quality and latency, but per-token cost, and data leaves the system.
- **A GPU instance:** fixes latency (the same `/ask` is ~10× faster on the M1's GPU) at much higher cost.
- **Ollama in a pod:** possible, but it competes with the app pods on one node and needs a GPU or CPU pinning plan.

## Consequences

- **Free and private, but slow and weak.** `/ask` takes a median 12.7 s on EC2 and handles ~0.07 answers/s; extra users queue. tinyllama is fully correct on only 28% of the golden set.
- **The honest SLO is p95 ≤ 30 s,** too slow for interactive chat. Changing that is a cost decision, not a tuning fix.
- **Ollama outside Kubernetes is a shared single point of failure:** this shaped the readiness design ([0006](0006-readiness-checks-own-faults-only.md)).
- **The LLM call needs a whole-answer deadline:** the HTTP client's timeout limits each read and resets on every streamed token. A 5 s "timeout" let 12 s answers through until the rollback drill exposed it (RESULTS §9).
