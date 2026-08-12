---
description: Diagnose AWS Secrets Manager secret rotation failures through a ten-category diagnostic tree (rotation Lambda timeout, VPC, DB endpoint, IAM, Master Secret, EventBridge schedule, superuser, strategy conflict, cross-account, twin secrets) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or ESCALATE.
nl_triggers:
  - "Secrets Manager rotation failed"
  - "secret rotation error"
  - "secret not rotating"
  - "LastRotatedDate stale"
  - "rotation Lambda timeout"
  - "rotation Lambda VPC"
  - "rotation disabled"
  - "EventBridge rule rotation"
  - "rotation schedule deleted"
  - "rate(1d) rotation"
  - "Master Secret ARN"
  - "rotation template misconfigured"
  - "cross-account secret access denied"
  - "rotation role denied"
  - "Alternating Users strategy"
  - "Single User strategy"
  - "rotation strategy conflict"
  - "twin secrets not synced"
  - "rotation token missing"
  - "ClientRequestToken"
  - "Superuser permissions rotation"
  - "database credential rotation failing"
  - "RotateSecret"
  - "Could not connect to database rotation"
  - "troubleshoot secret rotation"
  - "diagnose secret rotation failure"
routes_to: secrets-manager-rotation-troubleshooter
---

# /aws:troubleshoot-secrets-manager-rotation

Activate the `secrets-manager-rotation-troubleshooter` skill and
diagnose an AWS Secrets Manager secret rotation failure through the
ten-category diagnostic tree.

## What it does

Reads a symptom description (rotation Lambda error log line, stale
`LastRotatedDate`, application authentication failure after rotation,
"AWSPENDING stuck") plus the secret's `describe-secret` output, then
walks the symptom-driven diagnostic tree to a root cause with positive
evidence:

1. **Pre-flight** — secret state (`describe-secret`: RotationEnabled,
   RotationLambdaARN, RotationRules, LastRotatedDate,
   VersionIdsToStages), recent rotation Lambda log events
   (`filter-log-events` on `/aws/lambda/<rotation-lambda>`), AWS
   Health (regional incidents). Short-circuits on `RotationEnabled:
   false`, `DeletedDate` populated, `AWSPENDING` stuck, or AWS-side
   Secrets Manager / Lambda / KMS events.
2. **Symptom entry** — map the error to one of: rotation Lambda
   timeout (3s default), VPC connectivity (Lambda not attached to DB
   subnets), DB endpoint (wrong host/port/dbname), IAM
   (GetSecretValue / kms:Decrypt AccessDenied), Master Secret
   misconfiguration (env var points at deleted/wrong ARN),
   EventBridge schedule missing or disabled, DB superuser
   insufficient, strategy conflict (Single User vs Alternating Users
   template), cross-account resource policy, rotation token missing
   (direct Lambda invoke), twin secrets not synced, Redshift template
   mismatch.
3. **Layer-specific probes** —
   - Timeout: CloudWatch Duration vs configured Timeout; distinguish
     ROTATION_LAMBDA_TIMEOUT (3s default) from ROTATION_LAMBDA_VPC
     (Timeout ≥ 15s but DB unreachable).
   - VPC: `VpcConfig` empty (Lambda not in VPC), subnet route table
     (no route to DB CIDR), SG egress / DB SG ingress on the DB port.
   - DB endpoint: secret value's `host`/`port`/`dbname` keys vs
     `rds describe-db-instances` / `redshift describe-clusters`.
   - IAM: `iam simulate-principal-policy` on the rotation role for
     `secretsmanager:GetSecretValue`, `PutSecretValue`, `DescribeSecret`
     on the secret ARN and Master Secret ARN; `kms:Decrypt` on the
     CMK (if customer-managed).
   - Master Secret: Lambda env var `SECRETS_MANAGER_MASTER_ID` vs
     actual Master Secret ARN; `describe-secret` on the configured
     ARN to verify it exists.
   - Schedule: `events list-rules` / `describe-rule` /
     `list-targets-by-rule`; distinguish SCHEDULE_MISSING (rule
     absent) from SCHEDULE_DISABLED (rule State=DISABLED).
   - Superuser: SQL check on the Master Secret's DB user (MySQL
     `SUPER`, PostgreSQL `rds_superuser`, SQL Server `sysadmin`,
     Oracle `ALTER USER`, Redshift `superuser`).
   - Strategy: Lambda `Description` / `ROTATION_STRATEGY` env var;
     match the template family (Single vs Multi User) to the secret's
     expected strategy.
   - Cross-account: secret resource-based policy lists the rotation
     role ARN in the foreign account; KMS key policy (if
     customer-managed CMK).
   - Token: CloudTrail `RotateSecret` event present (manual `lambda
     invoke` produces no `ClientRequestToken`).
   - Twin: `describe-secret` in primary and secondary regions;
     `ReplicationStatus` for managed replicas.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that
   matches the symptom), INSUFFICIENT_DATA (a probe requires operator
   input), or ESCALATE (AWS-side incident; surface AWS Health event
   ARN).

Emits a deterministic diagnostic block per target:

```text
TARGET: <secret-id or ARN>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROTATION_LAMBDA_TIMEOUT | ROTATION_LAMBDA_VPC |
        ROTATION_LAMBDA_DB_CREDENTIAL | ROTATION_LAMBDA_DB_ENDPOINT |
        SCHEDULE_MISSING | SCHEDULE_DISABLED |
        MASTER_SECRET_MISCONFIGURED | PERMISSION_ROTATION_ROLE |
        PERMISSION_CROSS_ACCOUNT | KMS_DECRYPT_ROLE |
        ROTATION_TOKEN_MISSING | SUPERUSER_INSUFFICIENT |
        STRATEGY_CONFLICT | TWIN_SECRETS_NOT_SYNCED |
        PREVIOUS_CREDENTIAL_NOT_STORED | REDSHIFT_ROTATION_FUNCTION |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or LastRotatedDate delta>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "Secret rotation has not run in 7 days"
- "Rotation Lambda times out at 3 seconds"
- "Rotation Lambda cannot connect to the database"
- "Cross-account rotation Lambda denied reading the secret"
- "LastRotatedDate is stale; EventBridge rule missing"
- "Master Secret ARN does not exist error in rotation"
- "ALTER USER failed; SUPER privilege required"
- "rotation Lambda CREATE USER failed; already exists"
- "AWSPENDING version stuck"
- "twin secret in eu-west-1 not syncing"

A bare secret name + any error verb ("secret rotation broken",
"LastRotatedDate stale", "rotation failing") also routes here via the
orchestrator.

## Inputs

- Symptom description: rotation Lambda error log line, observed
  behaviour (LastRotatedDate delta, application auth failures after
  rotation, AWSPENDING stuck), intermittent vs persistent pattern.
- Secret configuration: SecretId or ARN, RotationEnabled,
  RotationLambdaARN, RotationRules (ScheduleExpression),
  LastRotatedDate, KmsKeyId, VersionIdsToStages, OwningService.
- For live-account diagnosis: rotation Lambda name (from
  RotationLambdaARN), recent CloudWatch log stream, Master Secret
  ARN, DB endpoint / cluster identifier. The skill uses
  `describe-secret`, `get-resource-policy`,
  `get-function-configuration`, `filter-log-events`, `describe-rule`,
  `list-targets-by-rule`, `describe-route-tables`,
  `describe-security-groups`, `describe-key`,
  `simulate-principal-policy`, `lookup-events`,
  `describe-db-instances`, `describe-clusters`.

## Outputs

- One diagnostic block per target secret.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: Lambda timeout/VPC update, EventBridge rule
  recreate/enable, Master Secret ARN fix, role policy edit, DB
  privilege grant, template family re-deploy, cross-account resource
  policy add, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Secrets Manager rotation
  failures).
- `/aws:audit-secrets-manager-rotation` for steady-state rotation
  coverage audits across all secrets in the account (finds secrets
  with rotation disabled, stale LastRotatedDate, missing rotation
  Lambda).
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when the
  rotation Lambda itself has invocation-time failures unrelated to
  rotation (cold-start, runtime deprecation, ECR image pull).
- `/aws:troubleshoot-iam-permission` for deeper diagnosis when the
  rotation role's effective permissions are denied by an SCP,
  permissions boundary, or cross-account resource policy on the
  Secrets Manager API.
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when the
  rotation Lambda cannot reach the database because of routing, NACL,
  VPC peering, or PrivateLink misconfiguration.
