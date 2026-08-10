---
description: Provision an AWS RDS DB parameter group or DB cluster parameter group with production-grade configuration (correct family — postgres15, mysql8.0, aurora-postgresql15, etc.; static vs dynamic parameter classification — static requires DB instance reboot; ApplyMethod — immediate vs pending-reboot; PostgreSQL tuning — max_connections, shared_buffers, work_mem, wal_buffers, checkpoint_completion_target, effective_cache_size; MySQL tuning — innodb_buffer_pool_size, max_connections, slow_query_log; Aurora-specific parameters; Aurora Serverless v2 capacity parameters; parameter group association with DB instances and clusters). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create rds parameter group"
  - "provision parameter group"
  - "db parameter group"
  - "db parameter group family"
  - "postgres parameter group"
  - "mysql parameter group"
  - "aurora parameter group"
  - "aurora cluster parameter group"
  - "static vs dynamic parameters"
  - "apply method immediate"
  - "pending reboot"
  - "shared_buffers"
  - "work_mem"
  - "max_connections rds"
  - "innodb_buffer_pool_size"
  - "slow_query_log"
  - "aurora serverless v2"
  - "rds parameter tuning"
routes_to: rds-parameter-group-deployer
---

# /aws:deploy-rds-parameter-group

Activate the `rds-parameter-group-deployer` skill and provision an
AWS RDS DB parameter group or DB cluster parameter group with
production-grade configuration.

## What it does

The skill walks a 9-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Family selection (postgres15, mysql8.0, aurora-postgresql15, etc.)
2. DBParameterGroup vs DBClusterParameterGroup type
3. Static vs dynamic parameter classification
4. ApplyMethod (immediate vs pending-reboot)
5. PostgreSQL tuning parameters
6. MySQL tuning parameters
7. Aurora-specific parameters
8. Aurora Serverless v2 capacity configuration
9. Create + associate + apply (with reboot planning)

## When to use

- You need to create a new DB parameter group with production tuning.
- You are tuning PostgreSQL parameters (shared_buffers, work_mem,
  max_connections, checkpoint_completion_target).
- You are tuning MySQL parameters (innodb_buffer_pool_size,
  slow_query_log, long_query_time).
- You need to configure Aurora cluster parameters.
- You are setting up Aurora Serverless v2 capacity.
- You want to check for provisioning blockers (wrong family, missing
  DB engine version, static params requiring reboot).

## How to invoke

### Slash command

```
/aws:deploy-rds-parameter-group
```

Then provide: parameter group name, family (or DB engine version to
derive it), parameter list with values and ApplyMethod, DB instance
or cluster identifier for association, and tags.

### Natural language

Any of these routes to the same skill:

- "create a PostgreSQL parameter group for production"
- "tune MySQL innodb_buffer_pool_size"
- "set up Aurora Serverless v2 parameter group"
- "configure slow query logging on RDS"
- "change max_connections on my DB instance"

### CLI routing

```bash
node cli/bin/cli.js route "deploy rds parameter group"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit
skills (e.g., an RDS parameter group auditor for post-provisioning
checks).

## Example

```
You: /aws:deploy-rds-parameter-group

     Provision a PostgreSQL 15 parameter group for the payments DB.
     Name: payments-pg15-params. Set max_connections=200,
     shared_buffers={DBInstanceClassMemory/4}, work_mem=8MB,
     wal_buffers=16MB, checkpoint_completion_target=0.9,
     effective_cache_size={DBInstanceClassMemory*3/4},
     random_page_cost=1.1, log_min_duration_statement=1000.
     Associate with payments-db-pg15.

Skill:
  GROUP: payments-pg15-params
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Family — postgres15
    [✓]      Type — DBParameterGroup
    [✓]      max_connections — 200 (static, PENDING REBOOT required)
    [✓]      shared_buffers — {DBInstanceClassMemory/4} (static, PENDING REBOOT required)
    [✓]      work_mem — 8MB (dynamic, immediate)
    [✓]      wal_buffers — 16MB (dynamic, immediate)
    [✓]      checkpoint_completion_target — 0.9 (dynamic, immediate)
    [✓]      effective_cache_size — {DBInstanceClassMemory*3/4} (dynamic, immediate)
    [✓]      random_page_cost — 1.1 (dynamic, immediate)
    [✓]      log_min_duration_statement — 1000 (dynamic, immediate)
    [✓]      Association — DB instance payments-db-pg15
    [✓]      Reboot required — YES (static params: max_connections, shared_buffers)
    [✓]      Tags — Environment=production, Application=payments
  VERIFICATION_COMMANDS:
    aws rds describe-db-parameters --db-parameter-group-name payments-pg15-params
    aws rds describe-db-instances --db-instance-identifier payments-db-pg15
    aws rds describe-pending-maintenance-actions --db-instance-identifier payments-db-pg15
```

## References

- Skill definition: `skills/rds-parameter-group-deployer/SKILL.md`
- Deployment CLI commands: `skills/rds-parameter-group-deployer/references/deployment-cli-commands.md`
- Database tuning guide: `skills/rds-parameter-group-deployer/references/database-tuning-guide.md`
- Eval suite: `skills/rds-parameter-group-deployer/evals/evals.json`
