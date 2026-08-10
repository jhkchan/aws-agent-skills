# Eval: session-store-redis-replication

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — session store with cluster mode disabled, noeviction (sessions must NOT be silently evicted), Multi-AZ failover

## Prompt

Provision an ElastiCache Redis cluster named "prod-sessions" in
us-east-1 for a session store. Session IDs are UUIDs; writes are
modest (~5k writes/sec, will not grow). Use cluster mode DISABLED
with 1 primary + 1 replica for Multi-AZ failover. The maxmemory-policy
must NOT evict silently (sessions would be lost) — use noeviction.
cache.r6g.large nodes. TLS + AUTH enabled. Customer CMK
alias/sessions-kms for encryption at rest. Snapshots 7 days, window
04:00-06:00 UTC. Subnet group prod-sessions-subnet spans 3 AZs.
Security group sg-sessions inbound 6379 from sg-app. Tags:
Environment=production, Workload=session-store. Account ID:
123456789012.
