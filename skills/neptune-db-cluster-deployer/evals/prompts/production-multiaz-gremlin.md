# Eval: production-multiaz-gremlin

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, Multi-AZ reader promotion + customer CMK + neptune_enforce_ssl + IAM database auth + Streams + snapshots

## Prompt

Provision a production Amazon Neptune DB cluster named "prod-graph" in
us-east-1 for a Gremlin property-graph workload. We need 1 writer + 2
readers across 3 AZs for Multi-AZ failover. Use db.r6g.8xlarge
instances. Engine version 1.3.2.0. The graph is ~200M vertices + 1B
edges. Customer-managed CMK alias/prod-graph-kms for encryption at
rest. Enable TLS (neptune_enforce_ssl=1) and IAM database auth. Set
neptune_query_timeout=30000 (OLTP queries). Enable Neptune Streams
for change capture. Snapshots: 7-day retention. Deletion protection
enabled. Subnet group prod-neptune-subnet spans 3 AZs. Security
group sg-neptune123 inbound 8182 from sg-app456. Tags:
Environment=production, Workload=graph. Account ID: 123456789012.
