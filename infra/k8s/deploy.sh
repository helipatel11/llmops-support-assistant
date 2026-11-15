#!/usr/bin/env bash
# Deploy one immutable image tag (a git SHA) and wait for the rollout.
#
#   infra/k8s/deploy.sh <git-sha> ["reason shown in rollout history"]
#
# The tag is chosen at deploy time instead of being committed in deployment.yaml, so
# re-applying the manifests can never silently roll pods back to an old image.
# Roll back with: kubectl -n llmops rollout undo deployment/support-assistant
set -euo pipefail

tag=${1:?usage: deploy.sh <git-sha> [reason]}
reason=${2:-"deploy $tag"}
reason=${reason//\"/}  # embedded in YAML below
registry=${REGISTRY:-183631323298.dkr.ecr.us-east-1.amazonaws.com}
here=$(cd "$(dirname "$0")" && pwd)

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$here"/*.yaml "$work"/

cat >> "$work/kustomization.yaml" <<YAML

images:
  - name: support-assistant
    newName: $registry/llmops-support-assistant
    newTag: "$tag"

patches:
  - target: {kind: Deployment, name: support-assistant}
    patch: |-
      - op: add
        path: /metadata/annotations
        value: {kubernetes.io/change-cause: "$reason"}
YAML

kubectl apply -k "$work"
kubectl -n llmops rollout status deployment/support-assistant --timeout=300s
kubectl -n llmops rollout history deployment/support-assistant | tail -3
