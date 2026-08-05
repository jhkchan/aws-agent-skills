# Baseline (no-skill) response: no-encryption-catalog-disabled

This file captures what a generic assistant produces WITHOUT the
glue-crawler-job-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, catalog-vs-source encryption reasoning).

---

This Glue job has a couple of issues. The data catalog encryption is set to
DISABLED, which means the catalog metadata is stored in plaintext. The
execution role also grants `s3:*` on all resources, which is more permission
than the job likely needs.

The security configuration and S3 source bucket encryption look fine. You
should enable catalog encryption and scope down the S3 permissions.
