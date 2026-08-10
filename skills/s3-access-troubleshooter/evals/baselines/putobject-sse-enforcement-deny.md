# Baseline (no-skill) response: putobject-sse-enforcement-deny

This file captures what a generic assistant produces WITHOUT the
s3-access-troubleshooter skill loaded — the contrast that proves the
skill surfaces the bucket-policy SSE-enforcement Deny as the root cause,
while a generic assistant focuses on the identity policy and misses the
Deny statement.

---

You're getting AccessDenied on PutObject. Make sure your IAM identity
policy has `s3:PutObject` on the bucket. Also check the KMS key policy
to make sure you have `kms:GenerateDataKey`.

Try uploading with `--server-side-encryption AES256` or
`--server-side-encryption aws:kms` to see if it's an encryption header
issue.

If it still fails, try widening the IAM policy temporarily to debug.
