---
description: Provision an RDS or Aurora database with production-grade defaults (KMS encryption, Multi-AZ, Performance Insights, parameter group, deletion protection). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create rds instance"
  - "provision rds"
  - "deploy rds"
  - "create aurora cluster"
  - "provision aurora"
  - "deploy aurora"
  - "multi-az database"
  - "rds production setup"
  - "aurora serverless v2"
  - "aurora serverless"
  - "aurora global database"
  - "performance insights"
  - "enhanced monitoring"
  - "parameter group tuning"
  - "rds encryption"
  - "backtrack mysql"
  - "blue green deployment"
  - "aurora ltes"
  - "aurora dsql"
  - "rds custom"
  - "harden rds instance"
routes_to: rds-instance-deployer
---

# /aws:deploy-rds-instance

Activate the `rds-instance-deployer` skill and provision an RDS or Aurora
database with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Engine + instance class selection (burstable / general-purpose / memory-optimized)
2. Network: DB subnet group + security group (scoped to app SG on engine port)
3. Encryption (KMS, immutable — must decide at creation)
4. Multi-AZ (HA with synchronous standby; Aurora cluster spans AZs)
5. Automated backups + PITR (1-35 day retention)
6. Enhanced Monitoring + Performance Insights (both, not either/or)
7. Parameter group + Option group (engine tuning + engine-specific features)
8. Aurora-specific: Serverless v2, Global Database, Backtrack
9. Deletion protection + tags
10. Latest: Blue/Green, Aurora LTES, Aurora DSQL

## When to use

- You need to create a new RDS instance or Aurora cluster with production
  defaults.
- You are sizing an instance class for a workload.
- You need to plan Multi-AZ, Aurora Serverless v2, or Aurora Global Database.
- You want to validate that a configuration meets production baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-rds-instance
```

Then provide: instance/cluster name, engine + version, instance class,
Multi-AZ preference, encryption key alias, retention policy, parameter
group requirements, and any optional Aurora features (Serverless v2,
Global Database, Backtrack).

### Natural language

Any of these routes to the same skill:

- "create a production Aurora PostgreSQL cluster"
- "provision an RDS MySQL Multi-AZ instance"
- "set up Aurora Serverless v2 for a bursty workload"
- "harden my RDS instance for production"
- "configure Aurora Global Database for DR"

### CLI routing

```bash
node cli/bin/cli.js route "create an rds instance"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
orchestrator routes to it when the user wants to create or harden RDS/Aurora
databases. The output checklist feeds into verification pipelines and audit
skills (rds-instance-auditor for post-deployment audit).

## Example

```
You: /aws:deploy-rds-instance

     Provision an Aurora PostgreSQL production cluster "prod-orders-pg"
     in us-east-1. Engine aurora-postgresql 16.3, db.r7g.large. Customer
     CMK alias/prod-rds-key. Writer + 2 readers across us-east-1a/b/c.
     14-day backups, Enhanced Monitoring 30s, Performance Insights on.
     Force SSL via parameter group, add pgaudit option. Deletion protection.
     DB subnet group prod-db-subnet-group. App SG sg-prod-app on 5432.
     Master credentials in Secrets Manager. Account: 123456789012.

Skill:
  CLUSTER: prod-orders-pg
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Engine: aurora-postgresql 16.3
    [✓] Instance class: db.r7g.large (Graviton, memory-optimized)
    [✓] DB subnet group: prod-db-subnet-group (3 AZs)
    [✓] Security group: sg-prod-app inbound on 5432; rds.force_ssl=1
    [✓] Encryption: KMS customer CMK (alias/prod-rds-key) at creation
    [✓] Multi-AZ: Aurora cluster spanning 3 AZs (1 writer + 2 readers)
    [✓] Backups: 14-day retention
    [✓] Enhanced Monitoring: 30-second interval
    [✓] Performance Insights: Enabled
    [✓] Parameter group: force_ssl, shared_buffers, log_statement=ddl
    [✓] Option group: pgaudit
    [✓] Deletion protection: Enabled
    [✓] Master credentials: Secrets Manager
  VERIFICATION_COMMANDS:
    aws rds describe-db-clusters --db-cluster-identifier prod-orders-pg
    aws kms describe-key --key-id alias/prod-rds-key
    aws ec2 describe-security-groups --group-ids sg-prod-db
```

## References

- Skill definition: `skills/rds-instance-deployer/SKILL.md`
- Instance classes and parameter tuning: `skills/rds-instance-deployer/references/instance-classes-and-parameter-tuning.md`
- Provisioning CLI commands: `skills/rds-instance-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/rds-instance-deployer/evals/evals.json`
