# Eval prompt: insufficient-permissions-iam-role

Diagnose the following CloudWatch Synthetics canary failure. Walk the
diagnostic decision tree and emit the standard VERDICT block (CANARY,
VERDICT, ROOT_CAUSE, FAILURE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CloudWatch Synthetics canary `homepage-check` in `us-east-1` started
failing at `2026-08-09T10:00Z`. The on-call engineer was paged.

## Known facts

- Canary type: HTTP ping
- `describe-canary` shows:
  - `Type: heartbeat`
  - `RuntimeVersion: synthetics-nodejs-5.0`
  - `ExecutionRoleArn: arn:aws:iam::111111111111:role/synthetics-canary-role`
  - `ArtifactS3Location: cw-synthetics-artifacts-prod`
- Run report (from `get-canary-runs`):
  - State: FAILED
  - Error: `AccessDenied` when reading canary artifact from S3
  - The canary did not execute any HTTP steps — it failed at startup
- IAM simulation results:
  - `s3:GetObject` on `arn:aws:s3:::cw-synthetics-artifacts-prod/*`:
    DENIED
  - `s3:ListBucket` on `arn:aws:s3:::cw-synthetics-artifacts-prod`:
    DENIED
  - `logs:CreateLogStream` on the log group: ALLOWED
- S3 bucket policy timeline:
  - `cw-synthetics-artifacts-prod` bucket policy was updated at
    `2026-08-09T09:55Z` to restrict access to a different principal
  - The policy previously allowed `arn:aws:iam::111111111111:role/synthetics-canary-role`
  - The new policy removed this role from the allowed principals
- The target endpoint `https://example.com` responds normally:
  - `curl -sI https://example.com` returns `200 OK` in 0.3s
- CloudWatch `SuccessPercent`: 100% before 10:00Z, 0% after

## Symptom

Canary startup failure with `AccessDenied` on S3. The canary cannot
read its own artifacts. The IAM role's S3 access was revoked by a
bucket policy change. The target endpoint is healthy.
