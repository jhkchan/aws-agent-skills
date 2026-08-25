# Worked Examples — ElastiCache Cluster Deployer

Secondary worked examples moved verbatim from SKILL.md. Loaded on demand.

## Worked example — PREREQUISITES_MISSING (subnet group absent) (from SKILL.md)

```text
ELASTICACHE_CLUSTER: cache-dev (Redis OSS 7.0, cache.r6g.large, cluster mode enabled)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Engine: Redis OSS (version 7.0)
  [✓] Topology: Cluster mode enabled (3 shards x 1 replica = 6 nodes total)
  [✓] Node type: cache.r6g.large
  [✗] Subnet group: dev-redis-subnet-group — DOES NOT EXIST. Run `aws elasticache describe-cache-subnet-groups --cache-subnet-group-name dev-redis-subnet-group` returns ResourceNotFound. Create the subnet group with subnets in at least 2 AZs before deploying.
  [✓] Security group: sg-dev123456 (port 6379, inbound from sg-app-dev)
  [✓] Multi-AZ failover: Enabled (3 AZs planned)
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:123456789012:key/b2c3d4e5-6789-01ab-cdef-234567890abc)
  [✓] In-transit encryption (TLS): Enabled
  [✓] Snapshot window: 01:00-03:00 UTC (no overlap with maintenance wed:04:00-wed:05:00 UTC)
VERIFICATION_COMMANDS:
  aws elasticache describe-cache-subnet-groups --cache-subnet-group-name dev-redis-subnet-group --region us-east-1
  # Create the subnet group first, then re-invoke this skill
```
