# Eval prompt: auth-failure-secret-rotation

Diagnose the following CloudWatch Synthetics canary failure. Walk the
diagnostic decision tree and emit the standard VERDICT block (CANARY,
VERDICT, ROOT_CAUSE, FAILURE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A CloudWatch Synthetics canary `api-health-canary` in `us-east-1` is
returning FAILED on every run since 03:01Z today. The on-call engineer
was paged by the CloudWatch alarm.

## Known facts

- Canary type: API HTTP
- `describe-canary` shows:
  - `Type: api`
  - `RuntimeVersion: synthetics-nodejs-5.0`
  - `RunConfig.TimeoutInSeconds: 30`
  - `ExecutionRoleArn: arn:aws:iam::111111111111:role/synthetics-api-canary-role`
  - `Schedule.Expression: rate(1 minute)`
- Run report (from `get-canary-runs`):
  - State: FAILED
  - Step 1 (auth): 401 Unauthorized — response body `{"error": "invalid_client"}`
  - Step 2 (health API): SKIPPED (step 1 failed)
  - Duration: 3 seconds
- CloudWatch `SuccessPercent`: 100% before 03:01Z, 0% after
- Secrets Manager:
  - Secret: `prod/oauth-client-secret`
  - `LastRotatedDate: 2026-08-09T03:00:12Z`
  - Rotation Lambda: `secretsmanager-rotation-fn` (configured for 30-day rotation)
- Canary log query shows:
  - First run after rotation (03:01Z): "Retrieving secret from Secrets Manager..." — then 401
  - Subsequent runs (03:02Z onward): "Using cached token" — then 401
- IAM simulation: canary role HAS `secretsmanager:GetSecretValue` on
  the secret ARN (permission is fine)
- The OAuth server is healthy (verified independently via curl with
  a manually-fetched token)
- The target health API responds 200 OK when authenticated

## Symptom

401 Unauthorized on step 1 (auth) starting at the exact time of a
Secrets Manager rotation. The canary log shows token caching across
runs ("Using cached token").
