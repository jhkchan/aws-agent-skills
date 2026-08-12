# Baseline (no-skill) — missing-firehose-role

> This is the response a model produces **without** the skill
> definition. It creates the metric stream without flagging that the
> IAM role's trust policy is missing cloudwatch.amazonaws.com — the
> stream would enter "running" status but silently deliver nothing.
> Does not emit a PREREQUISITES_MISSING verdict. Generated for with-
> skill-vs-baseline comparison.

---

Here is the create command:

```bash
aws cloudwatch put-metric-stream \
  --name BrokenStream \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/cw-metrics-to-s3 \
  --role-arn arn:aws:iam::123456789012:role/MyFirehoseRole \
  --output-format json \
  --include-filters '[{"Namespace":"AWS/EC2"}]' \
  --region us-east-1
```

The stream should start delivering EC2 metrics to S3 shortly.
