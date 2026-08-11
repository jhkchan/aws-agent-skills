# Eval: production-multiaz-durable

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, Multi-AZ shard-level failover + TLS (on by default) + named ACL (not open-access) + customer CMK + snapshots

## Prompt

Provision a production Amazon MemoryDB for Redis cluster named
"prod-memorydb" in us-east-1. This is a durable in-memory database —
the data MUST survive node failure. Use 3 shards with 1 replica per
shard for Multi-AZ failover. db.r6g.24xlarge nodes. Engine version
7.0. Customer-managed CMK alias/prod-memorydb-kms. TLS should be on
(default). Create a named ACL "prod-acl" with users app-rw
(read-write) and analytics-ro (read-only). Snapshots: 7-day
retention, window 03:00-05:00 UTC. Maintenance window
sun:05:00-sun:07:00. Subnet group prod-memorydb-subnet spans 3 AZs.
Security group sg-memorydb123 inbound 6379 from sg-app456. Tags:
Environment=production, Workload=in-memory-db. Account ID:
123456789012.
