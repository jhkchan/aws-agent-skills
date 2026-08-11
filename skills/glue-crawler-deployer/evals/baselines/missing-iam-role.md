# Baseline (no-skill) — missing-iam-role

> This is the response a model produces **without** the skill
> definition. It proceeds to create the crawler without flagging the
> missing IAM role and S3 data source path, leading to API call
> failures. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here is the crawler:

```bash
aws glue create-crawler --name my-crawler \
  --role some-role \
  --database-name default \
  --targets '{"S3Targets":[{"Path":"s3://my-bucket/data/"}]}'
```
