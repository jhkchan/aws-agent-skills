# Baseline (no-skill) response: unrotated-rds-secret

> This file captures what a generic assistant produces WITHOUT the
> secretsmanager-rotation-auditor skill loaded — the contrast that proves
> the skill adds structure (deterministic VERDICT, RISK level, four-step
> Lambda contract knowledge, specific remediation).

---

This RDS secret has `RotationEnabled: false`, which means the PostgreSQL
credentials are static and haven't been rotated in 180 days. That's a
security risk — if the credentials are leaked, they remain valid
indefinitely.

You should enable rotation for this secret. Secrets Manager can automatically
rotate RDS credentials using a Lambda function. Set the rotation interval to
30 days for database credentials.

To enable rotation, you can use the AWS Console or CLI to configure a
rotation Lambda and set the schedule.
