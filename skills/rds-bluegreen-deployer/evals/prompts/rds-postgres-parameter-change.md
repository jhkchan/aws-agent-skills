# Eval: rds-postgres-parameter-change

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — RDS PostgreSQL Blue/Green, parameter group change (shared_buffers, work_mem) in green, same engine version, green validation

## Prompt

Create an RDS Blue/Green Deployment for my RDS PostgreSQL
instance prod-pg-db (postgres 14.10) in us-east-1, account
123456789012. I want to apply a new parameter group prod-pg14-tuned
in the green environment with changed shared_buffers and work_mem.
Same engine version (14.10). My app has connection retry logic.
Tags: Environment=production, Change=parameter-group.
