# Baseline (no-skill) response: hardened-fargate-task

This file captures what a generic assistant produces WITHOUT the
ecs-task-definition-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, defense-in-depth reasoning).

---

This task definition looks well-configured for security:

- It runs on Fargate with awsvpc networking
- The container runs as user 1000 (non-root)
- Secrets are stored in Secrets Manager and referenced via the `secrets`
  array (not in environment variables)
- readonlyRootFilesystem is set to true
- All Linux capabilities are dropped
- no-new-privileges is enabled
- CPU and memory limits are set
- CloudWatch logging is configured
- A health check is defined

No major security concerns with this task definition.
