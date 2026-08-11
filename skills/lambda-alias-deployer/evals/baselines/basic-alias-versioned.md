# Baseline (no-skill) — basic-alias-versioned

> This is the response a model produces **without** the skill
> definition. It provides CLI commands but does not verify the
> published version exists, does not configure the API Gateway
> integration with the alias qualifier (invokes $LATEST instead),
> does not create the CloudWatch alarm with the Resource dimension,
> and does not emit the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

To create a Lambda alias:

```bash
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version 5
```

Then update your API Gateway to point to the alias.
