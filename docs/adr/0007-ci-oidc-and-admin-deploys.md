# 0007. CI pushes via GitHub OIDC; deploys from the admin machine

**Status:** Accepted

## Context

- **Stored keys:** CI used long-lived AWS access keys stored as GitHub secrets.
- **CD over SSH:** CD SSHed into the node with `StrictHostKeyChecking=no`.
- **Locked-down network:** after the security group was restricted to the admin IP (port 22 had been open to the internet), GitHub-hosted runners, whose IPs change, could no longer reach the node at all.

## Decision

- **CI:** GitHub's OIDC token is exchanged for temporary credentials of the role `llmops-github-ci`.
  - The trust policy allows only `repo:<owner>/llmops-support-assistant:ref:refs/heads/main`, so pull requests and forks get nothing.
  - The policy allows pushing to this one ECR repository.
  - The account's existing GitHub OIDC provider is read by Terraform, never modified.
  - Pushing is switched on with the repository variable `ECR_PUSH_ENABLED`, because the ECR repository only exists while the stack is up.
- **CD:** deploys run from the admin machine with `deploy.sh`. The CD workflow stays in the repo, disabled behind `DEPLOY_ENABLED`.

## Alternatives

- **Open SSH to GitHub's IP ranges:** thousands of shifting ranges, which is effectively opening SSH to the internet.
- **A self-hosted runner on the node:** works, but puts CI execution on the production machine.
- **Pull-based GitOps (Argo CD or Flux):** the cluster pulls the desired state, with no inbound access needed. The right next step (see [0005](0005-image-tag-chosen-at-deploy-time.md)).

## Consequences

- **No AWS keys stored in GitHub.** Verified: CloudTrail recorded `AssumeRoleWithWebIdentity` from `main`, and the image was pushed 87 s later (RESULTS §9). The old static-key secrets can be deleted, and the IAM user's keys deactivated.
- **CI and deployment are decoupled:** a merge produces an image; a human decides when to deploy it and can roll back. That's slower than full continuous deployment, but it keeps the node closed to the internet.
