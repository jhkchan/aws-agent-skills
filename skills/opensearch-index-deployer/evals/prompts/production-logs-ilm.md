# Eval: production-logs-ilm

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — production logs index with strict mapping, 5 primary shards for 150 GB, ILM rollover at 50 GB/1d, warm at 7d, delete at 90d, rollover alias

## Prompt

Create an OpenSearch index for application logs on domain
search-mydomain-abc123.us-east-1.es.amazonaws.com. Estimated
150 GB of logs per day. Use strict dynamic mapping. 5 primary
shards, 1 replica. Create an ILM policy that rolls over at
50 GB or 1 day, moves to warm after 7 days, and deletes after
90 days. Rollover alias logs-app-write. Index template
logs-template for pattern logs-app-*. Tags: Environment=
production, Application=app-logs.
