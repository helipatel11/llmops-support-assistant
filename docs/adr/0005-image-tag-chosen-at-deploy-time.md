# 0005. Immutable git-SHA images; tag chosen at deploy time

**Status:** Accepted

## Context

Originally CI pushed every build as `:v1` and CD ran `rollout restart`. Nobody could tell which code was running, and there was nothing to roll back *to*. After switching to SHA tags, a second trap remained: `deployment.yaml` still said `:v1`, so any `kubectl apply` of the manifests would silently roll every pod back to that old image.

## Decision

- **Tags:** images are tagged with the full git SHA, and ECR is set to `IMMUTABLE`, so a tag can never be overwritten.
- **Placeholder in the manifest:** `deployment.yaml` names a placeholder image, `support-assistant`.
- **Deploy script:** `infra/k8s/deploy.sh <sha> "<reason>"` sets the real tag with kustomize at deploy time, records it as the rollout's `change-cause`, and waits for the rollout.
- **Fail loudly:** applying the manifests without the script fails visibly (the image can't be pulled) instead of running an old version.
- **HPA ownership:** `replicas` was removed from the Deployment, so `apply` no longer resets what the HPA chose.

## Alternatives

- **GitOps (commit the tag, Argo CD or Flux syncs it):** the stronger model, with git as the record of what's deployed. It needs a controller in the cluster and a commit per release. It's the natural next step.
- **Helm with `--set image.tag`:** the same idea plus a templating layer this project doesn't otherwise need.
- **`kubectl set image` only:** works, but the manifests in git still carry a stale tag.

## Consequences

- **Every running pod maps to a commit:** `GET /version` and the "Pods by image commit" panel show it.
- **`kubectl rollout history` is a readable release log:** e.g. `DRILL B2: 07837e1 (LLM deadline 5 s)`.
- **Rollback is one command:** 2 s when the old pods still exist, 83–88 s after a completed rollout.
- **What's deployed is cluster state, not git state:** a GitOps controller would close that gap.
