# Baseline (no-skill) response: password-in-env-var

This file captures what a generic assistant produces WITHOUT the
ecs-task-definition-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, credential-rotation reasoning).

---

This task definition has `DATABASE_PASSWORD` stored in the `environment`
array as a plaintext value. This means the password is visible in the
task definition JSON and in the AWS console.

You should move the password to AWS Secrets Manager and reference it in
the `secrets` section of the container definition instead of putting it
in `environment`.

The task otherwise looks reasonable — it runs as user 1000, has CPU and
memory limits, and has CloudWatch logging configured.
