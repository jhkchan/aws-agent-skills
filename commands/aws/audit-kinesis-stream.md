---
description: Audit a Kinesis Data Streams configuration for encryption-at-rest gaps, extended-retention cost exposure, shard-count quota risk, enhanced-monitoring blind spots, and consumer health.
nl_triggers:
  - "audit this kinesis stream"
  - "check kinesis encryption"
  - "kinesis retention cost"
  - "kinesis enhanced monitoring"
  - "kinesis shard quota"
  - "kinesis consumer health"
  - "on-demand vs provisioned kinesis"
  - "kinesis stream cost"
  - "is my kinesis stream encrypted"
  - "kinesis stream audit"
  - "EncryptionType NONE kinesis"
  - "kinesis cost optimization"
  - "kinesis config review"
  - "kinesis consumer lag"
routes_to: kinesis-stream-auditor
---

# /aws:audit-kinesis-stream

Activate the `kinesis-stream-auditor` skill and audit one or more Kinesis
Data Streams configurations for security, cost, and operational exposure.

## What it does

Reads a Kinesis stream configuration (describe-stream-summary output) and
applies the ordered classification logic:

1. Encryption gate — EncryptionType: NONE is NO_ENCRYPTION (security-critical).
2. Cost risk — retention > 168h (extended charges), on-demand at low volume,
   shard count approaching 500-quota.
3. Config gap — enhanced monitoring missing IteratorAgeMilliseconds /
   WriteProvisionedThroughputExceeded, no consumers, classic consumer
   shared-throughput bottleneck.
4. Aggregation — worst verdict wins (NO_ENCRYPTION > COST_RISK > CONFIG_GAP > OK).

Emits a deterministic VERDICT per stream:

```text
STREAM: <stream-name>
VERDICT: NO_ENCRYPTION | COST_RISK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [NO_ENCRYPTION] <finding description (Step N)>
  - [COST_RISK] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Kinesis stream configuration and ask any of:

- "audit this kinesis stream"
- "is my kinesis stream encrypted?"
- "check kinesis retention cost"
- "is enhanced monitoring enabled?"
- "should I use on-demand or provisioned?"
- "how many shards is too many?"

A bare stream name or ARN + any audit verb ("audit this stream", "check
stream config") also routes here via the orchestrator.

## Inputs

- A Kinesis stream configuration summary (StreamName, StreamStatus,
  StreamMode, OpenShardCount, RetentionPeriodHours, EncryptionType, KeyId,
  EnhancedMonitoring, ConsumerCount). These attributes drive the
  classification logic.
- For on-demand streams: estimated daily ingest volume (helps evaluate
  on-demand vs provisioned cost fit).
- For live-account audits: `aws kinesis describe-stream-summary --stream-name
  <name>` provides all required fields.

## Outputs

- One VERDICT block per stream (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding category and step citation.
- Specific remediation: enable encryption, reduce retention, switch mode,
  enable monitoring metrics, register consumers.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Kinesis Data Streams).
- `/aws:audit-kms-key-policy` if the stream uses a customer-managed CMK and
  the key policy needs auditing.
