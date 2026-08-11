# Eval: elasticache-redirect-boundary

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — workload is a disposable cache (cache-miss acceptable); MemoryDB is the wrong service (durable database, higher cost); redirect to ElastiCache (use elasticache-cache-deployer)

## Prompt

I need a simple Redis cache in AWS. The data is disposable — cache-
miss is fine, we'll just recompute. Provision a MemoryDB cluster
named "app-cache" in us-east-1 with db.r6g.large nodes. Account ID:
123456789012.
