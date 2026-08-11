# Example usage: kafka-connect-troubleshooter

A walkthrough showing the skill diagnosing an MSK Connect sink
connector where the producer writes Protobuf but the connector is
configured with AvroConverter, causing the DLQ to fill. The skill
emits ROOT_CAUSE_FOUND with CATEGORY=SINK_DLQ.

## Input (user prompt)

> Our MSK Connect S3 sink connector is RUNNING but its task keeps
> FAILING. Records are going to the DLQ at ~200/min. The DLQ header
> shows "Error deserializing Avro message" but our producer is
> definitely writing Protobuf. What's going on?

## Skill output

```text
TARGET: s3-sink-connector
VERDICT: ROOT_CAUSE_FOUND
REASON: Sink connector sends records to DLQ at 100% error rate. DLQ
  headers show AvroConverter cannot decode — producer uses Protobuf,
  connector is configured with AvroConverter.
CATEGORY: SINK_DLQ
EVIDENCE:
  - connector RUNNING, tasks[0] FAILED then restarted
  - DLQ topic s3-sink-dlq receiving ~200 records/min
  - Failing probe: DLQ header __connect.errors.exception =
    "SerializationException: Error deserializing Avro message";
    producer is Protobuf per producer config
  - Passing probes: no rebalance; IAM valid; topic exists
REMEDIATION:
  1. Change the sink converter to match the producer:
     aws kafkaconnect update-connector --connector-arn $ARN \
       --connector-configuration '{"value.converter":"io.confluent.connect.protobuf.ProtobufConverter",...}'
  2. Verify: aws kafkaconnect describe-connector --connector-arn $ARN
       --query 'connector.state'
  3. Drain the DLQ once the fix is verified.
```

## What the skill caught that a generic assistant misses

1. **DLQ headers decode to identify the exact failure.** A generic
   assistant stops at "your converter is wrong." The skill decodes
   the `__connect.errors.exception` header to confirm
   `AvroConverter` is the deserializer that threw — narrowing the
   category to SINK_DLQ, not CONFIG_ERROR.

2. **Passing probes rule out other categories.** The skill verifies
   no rebalance churn (not WORKER_REBALANCE), IAM valid (not
   IAM_AUTH), topic exists (not CONFIG_ERROR). A generic assistant
   skips the elimination step.

3. **Producer-side converter verified separately.** The skill pulls
   the producer config to confirm Protobuf, not Avro — establishing
   which side is wrong (the connector, not the producer). A generic
   assistant assumes the producer is wrong.

4. **`update-connector` CLI with explicit config.** The skill's
   REMEDIATION includes the exact `aws kafkaconnect update-connector`
   command with the corrected `value.converter` value, not a vague
   "fix your converter."

5. **DLQ drain as a post-fix step.** The skill notes that the DLQ
   must be drained after the fix is verified — a generic assistant
   leaves the DLQ records to be re-processed or forgotten.

## Slash-command invocation

```
/aws:troubleshoot-kafka-connect
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose the MSK Connect sink connector that is filling its DLQ"
```

## Live-account follow-up (optional, requires AWS CLI)

After applying the fix, validate the recovery:

```bash
# Verify the connector is RUNNING with healthy tasks
aws kafkaconnect describe-connector --connector-arn $ARN \
  --query 'connector.state'

# Verify DLQ is no longer receiving records
aws cloudwatch get-metric-statistics \
  --namespace AWS/KafkaConnect --metric-name ErrorRate \
  --dimensions Name=Connector,Value=s3-sink-connector \
  --start-time $(date -d '15 minutes ago' -Iseconds) \
  --end-time $(date -Iseconds) --period 60 --statistics Sum \
  --query 'Datapoints[].Sum'

# Verify throughput is non-zero on the sink
aws cloudwatch get-metric-statistics \
  --namespace AWS/KafkaConnect --metric-name RecordsOut \
  --dimensions Name=Connector,Value=s3-sink-connector \
  --start-time $(date -d '15 minutes ago' -Iseconds) \
  --end-time $(date -Iseconds) --period 60 --statistics Sum \
  --query 'Datapoints[].Sum'

# Drain the DLQ (after verifying the fix holds for 30+ minutes)
# Option 1: Use kafka-console-consumer to read and process DLQ records
# Option 2: Use MSK async operations to delete the DLQ topic
# Option 3: Configure the DLQ topic with a short retention to auto-expire
```
