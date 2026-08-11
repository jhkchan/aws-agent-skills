---
description: Provision an Amazon Kinesis Data Stream with production-grade defaults (provisioned vs on-demand capacity mode, shard sizing, enhanced fan-out consumers, SSE-KMS encryption, resource-level IAM policies, CloudWatch monitoring). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create kinesis stream"
  - "deploy kinesis stream"
  - "kinesis data stream"
  - "kinesis on-demand"
  - "kinesis provisioned"
  - "kinesis shard count"
  - "kinesis enhanced fan-out"
  - "kinesis subscribetoshard"
  - "kinesis sse-kms"
  - "kinesis encryption"
  - "kinesis iam policy"
  - "kinesis cloudwatch iterator age"
  - "kinesis resource policy"
  - "kinesis throughput"
  - "kinesis stream mode"
routes_to: kinesis-stream-deployer
---

# /aws:deploy-kinesis-stream

Activate the `kinesis-stream-deployer` skill and provision an Amazon
Kinesis Data Stream with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Stream mode: provisioned vs on-demand (capacity model decision)
2. Shard count sizing (provisioned mode only — sized to write throughput)
3. Stream creation (CLI, SDK, IaC)
4. Enhanced fan-out consumers (dedicated read throughput via SubscribeToShard)
5. Server-side encryption (KMS CMK or AWS-managed key)
6. Resource-level IAM policies (producer and consumer)
7. CloudWatch monitoring (IteratorAgeMilliseconds, WriteProvisionedThroughputExceeded)
8. Stream ARN resource policies (cross-account access)
9. Recent features (on-demand mode, resource policies, TLS 1.2)

## When to use

- You need to create a new Kinesis Data Stream.
- You are choosing between provisioned (shard-based) and on-demand capacity.
- You need to register enhanced fan-out consumers for dedicated read throughput.
- You need to enable SSE-KMS encryption on a Kinesis stream.
- You need resource-level IAM policies for Kinesis producers/consumers.
- You need CloudWatch alarms for iterator age and write throttling.
- You need cross-account read access via a stream resource policy.

## When NOT to use

- **Kinesis Data Firehose** delivery streams — use Firehose-specific skills.
- **Kinesis Video Streams** — different service, not covered here.
- **Auditing existing stream configurations** — use `kinesis-stream-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-kinesis-stream
```

Then provide: stream name, stream mode (provisioned/on-demand), shard
count (if provisioned), enhanced fan-out consumer names, SSE-KMS key
ID/alias, retention period, producer/consumer IAM roles, CloudWatch
alarm SNS topic ARN, tags.

### Natural language

Any of these routes to the same skill:

- "create a Kinesis data stream with on-demand capacity"
- "set up enhanced fan-out consumers on my Kinesis stream"
- "enable SSE-KMS encryption on a Kinesis stream"
- "size shard count for my Kinesis write throughput"
- "create a Kinesis stream with cross-account read access"

### CLI routing

```bash
node cli/bin/cli.js route "create a kinesis stream"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Kinesis
Data Streams. The output checklist feeds into verification pipelines
and downstream audit skills.

## Example

```
You: /aws:deploy-kinesis-stream

     Create a Kinesis Data Stream named telemetry-ingest in
     us-east-1. On-demand mode. Enhanced fan-out consumer
     realtime-processor. SSE-KMS with CMK alias/kinesis/telemetry-ingest.
     Retention 168 hours. Account: 123456789012.

Skill:
  KINESIS_STREAM: telemetry-ingest
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Stream mode: ON_DEMAND
    [✓] Enhanced fan-out: realtime-processor
    [✓] SSE-KMS: enabled (CMK)
    [✓] CloudWatch alarm: IteratorAge > 300000ms
  VERIFICATION_COMMANDS:
    aws kinesis describe-stream-summary --stream-name telemetry-ingest --region us-east-1
    aws kinesis list-stream-consumers --stream-arn <stream-arn> --region us-east-1
```

## References

- Skill definition: `skills/kinesis-stream-deployer/SKILL.md`
- Stream mode and scaling guide: `skills/kinesis-stream-deployer/references/stream-mode-and-scaling.md`
- IAM and encryption guide: `skills/kinesis-stream-deployer/references/iam-and-encryption.md`
- Eval suite: `skills/kinesis-stream-deployer/evals/evals.json`
