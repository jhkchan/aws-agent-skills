# End-to-End Example: Kinesis Stream Deployment

A walkthrough showing how to use the `kinesis-stream-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an on-demand Kinesis Data Stream for telemetry
ingestion with an enhanced fan-out consumer and SSE-KMS encryption.
The stream needs:

- Stream name: telemetry-ingest
- Stream mode: ON_DEMAND (bursty traffic, unpredictable)
- Enhanced fan-out consumer: realtime-processor (low-latency, dedicated read)
- SSE-KMS: customer-managed key (alias/kinesis/telemetry-ingest)
- Retention: 168 hours (7 days)
- CloudWatch alarm: IteratorAgeMilliseconds > 300000ms

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-kinesis-stream
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Kinesis Data Stream named telemetry-ingest in
      us-east-1. On-demand mode. Enhanced fan-out consumer
      realtime-processor. SSE-KMS with CMK. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a kinesis stream"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
KINESIS_STREAM: telemetry-ingest (arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Stream name: telemetry-ingest
  [✓] Stream mode: ON_DEMAND
  [✓] Shard count: N/A (on-demand auto-scales)
  [✓] Retention period: 168 hours (7 days)
  [✓] Enhanced fan-out: realtime-processor (consumer ARN)
  [✓] SSE-KMS: enabled (key alias/kinesis/telemetry-ingest)
  [✓] KMS key policy: permits kinesis.amazonaws.com (GenerateDataKey, Decrypt)
  [✓] Producer IAM: EC2-producer-role → kinesis:PutRecord, PutRecords on stream ARN
  [✓] Consumer IAM: Lambda-consumer-role → kinesis:SubscribeToShard on stream + consumer ARN
  [✓] CloudWatch alarm: IteratorAgeMilliseconds > 300000 → arn:aws:sns:us-east-1:123456789012:alerts
  [✓] CloudWatch alarm: N/A (on-demand mode — no WriteProvisionedThroughputExceeded)
  [✓] Tags: Environment=production, Service=telemetry, Team=data-platform
VERIFICATION_COMMANDS:
  aws kinesis describe-stream-summary --stream-name telemetry-ingest --region us-east-1
  aws kinesis list-stream-consumers --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest --region us-east-1
  aws kinesis describe-stream --stream-name telemetry-ingest --query 'StreamDescription.{Encryption:EncryptionType,KeyId:KeyId}' --region us-east-1
  aws cloudwatch describe-alarms --alarm-name-prefix "Kinesis-telemetry-ingest" --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the on-demand stream
aws kinesis create-stream \
  --stream-name telemetry-ingest \
  --stream-mode-details StreamMode=ON_DEMAND \
  --region us-east-1

# Step 2: Wait for ACTIVE
aws kinesis wait stream-exists --stream-name telemetry-ingest --region us-east-1

# Step 3: Set retention to 168 hours
aws kinesis increase-stream-retention-period \
  --stream-name telemetry-ingest --retention-period-hours 168 --region us-east-1

# Step 4: Enable SSE-KMS with CMK
aws kinesis start-stream-encryption \
  --stream-name telemetry-ingest --encryption-type KMS \
  --key-id alias/kinesis/telemetry-ingest --region us-east-1

# Step 5: Register enhanced fan-out consumer
aws kinesis register-stream-consumer \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest \
  --consumer-name realtime-processor --region us-east-1

# Step 6: Create CloudWatch alarm for IteratorAge
aws cloudwatch put-metric-alarm \
  --alarm-name "Kinesis-telemetry-ingest-IteratorAge-High" \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --namespace AWS/Kinesis --statistic Maximum --period 300 \
  --threshold 300000 --comparison-operator GreaterThanThreshold \
  --dimensions Name=StreamName,Value=telemetry-ingest \
  --evaluation-periods 3 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts
```

---

## Step 4 — Post-deployment verification

```bash
# Stream status and mode
aws kinesis describe-stream-summary \
  --stream-name telemetry-ingest --region us-east-1 \
  --query 'StreamDescriptionSummary.{Status:StreamStatus,Mode:StreamModeDetails.StreamMode,Retention:RetentionPeriodHours}'

# Consumer registered
aws kinesis list-stream-consumers \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/telemetry-ingest \
  --region us-east-1

# Encryption enabled
aws kinesis describe-stream \
  --stream-name telemetry-ingest --region us-east-1 \
  --query 'StreamDescription.{EncryptionType:EncryptionType,KeyId:KeyId}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Stream mode | Default provisioned with shard-count 1 | ON_DEMAND (user requested; shard count irrelevant) | Shard count is ignored in on-demand mode |
| Enhanced fan-out | Not registered; consumer uses GetRecords | Consumer registered; SubscribeToShard IAM required | Enhanced fan-out needs dedicated consumer + API |
| SSE-KMS | AWS-managed key or not enabled | CMK with key policy permitting kinesis service | CMK key policy MUST allow kinesis.amazonaws.com |
| Consumer IAM | GetRecords only | SubscribeToShard on stream + consumer ARN | Enhanced fan-out needs consumer ARN in Resource |
| CloudWatch | No alarm or generic threshold | IteratorAge > 300000ms (relative to 168h retention) | Threshold must be relative to retention period |

---

## Related artifacts

- **Skill definition:** `skills/kinesis-stream-deployer/SKILL.md`
- **Stream mode and scaling guide:** `skills/kinesis-stream-deployer/references/stream-mode-and-scaling.md`
- **IAM and encryption guide:** `skills/kinesis-stream-deployer/references/iam-and-encryption.md`
- **Slash command:** `commands/aws/deploy-kinesis-stream.md`
- **Eval suite:** `skills/kinesis-stream-deployer/evals/evals.json`
- **Legacy test cases:** `skills/kinesis-stream-deployer/eval/test-cases.yaml`
