# Baseline (no-skill) — tag-target-scheduled-association

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but uses percentage-string rate
> control (max-concurrency "10%") instead of the integer form, omits
> the dynamic-vs-static targeting flag, does not set
> apply-at-creation, does not verify the KMS key on the output
> bucket, and skips the OPERATION_COMPLETED checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here is the create-association command:

```bash
aws ssm create-association \
  --name AWS-ApplyPatchBaseline \
  --targets "Key=tag:Environment,Values=production" \
  --schedule-expression "rate(30 minutes)" \
  --max-concurrency "10%" \
  --max-errors "5%" \
  --parameters Operation=Install,SnapshotId=latest \
  --output-location '{"S3Location":{"OutputS3BucketName":"my-ssm-output","OutputS3KeyPrefix":"ssm-output/"}}' \
  --region us-east-1
```

That should set up the patching. The association will run every 30
minutes.
