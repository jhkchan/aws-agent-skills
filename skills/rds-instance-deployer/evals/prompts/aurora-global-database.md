# Eval: aurora-global-database

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Global Database with cross-region DR + Backtrack + per-region CMKs

## Prompt

Provision an Aurora MySQL Global Database for a global commerce
workload. Primary cluster "commerce-global-primary" in us-east-1,
secondary cluster "commerce-global-secondary" in eu-west-1 (read-only
DR). Engine aurora-mysql 8.0. Instance class db.r7g.large. Use
separate customer CMKs: alias/commerce-rds-key in us-east-1,
alias/commerce-rds-key-eu in eu-west-1. Backtrack window 72 hours
on primary. 14-day backup retention. Enhanced Monitoring + Performance
Insights on both clusters. Force SSL via cluster parameter group.
Deletion protection on both clusters. Tags: Environment=production,
Workload=commerce-global. Account ID: 123456789012.
