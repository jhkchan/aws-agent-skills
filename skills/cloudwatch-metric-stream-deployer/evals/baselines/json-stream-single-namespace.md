# Baseline (no-skill) — json-stream-single-namespace

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but omits the namespace include
> filter (streams ALL namespaces — most expensive option), omits the
> statistics parameter (defaults to ALL statistics), does not verify
> the IAM role trust policy, and skips the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Here is the create command:

```bash
aws cloudwatch put-metric-stream \
  --name Ec2MetricStream \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3 \
  --role-arn arn:aws:iam::123456789012:role/CWMetricStreamRole \
  --output-format json \
  --region us-east-1
```

That will start streaming your CloudWatch metrics to S3.
