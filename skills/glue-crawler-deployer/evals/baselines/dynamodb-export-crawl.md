# Baseline (no-skill) — dynamodb-export-crawl

> This is the response a model produces **without** the skill
> definition. It tries to crawl DynamoDB directly instead of reading
> from the S3 export path, misses the DYNAMODB_JSON format
> requirement, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the crawler pointing at the DynamoDB table:

```bash
aws glue create-crawler --name ddb-crawler \
  --role GlueCrawlerRole \
  --database-name dynamo_db \
  --targets '{"DynamoDBTargets":[{"Path":"UserEvents"}]}'
```
