# Eval: lake-formation-event-driven

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — LF-enabled database, LF permissions on crawler role, event-driven via S3 Event Notifications, Grok classifier, MergeNewColumns

## Prompt

Create a Glue Crawler for S3 data at s3://my-data-lake/logs/.
The database lf_analytics_db is Lake Formation-enabled. Crawler
role GlueLFCrawlerRole needs LF permissions. Event-driven crawl
triggered by S3 ObjectCreated events on the logs/ prefix.
Custom Grok classifier AppLogClassifier for log parsing.
MergeNewColumns schema policy. Tags: Environment=production,
Governance=lake-formation.
