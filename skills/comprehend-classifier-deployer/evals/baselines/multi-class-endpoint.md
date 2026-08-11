# Baseline (no-skill) — multi-class-endpoint

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the multi-class vs
> multi-label mode selection rationale, the per-class document count
> verification, the endpoint-vs-batch cost trade-off analysis, the KMS
> encryption for both model artifacts AND volume, the auto-scaling
> configuration, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

You can train a Comprehend classifier like this:

```bash
aws comprehend create-document-classifier \
  --document-classifier-name support-ticket-classifier \
  --input-data-config S3Uri=s3://my-bucket/comprehend/training/training.csv \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendTrainingRole
```

Then create an endpoint:

```bash
aws comprehend create-endpoint \
  --endpoint-name ticket-endpoint \
  --model-arn <classifier-arn> \
  --desired-inference-units 1
```
