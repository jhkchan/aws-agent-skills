# Eval: neptune-cluster-gremlin

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY

## Prompt

Create Amazon Neptune cluster neptune-graph-prod in us-east-1. Primary db.r6g.large + 2 read replicas. Engine 1.3.0.0. KMS encryption. Subnet group neptune-subnet-prod. Security group sg-neptune-prod. neptune_enforce_ssl=1, neptune_query_timeout=120000. Neptune Streams. Backup 7 days.
