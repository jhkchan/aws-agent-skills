# Eval: global-cluster-dr

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — global cluster, primary us-east-1, secondary eu-west-1, r5.2xlarge, failover scripting noted

## Prompt

Create a DocumentDB global cluster named orders-global. Primary
cluster orders-docdb-primary in us-east-1 with db.r5.2xlarge,
1 primary + 2 replicas. Secondary cluster orders-docdb-secondary
in eu-west-1 with db.r5.2xlarge, 1 primary + 2 replicas. Engine
5.0. KMS encryption. Backup 7 days. Tags: Environment=production,
DR=active-active.
