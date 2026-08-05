---
description: Audit a Kinesis Data Firehose delivery stream for encryption (NoEncryption/SSE-S3/SSE-KMS CMK), BufferingHints quota violations, Lambda transformation backup posture, CloudWatch error-logging silence (LoggingConfig disabled), source backup absence under dynamic partitioning (silent data-loss vector), and dynamic-partitioning structural integrity (MetadataExtraction wiring, RetryDuration=0 trap).
nl_triggers:
  - "audit this Firehose delivery stream"
  - "is my Firehose stream encrypted"
  - "check Firehose Lambda transformation"
  - "is dynamic partitioning configured correctly"
  - "Firehose source backup missing"
  - "CloudWatch error logging disabled Firehose"
  - "BufferingHints out of range"
  - "firehose data loss vector"
  - "firehose NoEncryption destination"
  - "firehose silent failure"
  - "SSE-KMS CMK Firehose"
  - "DynamicPartitioningConfiguration audit"
  - "firehose encryption posture"
  - "ExtendedS3DestinationConfiguration audit"
routes_to: firehose-delivery-stream-auditor
---

# /aws:audit-firehose-delivery-stream

Activate the `firehose-delivery-stream-auditor` skill and audit one or
more Kinesis Data Firehose delivery streams for encryption-at-rest gaps
and configuration-driven data-loss vectors.

## What it does

Reads a Firehose delivery-stream configuration (the
`describe-delivery-stream` output shape) and applies the ordered
classification logic:

1. Pre-flight stream metadata gate — short-circuit CREATING/DELETING
   streams and identify DirectPut vs KinesisStreamAsSource.
2. Encryption evaluation — explicit `NoEncryption` short-circuits to
   NO_ENCRYPTION; absent `EncryptionConfiguration` block on ExtendedS3
   fires CONFIG_GAP; valid `KMSEncryptionConfig` passes.
3. BufferingHints quota — SizeInMBs (1-128) and IntervalInSeconds
   (60-900); out-of-range fires CONFIG_GAP.
4. Lambda transformation — processor buffer parameters + S3BackupMode
   Enabled; failures here are CONFIG_GAP.
5. CloudWatch error logging — LoggingConfig.Enabled must be true when
   any processing is enabled.
6. Dynamic partitioning integrity — S3BackupConfiguration required,
   RetryDuration > 0, MetadataExtraction processor wired.
7. Aggregation — first-fail-wins. NO_ENCRYPTION dominates CONFIG_GAP.

Emits a deterministic VERDICT per stream:

```text
STREAM: <delivery-stream-name>
VERDICT: NO_ENCRYPTION | CONFIG_GAP | OK
REASON: <1-2 sentences citing the fired step and the worst finding>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

## When to invoke

Paste a Firehose delivery-stream configuration and ask any of:

- "audit this Firehose delivery stream"
- "is my Firehose stream encrypted?"
- "what happens if my Lambda transform fails?"
- "is dynamic partitioning safe without source backup?"
- "are buffering hints within quota?"
- "is CloudWatch logging my Firehose errors?"

A bare delivery-stream ARN or name + any audit verb ("audit this
stream", "check Firehose config") also routes here via the
orchestrator.

## Inputs

- A Firehose delivery-stream configuration (JSON), pasted inline or
  referenced by file path. Accepts the
  `aws firehose describe-delivery-stream --delivery-stream-name <name>`
  output shape directly.
- Stream metadata: DeliveryStreamStatus, DeliveryStreamType,
  DeliveryStreamEncryptionConfigurationConfig (optional).
- Destination configuration: ExtendedS3DestinationConfiguration (most
  common), or legacy S3DestinationConfiguration, or
  HttpEndpoint/Redshift/Splunk/OpenSearch destinations (S3 staging
  layers are still audited).
- For dynamic partitioning: ProcessingConfiguration with
  MetadataExtraction processor parameters and
  DynamicPartitioningConfiguration block.

## Live-account audit snippet

```bash
aws firehose describe-delivery-stream \
  --delivery-stream-name <name> \
  --output json > /tmp/firehose-<name>.json
# Pipe the JSON to the auditor, or paste it into the prompt.
```

For an account-wide sweep:

```bash
# list-delivery-streams paginates at 10 per page (--limit max 10, NOT 50)
aws firehose list-delivery-streams --limit 10 --output json
# Use --exclusive-start-delivery-stream-name <last-name> to page.
```
