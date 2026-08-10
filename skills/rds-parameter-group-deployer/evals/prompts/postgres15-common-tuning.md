# Eval: postgres15-common-tuning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — postgres15 family, static shared_buffers/max_connections (pending reboot), dynamic work_mem/wal_buffers/checkpoint_completion_target (immediate)

## Prompt

Provision an RDS DB parameter group for PostgreSQL 15 in
us-east-1. Name: payments-pg15-params. Family: postgres15.
Parameters: max_connections=200 (pending-reboot),
shared_buffers={DBInstanceClassMemory/4} (pending-reboot),
work_mem=8MB (immediate),
wal_buffers=16MB (immediate),
checkpoint_completion_target=0.9 (immediate),
effective_cache_size={DBInstanceClassMemory*3/4} (immediate),
random_page_cost=1.1 (immediate),
log_min_duration_statement=1000 (immediate). Associate with
DB instance payments-db-pg15. Tags: Environment=production,
Application=payments.
