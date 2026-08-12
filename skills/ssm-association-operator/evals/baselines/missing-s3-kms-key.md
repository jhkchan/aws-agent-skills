# Baseline (no-skill) — missing-s3-kms-key

> This is the response a model produces **without** the skill
> definition. It creates the association pointing at the SSE-S3
> (S3-managed keys) output bucket without flagging that production
> execution artifacts need a customer-managed KMS key. Does not emit
> a REVIEW_REQUIRED verdict. Generated for with-skill-vs-baseline
> comparison.

---

Here is the create-association command:

```bash
aws ssm create-association \
  --name AWS-ApplyPatchBaseline \
  --targets "Key=tag:Environment,Values=dev" \
  --schedule-expression "rate(1 hour)" \
  --max-concurrency 5 \
  --max-errors 2 \
  --output-location '{"S3Location":{"OutputS3BucketName":"dev-ssm-output","OutputS3KeyPrefix":"output/"}}' \
  --region us-east-1
```

The output will go to dev-ssm-output which is encrypted by default
with S3-managed keys, so it should be fine.
