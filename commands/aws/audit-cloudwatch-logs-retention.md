---
description: Audit a CloudWatch Logs log group for Never-expire retention, missing SSE-KMS CMK encryption, retention x volume cost risk, missing metric filters, missing anomaly detector coverage, and subscription-filter fan-out cost. Emits a first-fail-wins verdict per log group.
nl_triggers:
  - "audit this CloudWatch Logs group"
  - "check log group retention"
  - "Never expire log group"
  - "is my log group retention set"
  - "CloudWatch Logs cost"
  - "is CloudWatch Logs encrypted with KMS"
  - "CloudWatch Logs CMK"
  - "are metric filters configured"
  - "is anomaly detection enabled"
  - "subscription filter audit"
  - "CloudWatch Logs compliance check"
  - "log group cost risk"
  - "audit log group posture"
  - "log retention compliance"
  - "CloudWatch Logs config gap"
  - "audit observability coverage"
routes_to: cloudwatch-logs-retention-auditor
---

# /aws:audit-cloudwatch-logs-retention

Activate the `cloudwatch-logs-retention-auditor` skill and audit one or
more CloudWatch Logs log groups for cost, security, and observability
posture.

## What it does

Reads a CloudWatch Logs log group configuration (`describe-log-groups`
output) paired with metric filters (`describe-metric-filters`),
subscription filters (`describe-subscription-filters`), and anomaly
detectors (`describe-anomaly-detectors`). Applies the ordered
first-fail-wins classification:

1. Never-expire retention check — `retentionInDays` absent or NO_RETENTION.
2. SSE-KMS CMK check — `kmsKeyId` present or NO_ENCRYPTION.
3. Cost-risk retention x volume — `retentionInDays` x `storedBytes`
   exceeds threshold or COST_RISK.
4. Observability config gap — no metric filters AND/OR no anomaly
   detector (or detector in TRAINING) or CONFIG_GAP.
5. All dimensions pass → OK.

Emits a deterministic VERDICT per log group:

```text
LOG_GROUP: <name-or-arn>
VERDICT: NO_RETENTION | NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the first failing dimension and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

## When to invoke

Paste a CloudWatch Logs log group configuration and ask any of:

- "audit this CloudWatch Logs group"
- "is my log group retention set"
- "is this log group Never expire"
- "check CloudWatch Logs cost"
- "is CloudWatch Logs encrypted with KMS"
- "are metric filters configured"
- "is anomaly detection enabled"
- "subscription filter audit"
- "CloudWatch Logs compliance check"
- "log group cost risk"

A bare log-group name or ARN plus any audit verb also routes here.

## Inputs

- Log group configuration from
  `aws logs describe-log-groups --log-group-name-prefix <name> --output json`
  (JSON or key-value summary).
- Metric filters from
  `aws logs describe-metric-filters --log-group-name <name>`.
- Subscription filters from
  `aws logs describe-subscription-filters --log-group-name <name>`.
- Anomaly detectors from
  `aws logs describe-anomaly-detectors --log-group-arn-list <arn>`.
- KMS key metadata from `aws kms describe-key --key-id <id>` (optional,
  for verifying CMK state and region).

## Outputs

- One VERDICT block per log group (first-fail-wins ordering).
- Additive FINDINGS list (lower-priority dimensions still enumerated
  even when first-fail-wins terminates at a higher-priority finding).
- Specific CLI remediation per finding, with safety caveats
  (KMS-request cost projection, retention legacy-events caveat,
  anomaly detector 14-day baseline delay).
