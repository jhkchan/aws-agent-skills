# Baseline (no-skill) — native-pdf-vpc-kms

> This is the response a model produces **without** the skill
> definition. It misses the Native PDF input mode flag, uses CSV
> format instead of Augmented Manifest, omits VPC config and KMS
> encryption parameters, and does not emit a READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Train the classifier:

```bash
aws comprehend create-document-classifier \
  --document-classifier-name document-type-classifier \
  --input-data-config S3Uri=s3://my-bucket/docs/training/pdf_manifest.jsonl \
  --language-code en \
  --role-arn arn:aws:iam::123456789012:role/ComprehendSecureRole
```

Then deploy the endpoint:

```bash
aws comprehend create-endpoint \
  --endpoint-name doc-classifier-endpoint \
  --model-arn <classifier-arn> \
  --desired-inference-units 2
```
