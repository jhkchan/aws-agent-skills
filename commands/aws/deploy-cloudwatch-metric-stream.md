---
description: Deploys an Amazon CloudWatch Metric Stream with production defaults (Firehose ARN configuration, namespace include/exclude filter, statistics selection, JSON/OpenTelemetry output format, IAM role with cloudwatch.amazonaws.com trust, Firehose-to-S3 delivery with KMS encryption, cost-per-metric awareness). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create cloudwatch metric stream"
  - "metric stream firehose"
  - "cloudwatch to s3 metrics"
  - "metric stream namespace filter"
  - "metric stream opentelemetry"
  - "metric stream json"
  - "cloudwatch export metrics"
  - "metric stream cost"
  - "replace getmetricdata polling"
  - "continuous metric export"
  - "stream cloudwatch metrics"
  - "metric stream"
  - "cloudwatch metric stream"
routes_to: cloudwatch-metric-stream-deployer
---

# /aws:deploy-cloudwatch-metric-stream

Activate the `cloudwatch-metric-stream-deployer` skill and deploy an
Amazon CloudWatch Metric Stream with production-grade defaults.

## What it does

The skill walks the deployment procedure and emits a READY_TO_DEPLOY
checklist:

1. Pipeline architecture (CloudWatch → Firehose → S3)
2. Firehose ARN configuration (delivery stream binding)
3. Namespace filter (include/exclude for cost control)
4. Statistics (Average, Sum, p99, etc.)
5. Output format (JSON vs OpenTelemetry)
6. IAM role permissions (cloudwatch → firehose → s3 chain)
7. Cross-account metric streaming (multi-account observability)
8. Cost model (per-metric pricing, cost-benefit vs GetMetricData)
9. Firehose buffering latency (1-5 minute delivery delay)
10. CloudWatch API operations (PutMetricStream lifecycle)
11. Recent features (OpenTelemetry 1.1.0, percentile stats)

## When to use

- You need to create a CloudWatch metric stream.
- You want to continuously export CloudWatch metrics to S3.
- You are replacing GetMetricData API polling with a stream.
- You want to stream metrics in JSON or OpenTelemetry format.
- You need to filter by namespace (include/exclude) for cost control.
- You are configuring cross-account metric streaming.
- You want to understand metric stream cost (per-metric pricing).

## When NOT to use

- **CloudWatch Logs subscriptions** — metric streams export metrics,
  not logs. Use logs-subscription skills for log data.
- **CloudWatch dashboards** — use dashboard-deployer skills for
  building dashboards.
- **CloudWatch alarms** — use alarm-operator skills for creating
  alarms. Metric stream data has 1-5 min latency — do NOT use it for
  alerting.
- **X-Ray tracing** — metric streams export CloudWatch metrics only.
  Use X-Ray skills for distributed tracing.

## How to invoke

### Slash command

```
/aws:deploy-cloudwatch-metric-stream
```

Then provide: stream name, Firehose delivery stream name, output
format (JSON/OpenTelemetry), namespace filter (include/exclude list),
statistics, IAM role name, S3 bucket name, tags.

### Natural language

Any of these routes to the same skill:

- "create a cloudwatch metric stream to export metrics to s3"
- "stream cloudwatch metrics to s3 via firehose"
- "replace getmetricdata polling with a metric stream"
- "export ec2 and lambda metrics to s3 continuously"
- "set up an opentelemetry metric stream for datadog"
- "filter a metric stream to only the aws/ec2 namespace"

### CLI routing

```bash
node cli/bin/cli.js route "create cloudwatch metric stream"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create CloudWatch
metric streams. The output checklist feeds into verification pipelines
and downstream observability skills.

## Example

```
You: /aws:deploy-cloudwatch-metric-stream

     Create a metric stream that exports EC2, Lambda, and RDS
     metrics to S3 via Firehose. JSON format. Include namespaces
     AWS/EC2, AWS/Lambda, AWS/RDS. Use Firehose cw-metrics-to-s3.

Skill:
  METRIC_STREAM: ProductionMetricStream → cw-metrics-to-s3 → s3://my-cloudwatch-metrics/
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Firehose: cw-metrics-to-s3 (S3 destination, SSE-KMS)
    [✓] Namespace filter: IncludeFilter=[AWS/EC2, AWS/Lambda, AWS/RDS]
    [✓] Output format: json
    [✓] Statistics: Average Sum SampleCount Min Max
    [✓] IAM role: CWMetricStreamRole (trust: cloudwatch.amazonaws.com)
  VERIFICATION_COMMANDS:
    aws cloudwatch get-metric-stream --name ProductionMetricStream --region us-east-1
    aws firehose describe-delivery-stream --delivery-stream-name cw-metrics-to-s3 --region us-east-1
```

## References

- Skill definition: `skills/cloudwatch-metric-stream-deployer/SKILL.md`
- Firehose and output formats guide: `skills/cloudwatch-metric-stream-deployer/references/firehose-and-output-formats.md`
- Filters and cost guide: `skills/cloudwatch-metric-stream-deployer/references/filters-and-cost.md`
- Eval suite: `skills/cloudwatch-metric-stream-deployer/evals/evals.json`
