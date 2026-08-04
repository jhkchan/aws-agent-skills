# Baseline (no-skill) response: broken-lambda-deleted

> This file captures what a generic assistant produces WITHOUT the
> secretsmanager-rotation-auditor skill loaded. The baseline notices the
> Lambda is deleted but misses the silent-failure severity (CRITICAL),
> the LastRotatedDate staleness root cause, and the pre-flight
> restoration steps.

---

The rotation Lambda for this Redshift secret has been deleted — it returns
a ResourceNotFoundException. This means the rotation configuration points
to a Lambda function that no longer exists. The last successful rotation
was on December 15, 2025, so the credentials have been static since then.

You should recreate the Lambda function and update the rotation
configuration. You can deploy a new Redshift rotation Lambda from the
Serverless Application Repository.
