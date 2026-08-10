# Eval: production-redis-cluster-mode

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, cluster mode enabled + Multi-AZ + customer CMK + TLS + AUTH + allkeys-lru + snapshots

## Prompt

Provision a production ElastiCache Redis cluster named "prod-cache" in
us-east-1. We need cluster mode enabled with 3 shards (1 replica per
shard for Multi-AZ failover). Traffic is mixed read/write at ~80k
writes/sec sustained. Use cache.r6g.2xlarge nodes. The cluster is a
general-purpose cache (data is disposable). Use customer-managed CMK
alias/prod-cache-kms for encryption at rest. Enable TLS and AUTH
(token in Secrets Manager). Snapshots: 7-day retention, window
03:00-05:00 UTC. Subnet group prod-cache-subnet spans 3 AZs. Security
group sg-cache123 has inbound 6379 from sg-app456. Tags:
Environment=production, Workload=cache. Account ID: 123456789012.
