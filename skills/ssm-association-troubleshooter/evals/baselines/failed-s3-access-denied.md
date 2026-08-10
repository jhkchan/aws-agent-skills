# Baseline (no-skill) response: failed-s3-access-denied

This file captures what a generic assistant produces WITHOUT the
ssm-association-troubleshooter skill loaded — the contrast that
proves the skill adds structure (3-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The association is failing because of an AccessDenied error on
S3. The instance role doesn't have permission to write to the S3
output bucket. You should add `s3:PutObject` permission to the
role for the bucket.

You may also want to check the S3 bucket policy to make sure it
allows the instance role to write.
