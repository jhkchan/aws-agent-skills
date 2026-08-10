# Eval: static-param-reboot-warning

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — postgres16 family, static params flagged for reboot, analytics tuning (high work_mem)

## Prompt

Provision an RDS DB parameter group for PostgreSQL 16 in
us-east-1. Name: analytics-pg16-params. Family: postgres16.
Parameters: shared_buffers={DBInstanceClassMemory/4},
max_connections=100, work_mem=64MB (immediate),
maintenance_work_mem=1GB (immediate),
effective_cache_size={DBInstanceClassMemory*3/4} (immediate),
random_page_cost=1.1 (immediate). Associate with DB instance
analytics-db-pg16. This is a read-heavy analytics workload.
Tags: Environment=production, Application=analytics.
