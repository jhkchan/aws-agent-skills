# Worked Examples — Secrets Manager Rotation Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — recover-pending (stuck AWSPENDING)

```text
OPERATION: recover-pending
VERDICT: COMPLETED
TARGET: prod/api-gateway-token
PRE_CHECKS:
  - [PASS] Single version in AWSPENDING: a1b2c3d4...
  - [PASS] AWSCURRENT version: e5f6g7h8...
  - [INFO] Connection test with AWSPENDING value: SUCCESS (new credential
    is live on the target)
  - [INFO] Connection test with AWSCURRENT value: FAILED (old credential
    already replaced on the target)
  - [PASS] Operator has access to confirm
STEPS:
  1. CONFIRM: About to promote AWSPENDING version a1b2c3d4... to
     AWSCURRENT and move the old AWSCURRENT e5f6g7h8... to AWSPREVIOUS
     on secret prod/api-gateway-token. This aligns the secret with the
     live target credential. Proceed? (yes/no)
  2. aws secretsmanager update-secret-version-stage \
       --secret-id prod/api-gateway-token \
       --version-stage AWSCURRENT \
       --move-to-version-id a1b2c3d4-... \
       --remove-from-version-id e5f6g7h8-...
POST_VERIFY:
  - [PASS] list-secret-version-ids: a1b2c3d4... is AWSCURRENT,
    e5f6g7h8... is AWSPREVIOUS, no version in AWSPENDING
  - [PASS] Application authentication metrics: no error spike (5-min
    sample post-fix)
NOTES:
  - Root cause: the rotation Lambda's finishSecret step failed with
    AccessDeniedException on UpdateSecretVersionStage. The execution
    role was missing that action. The role has been updated.
  - After this manual recovery, trigger a fresh rotation to confirm the
    schedule works end-to-end:
    aws secretsmanager rotate-secret --secret-id prod/api-gateway-token
  - Clean up old AWSPENDING versions (older failed rotations) if any:
    aws secretsmanager update-secret-version-stage \
      --secret-id prod/api-gateway-token \
      --version-stage AWSPENDING \
      --remove-from-version-id <old-pending-version>
```

### Worked example — diagnose-rotation (BLOCKED with remediation)

```text
OPERATION: diagnose-rotation
VERDICT: BLOCKED
TARGET: prod/payments-db-credentials (rotation Lambda:
        arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation)
PRE_CHECKS:
  - [PASS] Secret exists, RotationEnabled: true
  - [PASS] Lambda State: Active
  - [FAIL] Lambda last invocation errored with:
    "Task timed out after 3.00 seconds" (CloudWatch Logs, last 24h)
  - [PASS] No version stuck in AWSPENDING
STEPS: (none — root cause is Lambda timeout)
POST_VERIFY: (none)
NOTES:
  - Root cause: Lambda timeout is 3 seconds (default). RDS PostgreSQL
    rotation requires connect + authenticate + ALTER USER, which takes
    5-15 seconds on this DB.
  - Fix: increase the timeout, then trigger a manual rotation:
    aws lambda update-function-configuration \
      --function-name SecretsManagerRDSPostgreSQLRotation \
      --timeout 30
    aws secretsmanager rotate-secret --secret-id prod/payments-db-credentials
  - Verify LastRotatedDate advances:
    aws secretsmanager describe-secret --secret-id prod/payments-db-credentials \
      --query 'LastRotatedDate'
```

