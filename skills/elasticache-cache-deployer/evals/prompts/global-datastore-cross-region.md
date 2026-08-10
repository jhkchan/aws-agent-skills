# Eval: global-datastore-cross-region

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Global Datastore cross-region replication; primary cluster mode enabled; each region its own CMK

## Prompt

Provision an ElastiCache Redis Global Datastore named "prod-geo-cache"
with primary in us-east-1 and secondary in eu-west-1. Primary cluster
prod-geo-cache-us-east-1 is cluster mode enabled (3 shards, 1 replica
each, Multi-AZ). Secondary cluster prod-geo-cache-eu-west-1 mirrors
the topology. Both use cache.r6g.2xlarge, customer CMK
(alias/geo-cache-kms-us and alias/geo-cache-kms-eu respectively, each
in its region). TLS + AUTH enabled everywhere. Snapshots 7 days.
Subnet groups in each region span 3 AZs. Tags: Environment=production,
Workload=geo-cache. Account ID: 123456789012.
