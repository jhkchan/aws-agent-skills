# Eval: switchover-with-validation

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — switchover of existing Blue/Green after green validation passed, switchover timeout 600s, endpoint CNAME auto-follow

## Prompt

I have an RDS Blue/Green Deployment bg-prod-upgrade-2026 for my
Aurora PostgreSQL cluster prod-pg-cluster (aurora-postgresql 13.9)
in us-east-1. The green environment green-prod-pg-cluster is
running PostgreSQL 15.4. Green validation passed: engine version
confirmed, replication lag is under 1 second, query performance is
within baseline. I want to switch over. Switchover timeout 600
seconds. My application uses the cluster endpoint and has retry
logic.
