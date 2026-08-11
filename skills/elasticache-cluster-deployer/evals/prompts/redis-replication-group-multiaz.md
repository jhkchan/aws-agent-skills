# Eval: redis-replication-group-multiaz

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY

## Prompt

Create an ElastiCache Redis replication group cache-redis-prod in us-east-1 with cluster mode enabled, 3 shards, 1 replica per shard, node type cache.r6g.large, multi-AZ automatic failover enabled, encryption at-rest with KMS, in-transit TLS enabled with AUTH token, automated backup retention 7 days, subnet group cache-subnet-prod, security group sg-redis-prod.
