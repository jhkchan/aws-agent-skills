---
description: Audit a DynamoDB table for encryption (KMS), PITR, capacity mode, TTL, backup, GSI/LSI quota, and deletion protection.
nl_triggers:
  - "audit this DynamoDB table"
  - "check DynamoDB encryption"
  - "is my DynamoDB table encrypted"
  - "DynamoDB PITR check"
  - "DynamoDB capacity mode"
  - "DynamoDB backup posture"
  - "DynamoDB TTL configuration"
  - "GSI quota DynamoDB"
  - "is deletion protection enabled DynamoDB"
  - "DynamoDB autoscaling missing"
  - "harden DynamoDB table"
  - "DynamoDB compliance audit"
  - "DynamoDB continuous backups"
routes_to: dynamodb-table-auditor
---

# /aws:audit-dynamodb-table

Activate the `dynamodb-table-auditor` skill and audit one or more DynamoDB
table configurations for security, recovery, and compliance posture.

## What it does

Reads a DynamoDB table configuration (describe-table + describe-continuous-
backups + describe-time-to-live + autoscaling policies) and applies the
ordered classification logic:

1. Encryption gate — SSE disabled (AES256, no KMS) is UNENCRYPTED (worst
   verdict). AWS-managed KMS key (alias/aws/dynamodb) is an additive
   CONFIG_GAP. Customer-managed CMK is OK.
2. PITR — ContinuousBackupsStatus DISABLED is NO_PITR. AWS Backup snapshots
   do NOT substitute for PITR (different RPO).
3. Capacity mode — PROVISIONED with no autoscaling (on table or any GSI) is
   CAPACITY_MISMATCH. GSI throttle cascade is the most commonly missed
   misconfiguration.
4. Config gaps — TTL disabled, deletion protection off, no streams, GSI
   quota proximity, AWS-managed KMS key. Accumulate as CONFIG_GAP findings.
5. Aggregation — worst-first: UNENCRYPTED > NO_PITR > CAPACITY_MISMATCH >
   CONFIG_GAP > OK.

Emits a deterministic VERDICT per table:

```text
TABLE: <table-name>
VERDICT: UNENCRYPTED | NO_PITR | CAPACITY_MISMATCH | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [UNENCRYPTED|NO_PITR|CAPACITY_MISMATCH|CONFIG_GAP|OK] <finding (Step N)>
REMEDIATION: <specific CLI action per finding, or "None required" if OK>
```

## When to invoke

Paste a DynamoDB table configuration and ask any of:

- "audit this DynamoDB table"
- "is my table encrypted?"
- "check PITR on my table"
- "is autoscaling configured?"
- "should I use on-demand or provisioned?"
- "is deletion protection on?"

A bare table name + any audit verb ("audit this table", "check table config")
also routes here via the orchestrator.

## Inputs

- DynamoDB table configuration: describe-table output (BillingModeSummary,
  SSEDescription, ProvisionedThroughput, GlobalSecondaryIndexes,
  LocalSecondaryIndexes, DeletionProtectionEnabled, StreamSpecification).
- Continuous backups: describe-continuous-backups output
  (ContinuousBackupsStatus, PointInTimeRecoveryDescription).
- TTL: describe-time-to-live output (TimeToLiveStatus, AttributeName).
- Autoscaling: application-autoscaling describe-scaling-policies output
  (for PROVISIONED tables — on-demand tables do not need this).
- For Global Tables: provide metadata for each replica independently.

## Outputs

- One VERDICT block per table (multiple findings aggregate to the worst
  verdict by priority).
- Enumerated FINDINGS list with per-finding category and step citation.
- Specific remediation: enable SSE-KMS, enable PITR, set up autoscaling,
  enable TTL, enable deletion protection, enable streams.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for DynamoDB table hardening).
- `/aws:audit-kms-key-policy` for auditing the KMS customer-managed key that
  the DynamoDB table references — the key policy is a separate audit surface.
