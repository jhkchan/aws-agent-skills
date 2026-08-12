# End-to-End Example: CloudWatch Metric Stream Deployment

A walkthrough showing how to use the `cloudwatch-metric-stream-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a CloudWatch metric stream that continuously exports
EC2, Lambda, and RDS metrics to S3 via Kinesis Data Firehose. The
stream needs:

- Name: ProductionMetricStream
- Output format: JSON
- Include filter: AWS/EC2, AWS/Lambda, AWS/RDS
- Statistics: Average, Sum, SampleCount, Min, Max
- Firehose: cw-metrics-to-s3 (delivers to s3://my-cloudwatch-metrics/)
- S3 bucket: SSE-KMS with customer-managed key
- Tags: Environment=production, Owner=cloudops

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloudwatch-metric-stream
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CloudWatch metric stream that exports EC2, Lambda,
      and RDS metrics to S3 via Firehose. JSON format. Use the
      cw-metrics-to-s3 delivery stream."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create cloudwatch metric stream"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
METRIC_STREAM: ProductionMetricStream → cw-metrics-to-s3 → s3://my-cloudwatch-metrics/cloudwatch-metrics/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] S3 bucket: s3://my-cloudwatch-metrics/cloudwatch-metrics/ (SSE-KMS, key arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Firehose delivery stream: cw-metrics-to-s3 (S3 destination, GZIP, 5MB/300s buffer)
  [✓] IAM role: CWMetricStreamRole (trust: cloudwatch.amazonaws.com, perms: firehose:PutRecord/PutRecordBatch)
  [✓] Namespace filter: IncludeFilter=[AWS/EC2, AWS/Lambda, AWS/RDS]
  [✓] Statistics: Average Sum SampleCount Min Max
  [✓] Output format: json
  [✓] Firehose buffering: 5MB / 300s (latency: ~5 min)
  [✓] Cost estimate: ~1500 unique metrics × $0.003 = ~$4.50/month
  [✓] Cross-account: none
  [✓] Tags: Environment=production, Owner=cloudops
VERIFICATION_COMMANDS:
  aws cloudwatch get-metric-stream --name ProductionMetricStream --region us-east-1
  aws cloudwatch list-metric-streams --region us-east-1
  aws firehose describe-delivery-stream --delivery-stream-name cw-metrics-to-s3 --region us-east-1
  aws s3 ls s3://my-cloudwatch-metrics/cloudwatch-metrics/ --region us-east-1 | head -5
```

---

## Step 3 — Provisioning commands

```bash
# Step 0: verify prerequisites
aws firehose describe-delivery-stream \
  --delivery-stream-name cw-metrics-to-s3 \
  --query 'DeliveryStreamDescription.{Status:DeliveryStreamStatus,Dest:Destinations[0].S3DestinationDescription.BucketARN}' \
  --region us-east-1

aws iam get-role \
  --role-name CWMetricStreamRole \
  --query 'Role.AssumeRolePolicyDocument' --output json --region us-east-1

aws s3api get-bucket-encryption \
  --bucket my-cloudwatch-metrics --region us-east-1

# Step 1: create the metric stream
STREAM_NAME=$(aws cloudwatch put-metric-stream \
  --name "ProductionMetricStream" \
  --firehose-arn "arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3" \
  --role-arn "arn:aws:iam::123456789012:role/CWMetricStreamRole" \
  --output-format "json" \
  --include-filters '[{"Namespace":"AWS/EC2"},{"Namespace":"AWS/Lambda"},{"Namespace":"AWS/RDS"}]' \
  --statistics "Average Sum SampleCount Min Max" \
  --tags "Key=Environment,Value=production" "Key=Owner,Value=cloudops" \
  --query 'Arn' \
  --region us-east-1 --output text)

echo "Metric stream ARN: $STREAM_NAME"

# Step 2: wait for first data (1-5 min Firehose buffering)
echo "Waiting 5 minutes for first Firehose delivery..."
sleep 300

# Step 3: verify data in S3
aws s3 ls "s3://my-cloudwatch-metrics/cloudwatch-metrics/" \
  --region us-east-1 --recursive | head -10
```

---

## Step 4 — Post-deployment verification

```bash
# Metric stream status — should be "running"
aws cloudwatch get-metric-stream \
  --name "ProductionMetricStream" \
  --query 'MetricStream.{Name:Name,State:State,FirehoseArn:FirehoseArn,Format:OutputFormat}' \
  --region us-east-1

# Firehose delivery health
aws firehose describe-delivery-stream \
  --delivery-stream-name cw-metrics-to-s3 \
  --query 'DeliveryStreamDescription.{Status:DeliveryStreamStatus,Age:CreateTimestamp}' \
  --region us-east-1

# S3 data verification — should show GZIP files from the last 5 min
aws s3 ls "s3://my-cloudwatch-metrics/cloudwatch-metrics/" \
  --region us-east-1 --recursive | tail -5

# Sample the data (download and inspect one file)
LATEST_FILE=$(aws s3 ls "s3://my-cloudwatch-metrics/cloudwatch-metrics/" \
  --region us-east-1 --recursive | sort | tail -1 | awk '{print $4}')
aws s3 cp "s3://my-cloudwatch-metrics/$LATEST_FILE" /tmp/sample.gz --region us-east-1
gunzip -c /tmp/sample.gz | head -5
```

---

## Step 5 — Set up monitoring and cost alerts

```bash
# Alarm on Firehose data freshness (detect stalled delivery)
aws cloudwatch put-metric-alarm \
  --alarm-name "firehose-metric-stream-stale" \
  --metric-name "DeliveryToS3.DataFreshness" \
  --namespace "AWS/Firehose" \
  --statistic "Maximum" \
  --period 300 \
  --threshold 600 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=DeliveryStreamName,Value=cw-metrics-to-s3" \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cloudops-alerts" \
  --region us-east-1

# Billing alarm on metric stream costs (via Cost Explorer anomaly detection
# or CloudWatch billing alarm scoped to CloudWatch)
aws cloudwatch put-metric-alarm \
  --alarm-name "cloudwatch-cost-anomaly" \
  --metric-name "EstimatedCharges" \
  --namespace "AWS/Billing" \
  --statistic "Maximum" \
  --period 86400 \
  --threshold 50 \
  --comparison-operator "GreaterThanThreshold" \
  --dimensions "Name=Currency,Value=USD" \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cloudops-alerts" \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Namespace filter | No filter (stream everything) | IncludeFilter=[AWS/EC2, AWS/Lambda, AWS/RDS] | Without a filter, ALL metrics are streamed — 10x+ cost |
| Statistics | All statistics (default) | Specific statistics: Average Sum SampleCount Min Max | Omitting statistics multiplies output volume by 5-7x |
| IAM role trust | Does not verify trust policy | Verifies trust includes cloudwatch.amazonaws.com | Without correct trust, stream shows "running" but delivers nothing |
| Firehose latency | Assumes real-time | Notes 1-5 min buffering delay | Real-time alerting needs CloudWatch alarms directly, not metric stream |
| Cost model | No cost estimate | Per-metric cost estimate ($0.003 × N metrics) | Cost awareness prevents bill surprises |
| Output format | Picks JSON by default | Asks about consumer (AWS-native vs third-party) | OpenTelemetry for Datadog/Grafana; JSON for Athena |
| S3 encryption | No KMS verification | Verifies SSE-KMS with customer-managed key | Metric data at rest needs encryption |
| Firehose role | Confuses with metric stream role | Two distinct roles documented | Missing either role causes silent failure |

---

## Related artifacts

- **Skill definition:** `skills/cloudwatch-metric-stream-deployer/SKILL.md`
- **Firehose and output formats guide:** `skills/cloudwatch-metric-stream-deployer/references/firehose-and-output-formats.md`
- **Filters and cost guide:** `skills/cloudwatch-metric-stream-deployer/references/filters-and-cost.md`
- **Slash command:** `commands/aws/deploy-cloudwatch-metric-stream.md`
- **Eval suite:** `skills/cloudwatch-metric-stream-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloudwatch-metric-stream-deployer/eval/test-cases.yaml`
