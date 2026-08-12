# Baseline (no-skill) response: cross-account-bucket-policy-missing

---

The cross-account-reader role is getting Access Denied. Since the IAM
policy already allows s3:GetObject on the bucket, check the bucket
policy on the shared-data-bucket to make sure it includes the caller's
account.

Cross-account S3 access can be tricky. You may need to add a bucket
policy statement that allows the other account to read from the
bucket.
