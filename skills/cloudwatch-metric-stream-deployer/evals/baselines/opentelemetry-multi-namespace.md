# Baseline (no-skill) — opentelemetry-multi-namespace

> This is the response a model produces **without** the skill
> definition. It emits the command but does not flag that streaming
> four namespaces with ALL statistics (omitted) multiplies the output
> volume, does not note that Firehose buffering adds 1-5 minutes of
> latency (relevant for Datadog integration), and skips the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the metric stream:

```bash
aws cloudwatch put-metric-stream \
  --name OtelExportStream \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/otel-firehose \
  --role-arn arn:aws:iam::123456789012:role/CWMetricStreamRole \
  --output-format opentelemetry \
  --region us-east-1
```

Datadog can then pick up the metrics from the S3 bucket.
