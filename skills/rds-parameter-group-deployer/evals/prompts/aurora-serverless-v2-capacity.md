# Eval: aurora-serverless-v2-capacity

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aurora-postgresql15 cluster parameter group, formula-based memory values, capacity configuration

## Prompt

Provision an Aurora DB cluster parameter group for
PostgreSQL 15 Serverless v2 in us-east-1. Name:
slsv2-pg15-params. Family: aurora-postgresql15. Parameters:
shared_buffers={DBInstanceClassMemory/4} (pending-reboot),
work_mem=4MB (immediate),
effective_cache_size={DBInstanceClassMemory*3/4} (immediate),
max_connections={LEAST({DBInstanceClassMemory/9531392},5000)}
(pending-reboot),
autovacuum_naptime=30s (immediate). Cluster scaling:
MinCapacity=2, MaxCapacity=16. Associate with Aurora cluster
slsv2-cluster. Tags: Environment=production,
Application=serverless.
