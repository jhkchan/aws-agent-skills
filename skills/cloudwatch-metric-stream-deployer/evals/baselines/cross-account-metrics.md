# Baseline (no-skill) — cross-account-metrics

> This is the response a model produces **without** the skill
> definition. It creates the stream but does not flag the cross-
> account IAM requirements (the Firehose resource policy or the role
> must explicitly allow the workload account principal), does not
> verify the trust policy on the cross-account role, and skips the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the metric stream:

```bash
aws cloudwatch put-metric-stream \
  --name WorkloadA-to-Observability \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/central-firehose \
  --role-arn arn:aws:iam::111111111111:role/CWMetricStreamCrossAcctRole \
  --output-format json \
  --include-filters '[{"Namespace":"AWS/EC2"},{"Namespace":"AWS/Lambda"},{"Namespace":"ApplicationMetrics"}]' \
  --region us-east-1
```

The metrics should show up in the observability account's S3 bucket.
