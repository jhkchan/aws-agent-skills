---
description: Deploy an Amazon RDS Blue/Green Deployment for zero-downtime database upgrades (major version upgrades, parameter group changes, schema changes in green, switchover with ~1-minute downtime via DNS update, green validation, green cleanup). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create blue green deployment"
  - "deploy blue green"
  - "rds blue green"
  - "blue green switchover"
  - "zero downtime database upgrade"
  - "aurora blue green"
  - "rds major version upgrade green"
  - "green environment validation"
  - "switch over blue green"
  - "blue green deployment"
routes_to: rds-bluegreen-deployer
---

# /aws:deploy-rds-bluegreen

Activate the `rds-bluegreen-deployer` skill and deploy an Amazon RDS
Blue/Green Deployment with production-grade defaults.

## What it does

The skill walks the deployment procedure and emits a READY_TO_DEPLOY
checklist:

1. Blue/Green model (source to staging clone)
2. Engine and version support (Aurora MySQL/PostgreSQL, RDS MySQL/PostgreSQL)
3. Create the Blue/Green Deployment (create-blue-green-deployment)
4. Database changes in green (major version upgrade, parameter, schema)
5. Green environment validation (engine version, replication lag, schema, performance)
6. Switchover (1-minute downtime via DNS CNAME swap)
7. Switchover timeout configuration
8. Application connection string update (CNAME auto-follow)
9. Delete green after successful switch (stop 2x billing)
10. Blue/Green limitations (engine constraints, storage, topology)
11. Monitoring during green validation (CloudWatch metrics)

## When to use

- You need to perform a zero-downtime major version upgrade.
- You need to apply parameter group changes without downtime.
- You need to apply schema changes (DDL) in a staging environment first.
- You need to switch over a Blue/Green Deployment.
- You need to validate the green environment before switchover.
- You need to delete a green environment after successful switchover.

## When NOT to use

- **Standard RDS modifications** without Blue/Green — use
  `modify-db-instance` directly for non-disruptive changes.
- **RDS Custom** — does NOT support Blue/Green.
- **Unsupported engines** (SQL Server, Oracle, MariaDB, Db2) — use
  standard maintenance window upgrades.
- **Aurora Global Database failover** — different mechanism.
- **Multi-AZ failover** — automatic failover, not Blue/Green.

## How to invoke

### Slash command

```
/aws:deploy-rds-bluegreen
```

Then provide: source DB identifier, target engine version, target
parameter group name, switchover timeout, application retry logic
status, tags.

### Natural language

Any of these routes to the same skill:

- "create a blue green deployment for my Aurora MySQL cluster"
- "upgrade my RDS PostgreSQL from 13 to 15 with zero downtime"
- "switch over my blue green deployment"
- "validate the green environment before switchover"
- "apply a schema change in green before switching"

### CLI routing

```bash
node cli/bin/cli.js route "create rds blue green deployment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Blue/Green
Deployments or perform zero-downtime database upgrades. The output
checklist feeds into verification pipelines and downstream audit
skills.

## Example

```
You: /aws:deploy-rds-bluegreen

     Create a Blue/Green Deployment for my Aurora MySQL cluster
     prod-mysql-db (5.7) to upgrade to 8.0 in green. Use
     parameter group prod-mysql80-params. Region us-east-1.

Skill:
  BLUE_GREEN: prod-mysql-db → green-prod-mysql-db
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Major version upgrade: 5.7 → 8.0 (in green)
    [✓] Parameter group: prod-mysql80-params (applied to green)
    [✓] Green validation: PASSED
    [✓] Replication (blue → green): ACTIVE, lag < 1s
    [✓] Switchover timeout: 300 seconds
    [✓] Endpoint strategy: CNAME auto-follow (no app change needed)
  VERIFICATION_COMMANDS:
    aws rds describe-blue-green-deployments --blue-green-deployment-identifier <bg-id> --region us-east-1
    aws rds describe-db-instances --db-instance-identifier <green-db-id> --region us-east-1
```

## References

- Skill definition: `skills/rds-bluegreen-deployer/SKILL.md`
- Switchover and DNS guide: `skills/rds-bluegreen-deployer/references/switchover-and-dns.md`
- Green validation and changes guide: `skills/rds-bluegreen-deployer/references/green-validation-and-changes.md`
- Eval suite: `skills/rds-bluegreen-deployer/evals/evals.json`
