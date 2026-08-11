# Eval: data-tiering-cost-optimized

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — data tiering enabled at creation (one-way door) with db.r6gd.24xlarge; Multi-AZ; named ACL

## Prompt

Provision a MemoryDB for Redis cluster named "analytics-db" in
us-east-1 for a 1.5 TB dataset with a 30/70 hot/cold access split.
Use db.r6gd.24xlarge nodes with data tiering enabled (the cold set
should go to SSD). 3 shards with 1 replica each for Multi-AZ. Engine
version 7.0. Named ACL "analytics-acl" with user app-rw. Snapshots
7 days. Subnet group analytics-subnet spans 3 AZs. Security group
sg-analytics inbound 6379 from sg-analytics-app. Tags:
Environment=production, Workload=analytics-tiered. Account ID:
123456789012.
