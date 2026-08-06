# Baseline (no-skill) response: overpermissive-role-admin-wildcard

This file captures what a generic assistant produces WITHOUT the
glue-crawler-job-auditor skill loaded.

---

The job's encryption settings look good — the catalog uses SSE-KMS, the S3
source is encrypted, and a security configuration is attached. However, the
execution role grants `Action: "*"` on `Resource: "*"`, which is
administrator-level access. It also has `iam:PassRole` on every role.

You should tighten this role to use only the specific Glue and S3 actions
the job actually needs.
