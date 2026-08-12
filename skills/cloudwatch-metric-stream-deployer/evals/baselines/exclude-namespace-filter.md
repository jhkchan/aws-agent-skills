# Baseline (no-skill) — exclude-namespace-filter

> This is the response a model produces **without** the skill
> definition. It creates the stream but does not flag the cost
> implication of streaming ALL non-excluded namespaces (which can be
> hundreds of thousands of metrics in a busy account), omits the
> statistics parameter, and skips the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Here is the command:

```bash
aws cloudwatch put-metric-stream \
  --name OpsAllExceptLogs \
  --firehose-arn arn:aws:firehose:us-east-1:123456789012:deliverystream/ops-firehose \
  --role-arn arn:aws:iam::123456789012:role/CWMetricStreamRole \
  --output-format json \
  --exclude-filters '[{"Namespace":"AWS/Logs"}]' \
  --region us-east-1
```

This will stream everything except AWS/Logs.
