# 0006. Readiness fails only on a pod's own faults

**Status:** Accepted

## Context

The original readiness probe hit `/health`, which always returned 200, so a pod with a broken index still got traffic. The obvious fix, "readiness checks all dependencies", has a trap: Ollama is **shared** by every pod. If readiness failed whenever Ollama was unreachable, an Ollama outage would remove *every* pod from the Service. `/predict`, which doesn't use Ollama, would go down with `/ask`.

## Decision

`/ready` fails only for problems that belong to this pod or this release:

- the pod's own index doesn't match its config, or
- Ollama is reachable but lacks the models this release is configured for (a config error in this release).

**Ollama unreachable does not fail readiness.** `/ready` reports it in its body, `/ask` returns 503, and the error-ratio alert fires. Liveness (`/health`) checks no dependencies at all, so an outage can't cause a restart loop.

## Alternatives

- **Check everything:** cascading total outage, as described above.
- **Check nothing (the original):** broken pods receive traffic.
- **Separate per-feature readiness:** split `/predict` and `/ask` into separate Deployments. Cleaner isolation, more moving parts. Worth it if the endpoints' scaling needs diverge further.

## Consequences

- **Verified in the drill:** a config release pointing at a model the node didn't have (llama3) never became Ready. The rollout stalled while the old pods served all traffic, with **0 user errors**, and Kubernetes marked it failed after 240 s.
- **Verified locally:** with Ollama unreachable, pods stayed Ready and `/predict` kept working.
- **Limit:** readiness can't catch a release that is healthy by every check but behaves badly, like the 5 s deadline image. Only monitoring caught that one (RESULTS §9).
