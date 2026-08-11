# Baseline (no-skill) — augmented-manifest-ground-truth

> This is the response a model produces **without** the skill
> definition. It does not recognize the Augmented Manifest format from
> Ground Truth, does not specify the data-format parameter, misses
> per-class document count verification, and does not emit a
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Upload the manifest and train:

```bash
aws comprehend create-document-classifier \
  --document-classifier-name review-sentiment-classifier \
  --input-data-config S3Uri=s3://my-bucket/reviews/labeled/manifest.jsonl \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendRole
```

Then create the endpoint:

```bash
aws comprehend create-endpoint \
  --endpoint-name review-endpoint \
  --model-arn <classifier-arn> \
  --desired-inference-units 1
```
