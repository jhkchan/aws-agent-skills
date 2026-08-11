# Baseline (no-skill) — s3-crawler-classifier-projection

> This is the response a model produces **without** the skill
> definition. It creates the crawler but misses the classifier
> ordering (first-match-wins), the partition projection configuration
> (table properties), the incremental crawl trade-off explanation,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the crawler:

```bash
aws glue create-crawler --name events-crawler \
  --role GlueCrawlerRole \
  --database-name analytics_db \
  --targets '{"S3Targets":[{"Path":"s3://my-data-lake/events/"}]}'
```

Then create the JSON classifier and schedule it.
