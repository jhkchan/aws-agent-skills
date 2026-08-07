# End-to-End Example: Aurora PostgreSQL Production Deployment

A walkthrough showing how to use the `rds-instance-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Aurora PostgreSQL production cluster for an OLTP
orders workload. The cluster needs:

- Aurora PostgreSQL 16.3, instance class db.r7g.large
- Customer-managed CMK encryption (alias/prod-rds-key)
- Cluster spanning 3 AZs: 1 writer + 2 readers (read-scaling + failover)
- 14-day backup retention (PITR coverage)
- Enhanced Monitoring (30s interval) + Performance Insights
- Custom parameter group: force SSL, shared_buffers tuned, log DDL
- pgaudit option for audit logging
- Deletion protection on the cluster
- Master credentials in AWS Secrets Manager

Cluster name: `prod-orders-pg`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rds-instance
```

Then paste the cluster requirements.

### Option B: Natural language

```
You: "Provision an Aurora PostgreSQL production cluster named prod-orders-pg
      in us-east-1. Engine aurora-postgresql 16.3, instance class db.r7g.large.
      Customer CMK alias/prod-rds-key. Writer + 2 readers across us-east-1a/b/c.
      14-day backups, Enhanced Monitoring 30s, Performance Insights on.
      Force SSL via parameter group, add pgaudit option. Deletion protection.
      DB subnet group prod-db-subnet-group. App SG sg-prod-app on 5432.
      Master credentials in Secrets Manager. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an aurora postgresql cluster"
```

Output:

```
[Phase: Deploy | Skills routed: rds-instance-deployer]

Primary route: rds-instance-deployer (score: 21)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CLUSTER: prod-orders-pg
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: aurora-postgresql 16.3
  [✓] Instance class: db.r7g.large (memory-optimized for buffer cache; Graviton for price/perf)
  [✓] DB subnet group: prod-db-subnet-group spanning 3 AZs (us-east-1a/b/c)
  [✓] Security group: inbound from sg-prod-app on port 5432; rds.force_ssl=1 (defense-in-depth)
  [✓] Encryption: KMS customer-managed CMK (alias/prod-rds-key) — enabled at creation (immutable)
  [✓] Multi-AZ: Aurora cluster spanning 3 AZs (1 writer + 2 readers as failover targets)
  [✓] Automated backups: 14-day retention (backup window: 03:00-04:00 UTC)
  [✓] Enhanced Monitoring: 30-second interval (role: rds-monitoring-role)
  [✓] Performance Insights: Enabled (retention: 7 days)
  [✓] Parameter group: prod-orders-pg-params (rds.force_ssl=1, shared_buffers={DBInstanceClassMemory/4}, log_statement=ddl)
  [✓] Option group: prod-orders-pg-options (pgaudit)
  [✓] Deletion protection: Enabled (on cluster)
  [✓] Master credentials: Secrets Manager (manage-master-user-password)
  [✓] Tags: Environment=production, Workload=orders
VERIFICATION_COMMANDS:
  aws rds describe-db-clusters --db-cluster-identifier prod-orders-pg
  aws rds describe-db-instances --db-instance-identifier prod-orders-pg-0
  aws kms describe-key --key-id alias/prod-rds-key
  aws ec2 describe-security-groups --group-ids sg-prod-db
  aws iam get-role --role-name rds-monitoring-role
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Custom cluster parameter group
aws rds create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-orders-pg-cluster-params \
  --db-parameter-group-family aurora-postgresql16 \
  --description "Cluster params for prod-orders-pg"

aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-orders-pg-cluster-params \
  --parameters "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate"

# Step 2: Option group with pgaudit
aws rds create-option-group \
  --option-group-name prod-orders-pg-options \
  --engine-name postgres \
  --major-engine-version 16 \
  --option-group-description "Options for prod-orders-pg"

aws rds modify-option-group \
  --option-group-name prod-orders-pg-options \
  --options "OptionName=pgaudit,OptionSettings=[{Name=pgaudit.log,Value=write,ddl}]"

# Step 3: Create the Aurora cluster (encryption at creation — immutable)
aws rds create-db-cluster \
  --db-cluster-identifier prod-orders-pg \
  --engine aurora-postgresql \
  --engine-version 16.3 \
  --master-username admin \
  --manage-master-user-password \
  --database-name orders \
  --vpc-security-group-ids sg-prod-db \
  --db-subnet-group-name prod-db-subnet-group \
  --db-cluster-parameter-group-name prod-orders-pg-cluster-params \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-rds-key \
  --backup-retention-period 14 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --enable-http-endpoint \
  --deletion-protection

# Step 4: Writer instance
aws rds create-db-instance \
  --db-instance-identifier prod-orders-pg-0 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-orders-pg \
  --availability-zone us-east-1a \
  --auto-minor-version-upgrade \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --monitoring-interval 30 \
  --monitoring-role-arn arn:aws:iam::123456789012:role/rds-monitoring-role

# Step 5: Reader instances (different AZs for failover targets)
aws rds create-db-instance \
  --db-instance-identifier prod-orders-pg-1 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-orders-pg \
  --availability-zone us-east-1b \
  --auto-minor-version-upgrade \
  --enable-performance-insights \
  --performance-insights-retention-period 7

aws rds create-db-instance \
  --db-instance-identifier prod-orders-pg-2 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-orders-pg \
  --availability-zone us-east-1c \
  --auto-minor-version-upgrade \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Cluster config — StorageEncrypted, DeletionProtection, BackupRetentionPeriod,
# DBClusterParameterGroup, AllocatedStorage, Engine, EngineVersion
aws rds describe-db-clusters --db-cluster-identifier prod-orders-pg

# Instance config — DBInstanceClass, DBSubnetGroup, VpcSecurityGroups,
# EnhancedMonitoringResponse, PerformanceInsightsEnabled
aws rds describe-db-instances --db-instance-identifier prod-orders-pg-0

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-rds-key

# Security group — inbound rules scoped to sg-prod-app on port 5432
aws ec2 describe-security-groups --group-ids sg-prod-db

# Enhanced Monitoring role
aws iam get-role --role-name rds-monitoring-role
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Encryption timing | "Enable in the console after" | Enabled at `create-db-cluster` | `StorageEncrypted` is immutable after creation. Post-creation encryption requires snapshot migration — multi-hour with app cutover. |
| Cluster vs instance scope | Sets encryption on instance | Sets encryption on cluster | For Aurora, encryption/deletion-protection/Multi-AZ are cluster properties. Setting them on instances produces false confidence. |
| Reader topology | Creates readers in same AZ | Distributes across 3 AZs | Readers in different AZs are failover targets; same-AZ readers don't survive an AZ failure. |
| Multi-AZ for Aurora | Confuses with non-Aurora standby | Notes Aurora cluster spans AZs implicitly | Aurora Multi-AZ is cluster-level; the standby-is-not-readable rule does not apply (Aurora readers ARE readable). |
| Parameter group | Uses default | Custom group with rds.force_ssl=1, shared_buffers tuned | Default parameter group is not editable; `shared_buffers={DBInstanceClassMemory/4}` auto-sizes to the instance class. |
| Master credentials | Hardcoded password | Secrets Manager (manage-master-user-password) | Hardcoded passwords in commands are an anti-pattern; Secrets Manager rotates them and integrates with IAM. |
| Force SSL | Forgotten | Enabled via parameter group (defense-in-depth) | Even if the SG is later loosened, the database rejects plaintext connections. |

---

## Related artifacts

- **Skill definition:** `skills/rds-instance-deployer/SKILL.md`
- **Instance classes and parameter tuning guide:** `skills/rds-instance-deployer/references/instance-classes-and-parameter-tuning.md`
- **Provisioning CLI commands:** `skills/rds-instance-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-rds-instance.md`
- **Eval suite:** `skills/rds-instance-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rds-instance-deployer/eval/test-cases.yaml`
