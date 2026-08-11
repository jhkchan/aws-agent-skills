---
description: Provision a Kinesis Data Firehose delivery stream with production-grade defaults (source selection, Lambda transformation, Parquet/ORC format conversion, S3/OpenSearch/HTTP/Redshift destinations, buffering hints, backup, KMS encryption). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create firehose delivery stream"
  - "deploy firehose"
  - "firehose s3 destination"
  - "firehose lambda transformation"
  - "firehose parquet conversion"
  - "firehose opensearch destination"
  - "firehose redshift destination"
  - "firehose splunk http endpoint"
  - "firehose buffering hints"
  - "kinesis firehose"
  - "delivery stream"
routes_to: firehose-delivery-stream-deployer
---

# /aws:deploy-firehose-delivery-stream

Activate the `firehose-delivery-stream-deployer` skill and provision a
Kinesis Data Firehose delivery stream with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Source selection (Direct PUT / Kinesis Stream / MSK / CW Logs)
2. Lambda transformation (ETL, blueprints)
3. Format conversion (Parquet/ORC via Glue schema)
4. S3 destination (prefix, error prefix, buffering, compression)
5. OpenSearch destination (index, rotation, retry)
6. HTTP endpoint destination (Splunk/custom)
7. Redshift destination (COPY via S3 staging)
8. Backup configuration (source/failed record backup)
9. Buffering hints (latency vs cost trade-off)
10. Retry and duration settings
11. CloudWatch logging
12. Server-side encryption (KMS)
13. Recent features (Parquet conversion, MSK source, partition projection)

## When to use

- You need to create a Firehose delivery stream.
- You are configuring an S3, OpenSearch, HTTP, or Redshift destination.
- You need Lambda transformation for ETL processing.
- You want Parquet or ORC format conversion for Athena.
- You need to tune buffering hints for latency vs cost.
- You are setting up KMS encryption for the delivery stream.

## When NOT to use

- **Kinesis Data Streams** — use kinesis-stream-deployer.
- **Kinesis Data Analytics** — use kinesis-analytics-deployer.
- **Firehose auditing** — use firehose-delivery-stream-auditor.
- **Firehose troubleshooting** — use kinesis-firehose-troubleshooter.

## How to invoke

### Slash command

```
/aws:deploy-firehose-delivery-stream
```

Then provide: stream name, source type, destination type and
configuration (bucket/domain/endpoint), Lambda function ARN (if
transformation), Glue database/table (if format conversion), buffering
hints, KMS key ARN (if encryption), backup bucket, tags.

### Natural language

Any of these routes to the same skill:

- "create a Firehose delivery stream to S3"
- "set up Firehose with Parquet conversion for Athena"
- "configure Firehose to deliver to OpenSearch"
- "create a Firehose stream with Lambda transformation"
- "set up Firehose for Splunk ingestion"

### CLI routing

```bash
node cli/bin/cli.js route "create a firehose delivery stream"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Firehose
delivery streams. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-firehose-delivery-stream

     Create a Firehose stream named events-to-s3-parquet.
     Direct PUT source. Convert to Parquet using Glue
     analytics/events_table. S3 bucket my-data-lake with
     Hive-style prefix. Buffering 128MB for Parquet.

Skill:
  FIREHOSE: events-to-s3-parquet (Direct PUT → S3)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Source: Direct PUT
    [✓] Format conversion: Parquet (Glue analytics/events_table)
    [✓] Destination: S3 (my-data-lake, Hive-style prefix)
    [✓] Buffering hints: 128MB / 300s (tuned for Parquet)
    [✓] Compression: UNCOMPRESSED
    [✓] KMS encryption: enabled
  VERIFICATION_COMMANDS:
    aws firehose describe-delivery-stream --delivery-stream-name events-to-s3-parquet --region us-east-1
```

## References

- Skill definition: `skills/firehose-delivery-stream-deployer/SKILL.md`
- Destinations and buffering guide: `skills/firehose-delivery-stream-deployer/references/destinations-and-buffering.md`
- Transformation and encryption guide: `skills/firehose-delivery-stream-deployer/references/transformation-and-encryption.md`
- Eval suite: `skills/firehose-delivery-stream-deployer/evals/evals.json`
