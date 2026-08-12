# Baseline (no-skill) response: s3-bucket-access-denied-glue-ok

This file captures what a generic assistant produces WITHOUT the
athena-query-failure-troubleshooter skill loaded.

---

Your Athena query failed with Access Denied on S3. The IAM role
doesn't have permission to read from the prod-data-lake bucket. You
need to add S3 permissions to the role that's running the Athena
query.

Check if the bucket policy allows access from your account, and make
sure the IAM role has s3:GetObject and s3:ListBucket permissions on
the bucket. You might also need to check if Lake Formation is
blocking access, although it looks like it's not enabled in your case.
