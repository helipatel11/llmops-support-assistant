# 0003. k3s on a single EC2 instance, rebuilt per session

**Status:** Accepted

## Context

The goal is to operate a real Kubernetes deployment (probes, rollouts, autoscaling, service discovery, monitoring) on a personal budget. EKS costs about $73/month for the control plane alone, before any nodes.

## Decision

- **Cluster:** k3s v1.30.4 on one t3.large (2 vCPU, 8 GB), provisioned by Terraform. Cloud-init installs k3s, Ollama and the models.
- **Lifecycle:** the stack is created for each working session and destroyed afterwards.
  - About $0.08/hour.
  - A clean first boot takes 2 min 12 s after `terraform apply`.
  - Sessions so far cost about $0.11–0.16.

## Alternatives

- **EKS:** the production-grade choice, but the control-plane cost dominates a hobby budget.
- **docker compose on EC2:** cheaper still, but nothing to learn about Kubernetes operations.
- **A local kind/minikube cluster:** free, but no real cloud IAM, networking or ECR.

## Consequences

- Real Kubernetes behaviour at hobby cost. Rebuilding by one command is itself tested every session.
- **No redundancy:** one node, and Ollama runs outside Kubernetes.
- **The HPA scaled 2 → 5 pods with no capacity gain.** Extra pods on one core share the same CPU, and the real consumer (Ollama) is invisible to pod-CPU autoscaling (RESULTS §7). Horizontal scaling would need more nodes, with Ollama per node or on its own GPU node.
- Terraform state is local. Shared or remote state would be needed for a team.
