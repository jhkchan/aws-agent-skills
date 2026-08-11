# Baseline (no-skill) — signing-job-from-s3-source

> This is the response a model produces **without** the skill
> definition. It submits the signing job but does not flag the
> immutability of the resulting artifact, does not call out that
> UpdateFunctionCode must point at the SIGNED destination (not the
> unsigned source), and does not emit the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Run the signing job:

```bash
aws signer start-signing-job \
  --source 'source={s3={bucketName=my-unsigned-artifacts,key=lambda/my-prod-function.zip,version=v1abc}}' \
  --destination 'destination={s3={bucket=my-signed-artifacts,prefix=lambda/signed/}}' \
  --profile-name lambda-signing-prod
```

Then deploy the function.
