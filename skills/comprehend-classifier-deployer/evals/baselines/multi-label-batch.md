# Baseline (no-skill) — multi-label-batch

> This is the response a model produces **without** the skill
> definition. It suggests an endpoint deployment instead of batch for
> a nightly 50k-document workload, misses the multi-label mode
> distinction, does not verify per-label document counts, and does not
> emit a READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Train the classifier and deploy an endpoint:

```bash
aws comprehend create-document-classifier \
  --document-classifier-name news-tag-classifier \
  --input-data-config S3Uri=s3://my-bucket/news/training/manifest.jsonl \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendBatchRole

aws comprehend create-endpoint \
  --endpoint-name news-endpoint \
  --model-arn <classifier-arn> \
  --desired-inference-units 1
```

Then classify articles one by one.
