# Baseline (no-skill) response: s3-logs-no-kms-encryption

This file captures what a generic assistant produces WITHOUT the
codebuild-project-auditor skill loaded.

---

The project writes its build logs to S3 and has encryptionDisabled set
to true for both the S3 logs and the build artifacts. CloudWatch Logs
are disabled.

You should consider enabling SSE-KMS on the S3 logs and artifacts
buckets so that you control the encryption keys. The default S3
encryption is AES-256 but a customer-managed KMS key gives you more
control.

Otherwise the project runs as a non-privileged container in a VPC. No
badge is enabled.
