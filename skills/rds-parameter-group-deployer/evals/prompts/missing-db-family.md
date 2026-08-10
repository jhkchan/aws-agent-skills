# Eval: missing-db-family

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — parameter group family required and immutable, engine version not specified

## Prompt

Provision an RDS DB parameter group in us-east-1. Name:
app-pg-params. Parameters: max_connections=100,
shared_buffers={DBInstanceClassMemory/4}, work_mem=8MB.
I'm not sure which family to use — the DB instance is running
either PostgreSQL or MySQL, I don't remember the version.
