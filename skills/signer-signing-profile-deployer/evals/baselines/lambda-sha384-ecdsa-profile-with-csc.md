# Baseline (no-skill) — lambda-sha384-ecdsa-profile-with-csc

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses that the platform
> fixes the cryptographic algorithm (no `--algorithm` flag), that
> `AllowedPublishingProfiles` requires the version suffix, that
> Lambda code signing is enforced at UPDATE not at runtime, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up a Signer profile:

```bash
aws signer put-signing-profile \
  --profile-name lambda-signing-prod \
  --platform-id AWSLambda-SHA384-ECDSA
```

Then make a CSC and attach it.

```bash
aws lambda create-code-signing-config \
  --allowed-publishers AllowedPublishingProfiles=arn:aws:signer:us-east-1:111122223333:/signing-profiles/lambda-signing-prod
```

That should cover it. Lambda will check signatures when the function
runs.
