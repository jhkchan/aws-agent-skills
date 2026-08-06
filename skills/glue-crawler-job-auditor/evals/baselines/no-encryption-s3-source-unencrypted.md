# Baseline (no-skill) response: no-encryption-s3-source-unencrypted

This file captures what a generic assistant produces WITHOUT the
glue-crawler-job-auditor skill loaded.

---

The catalog encryption is enabled (SSE-KMS) and the execution role is
reasonably scoped. However, the S3 source bucket does not have server-side
encryption configured, which means the data the job reads is stored in
plaintext at rest.

You should enable SSE-S3 or SSE-KMS on the source bucket.
