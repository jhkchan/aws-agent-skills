# Baseline (no-skill) — semantic-version-update

> This is the response a model produces **without** the skill
> definition. It updates the version but does not explain that
> versions are immutable (1.0.0 is preserved), does not classify
> the bump as MINOR (backward-compatible), and omits the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Update the app to version 1.1.0:

```bash
aws serverlessrepo create-application \
  --application-id "arn:aws:serverlessrepo:us-east-1:123456789012:apps/s3-file-processor" \
  --semantic-version "1.1.0" \
  --template-body file://packaged.yaml
```

That should overwrite the old version.
