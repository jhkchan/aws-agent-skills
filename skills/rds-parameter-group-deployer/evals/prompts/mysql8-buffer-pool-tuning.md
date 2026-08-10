# Eval: mysql8-buffer-pool-tuning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — mysql8.0 family, innodb_buffer_pool_size (dynamic), max_connections (static), slow_query_log (dynamic)

## Prompt

Provision an RDS DB parameter group for MySQL 8.0 in
us-east-1. Name: orders-mysql8-params. Family: mysql8.0.
Parameters: innodb_buffer_pool_size={DBInstanceClassMemory*3/4}
(immediate), max_connections=300 (pending-reboot),
slow_query_log=1 (immediate), long_query_time=1 (immediate),
innodb_flush_log_at_trx_commit=1 (immediate),
character_set_server=utf8mb4 (pending-reboot). Associate
with DB instance orders-db-mysql8. Tags: Environment=production,
Application=orders.
