# Baseline (no-skill) response: insufficient-context-need-more-info

This file captures what a generic assistant produces WITHOUT the
s3-access-troubleshooter skill loaded — the contrast that proves the
skill refuses to guess and emits NEED_MORE_INFO with the specific
missing inputs, while a generic assistant guesses at common causes
without enough information.

---

You're getting AccessDenied uploading to S3. The most common causes are:

1. Your IAM role doesn't have `s3:PutObject` permission.
2. The bucket policy has a Deny statement.
3. KMS key policy is missing your role.
4. The bucket is full.
5. Object Lock retention is preventing the upload.

Try widening your IAM permissions to `s3:*` temporarily to confirm
whether it's an IAM issue. If that works, narrow down to the specific
permission.

Also check the bucket policy and KMS key policy in the bucket's
account.
