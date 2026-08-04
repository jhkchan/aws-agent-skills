# Baseline (no-skill) response: host-network-root-user

This file captures what a generic assistant produces WITHOUT the
ecs-task-definition-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, network-isolation reasoning).

---

This task definition has two security concerns:

1. `networkMode: host` — the container shares the host's network
   namespace. This means there is no network isolation between the
   container and the EC2 host.

2. `user: root` — the container runs as the root user (UID 0).

You should consider changing the network mode to `awsvpc` for better
isolation, and setting a non-root user for the container.

The task has CPU and memory limits set and has logging configured.
