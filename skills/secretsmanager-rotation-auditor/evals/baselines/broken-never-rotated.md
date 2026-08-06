# Baseline (no-skill) response: broken-never-rotated

> This file captures what a generic assistant produces WITHOUT the
> secretsmanager-rotation-auditor skill loaded. The baseline may
> incorrectly classify this as OK or STALE because "rotation is enabled
> and the Lambda exists" — missing that null LastRotatedDate after 3
> intervals is definitive proof of silent failure, and that the target
> RDS instance is deleted.

---

This Oracle secret has rotation enabled with a 30-day interval, but
LastRotatedDate is null — it has never been rotated. The Lambda function
is active and has the right permissions. The last invocation errored with
a ResourceNotFoundException saying the DBInstance was not found.

It looks like the RDS instance was deleted but the secret and rotation
configuration remain. You should either delete the secret if it's no
longer needed, or update it to point to the replacement database.

The rotation is effectively broken since there's no target to rotate
against.
