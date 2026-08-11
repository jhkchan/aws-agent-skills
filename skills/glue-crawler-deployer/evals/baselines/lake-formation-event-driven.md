# Baseline (no-skill) — lake-formation-event-driven

> This is the response a model produces **without** the skill
> definition. It creates the crawler but misses the Lake Formation
> permissions requirement (crawler fails with AccessDeniedException
> on LF-enabled databases), the S3 Event Notification setup for
> event-driven crawl, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the crawler:

```bash
aws glue create-crawler --name lf-logs-crawler \
  --role GlueLFCrawlerRole \
  --database-name lf_analytics_db \
  --targets '{"S3Targets":[{"Path":"s3://my-data-lake/logs/"}]}'
```

Then add the Grok classifier.
