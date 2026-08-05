---
description: Audit an SQS queue for missing or misconfigured dead-letter queue, public access via Principal:* queue policies, encryption-at-rest gaps, maxReceiveCount tuning, and DLQ retention periods. Classifies into NO_DLQ, PUBLIC_ACCESS, NO_ENCRYPTION, CONFIG_GAP, or OK.
nl_triggers:
  - "audit this SQS queue"
  - "check SQS dead-letter queue"
  - "is my SQS queue missing a DLQ"
  - "check SQS redrive policy"
  - "is my SQS queue public"
  - "SQS queue encryption"
  - "maxReceiveCount tuning"
  - "SQS queue policy too permissive"
  - "DLQ retention period"
  - "cross-account DLQ"
  - "poison pill SQS"
  - "Principal star SQS"
  - "SQS SSE-SQS"
  - "SqsManagedSseEnabled"
  - "harden SQS queue"
  - "SQS compliance audit"
  - "FIFO queue DLQ"
  - "SQS queue security"
routes_to: sqs-dlq-policy-auditor
---

# /aws:audit-sqs-dlq-policy

Activate the `sqs-dlq-policy-auditor` skill and audit one or more SQS
queue configurations (attributes + DLQ attributes) for security exposure
and reliability posture.

## What it does

Reads an SQS queue attribute document (Policy, RedrivePolicy,
KmsMasterKeyId, SqsManagedSseEnabled, MessageRetentionPeriod,
VisibilityTimeout), optionally paired with DLQ attributes, and applies
the ordered classification logic:

1. Public access via queue policy — `Principal: "*"` with sensitive SQS
   actions (SendMessage, ReceiveMessage, DeleteMessage, sqs:*) and no
   strong condition (aws:SourceArn, aws:SourceAccount). The S3/SNS
   notification pattern (Principal:"*" + aws:SourceArn) is recognized as
   SAFE — not flagged.
2. Dead-letter queue presence — no RedrivePolicy means poison-pill
   messages retry until expiry (default 4 days), burning compute budget.
3. Encryption-at-rest — neither SqsManagedSseEnabled (free SSE-SQS) nor
   KmsMasterKeyId (SSE-KMS) set means plaintext at rest.
4. Configuration gaps — maxReceiveCount <= 1 (too aggressive) or > 1000
   (poison-pill loop), DLQ retention < 4 days, cross-account DLQ without
   RedriveAllowPolicy.
5. Aggregation — worst finding wins (PUBLIC_ACCESS > NO_DLQ >
   NO_ENCRYPTION > CONFIG_GAP > OK).

Emits a deterministic VERDICT per queue:

```text
QUEUE: <queue-url>
VERDICT: PUBLIC_ACCESS | NO_DLQ | NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
RISK: CRITICAL | HIGH | MEDIUM | LOW
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an SQS queue configuration and ask any of:

- "audit this SQS queue"
- "is my SQS queue missing a DLQ?"
- "check the redrive policy on this queue"
- "is this queue publicly accessible?"
- "is SQS encryption enabled?"
- "is my maxReceiveCount too low?"
- "check DLQ retention period"
- "harden this SQS queue"

A queue URL or ARN plus any audit verb ("audit this queue", "check queue
policy") also routes here via the orchestrator.

## Inputs

- An SQS queue attribute document: Policy (queue policy JSON), RedrivePolicy
  (JSON-encoded string), KmsMasterKeyId, SqsManagedSseEnabled,
  MessageRetentionPeriod, VisibilityTimeout. These attributes drive the
  classification.
- Optional: DLQ attributes (QueueArn, MessageRetentionPeriod) for the DLQ
  retention-period sub-check (Step 4c). If omitted, the skill notes the
  missing data rather than skipping the check silently.
- For live-account audits: a queue URL (requires AWS CLI credentials).

## Outputs

- One VERDICT block per queue (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: remove wildcard principals (or add aws:SourceArn
  conditions), configure DLQ, enable SSE-SQS, tune maxReceiveCount,
  extend DLQ retention.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for SQS messaging security and reliability).
- `/aws:audit-kms-key-policy` for auditing the KMS key policy when SSE-KMS
  is used (KmsMasterKeyId set) — routes to kms-key-policy-auditor.
