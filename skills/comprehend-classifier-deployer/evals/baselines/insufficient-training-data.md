# Baseline (no-skill) — insufficient-training-data

> This is the response a model produces **without** the skill
> definition. It proceeds to train the classifier without flagging
> that the billing class has only 30 documents (below the 50-doc
> minimum per class). Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Sure, here's how to train the classifier:

```bash
aws comprehend create-document-classifier \
  --document-classifier-name email-router-classifier \
  --input-data-config S3Uri=s3://my-bucket/email/training/training.csv \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendRole
```

Then deploy the endpoint:

```bash
aws comprehend create-endpoint \
  --endpoint-name email-endpoint \
  --model-arn <classifier-arn> \
  --desired-inference-units 1
```
