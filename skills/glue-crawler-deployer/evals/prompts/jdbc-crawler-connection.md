# Eval: jdbc-crawler-connection

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — JDBC crawler using pg-connection Glue Connection, public schema, full crawl, on-demand

## Prompt

Create a Glue Crawler for a PostgreSQL database. Glue Connection
name pg-connection. Crawl the public schema. Database jdbc_db.
Full crawl. On-demand schedule initially. IAM role
GlueJdbcCrawlerRole. Tags: Environment=production,
Source=postgresql.
