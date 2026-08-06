# Baseline (no-skill) response: missing-resource-limits

This file captures what a generic assistant produces WITHOUT the
ecs-task-definition-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, resource-limit reasoning).

---

This task definition is missing CPU and memory limits on both the task
level and the container level. Without resource limits, a single
container could consume all the resources on the host.

There is also no log configuration, so container logs will not be
captured to CloudWatch.

You should add CPU and memory limits and configure logging for
production use.

The container runs as user 1000 which is good (non-root). The network
mode is awsvpc which is the recommended mode.
