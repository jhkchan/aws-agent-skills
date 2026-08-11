# Eval: s3-crawler-classifier-projection

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — S3 crawler with EventsJsonClassifier listed before built-in JSON, partition projection for year/month/day, incremental crawl, daily cron

## Prompt

Create a Glue Crawler for S3 data at
s3://my-data-lake/events/year=2026/. Data is JSON files with
nested event_id, timestamp, event_type, and payload fields.
Create a custom JSON classifier named EventsJsonClassifier.
Use partition projection for year, month, and day columns.
Database analytics_db. Incremental crawl. Daily schedule at
2 AM UTC. Table prefix raw_. Tags: Environment=production,
DataSource=s3-events.
