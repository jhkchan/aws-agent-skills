# End-to-End Example: DocumentDB Cluster Deployment

A walkthrough showing how to use the `documentdb-cluster-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production DocumentDB cluster for an orders
service with multi-AZ replication, change streams for CDC, KMS
encryption, and storage autoscaling. The cluster needs:

- Cluster name: orders-docdb
- Engine version: 5.0.0 (MongoDB 5.0 compatibility)
- Instance class: db.r5.large (1 primary + 2 replicas)
- Multi-AZ: 3 AZs (us-east-1a, us-east-1b, us-east-1c)
- Change streams: enabled, 2-day retention (172800 seconds)
- KMS key: arn:aws:kms:us-east-1:123456789012:key/abc123
- Backup retention: 7 days
- Storage autoscaling ceiling: 10 TB
- Subnet group: docdb-subnet-group
- Security group: sg-docdb-001 (port 27017 from 10.0.0.0/16)
- Indexes: compound {status, created_at} + single {email}

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-documentdb-cluster
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a DocumentDB cluster named orders-docdb in us-east-1.
      Engine 5.0, r5.large with 1 primary and 2 replicas. Enable
      change streams with 2-day retention. KMS key
      arn:aws:kms:us-east-1:123456789012:key/abc123. Backup 7 days.
      Storage ceiling 10 TB. Indexes on status+created_at and email."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a documentdb cluster"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DOCUMENTDB_CLUSTER: orders-docdb (5.0.0)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Cluster identifier: orders-docdb
  [✓] Engine version: 5.0.0 (MongoDB 5.0 compatibility)
  [✓] Instance class: db.r5.large — production
  [✓] Instance count: 1 primary + 2 replicas (multi-AZ: yes)
  [✓] Subnet group: docdb-subnet-group (spans 3 AZs)
  [✓] Security group: sg-docdb-001 (port 27017 from 10.0.0.0/16)
  [✓] Parameter group: docdb-prod-params (change_streams: enabled, retention: 2 days)
  [✓] KMS encryption: customer-managed (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Backup retention: 7 days (PITR: enabled)
  [✓] Storage autoscaling ceiling: 10 TB (headroom: 50%)
  [✓] Change streams: enabled (retention: 2 days)
  [✓] Indexing strategy: compound {status, created_at} + single {email}
  [✓] Global cluster: none
  [✓] TLS: enabled (production default)
  [✓] Deletion protection: enabled
  [✓] Tags: Environment=production, Application=orders
VERIFICATION_COMMANDS:
  aws docdb describe-db-clusters --db-cluster-identifier orders-docdb --region us-east-1
  aws docdb describe-db-instances --query 'DBInstances[?DBClusterIdentifier==`orders-docdb`]' --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/DocDB --metric-name DatabaseCpuUtilization --dimensions Name=DBClusterIdentifier,Value=orders-docdb --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the cluster parameter group (with change streams)
aws docdb create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name docdb-prod-params \
  --db-parameter-group-family docdb5.0 \
  --description "Production DocumentDB parameters" \
  --region us-east-1

aws docdb modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name docdb-prod-params \
  --parameters \
    ParameterName=change_streams_log_retention_duration,ParameterValue=172800,ApplyMethod=immediate \
    ParameterName=audit_logs,ParameterValue=enabled,ApplyMethod=immediate \
  --region us-east-1

# Step 2: Create the cluster
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb \
  --engine docdb \
  --engine-version 5.0.0 \
  --master-username admin \
  --master-user-password 'UseAStrongPassword123!' \
  --db-subnet-group-name docdb-subnet-group \
  --vpc-security-group-ids sg-docdb-001 \
  --db-cluster-parameter-group-name docdb-prod-params \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --deletion-protection \
  --region us-east-1

# Step 3: Create the primary instance
aws docdb create-db-instance \
  --db-instance-identifier orders-docdb-primary \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier orders-docdb \
  --region us-east-1

# Step 4: Create replica instances in different AZs
aws docdb create-db-instance \
  --db-instance-identifier orders-docdb-replica-1 \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier orders-docdb \
  --preferred-availability-zone us-east-1b \
  --promotion-tier 0 \
  --region us-east-1

aws docdb create-db-instance \
  --db-instance-identifier orders-docdb-replica-2 \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier orders-docdb \
  --preferred-availability-zone us-east-1c \
  --promotion-tier 1 \
  --region us-east-1
```

---

## Step 4 — Create indexes via mongo shell

```bash
# Download CA bundle
wget https://s3.amazonaws.com/rds-downloads/rds-combined-ca-bundle.pem

# Connect to the cluster
mongo "mongodb://admin:password@orders-docdb.cluster-abc.us-east-1.docdb.amazonaws.com:27017/?tls=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false" \
  --tlsCAFile rds-combined-ca-bundle.pem
```

```javascript
// Create indexes BEFORE deploying application queries
db.orders.createIndex({ status: 1, created_at: -1 })
db.users.createIndex({ email: 1 })

// Verify indexes
db.orders.getIndexes()
db.users.getIndexes()
```

---

## Step 5 — Post-deployment verification

```bash
# Cluster status — should be available
aws docdb describe-db-clusters \
  --db-cluster-identifier orders-docdb \
  --query 'DBClusters[0].Status' --region us-east-1

# Instance status — all should be available
aws docdb describe-db-instances \
  --query 'DBInstances[?DBClusterIdentifier==`orders-docdb`].{ID:DBInstanceIdentifier,Class:DBInstanceClass,Status:DBInstanceStatus,AZ:AvailabilityZone}' \
  --region us-east-1 --output table

# Change streams parameter — should be 172800
aws docdb describe-db-cluster-parameters \
  --db-cluster-parameter-group-name docdb-prod-params \
  --query 'Parameters[?ParameterName==`change_streams_log_retention_duration`].ParameterValue' \
  --region us-east-1

# CloudWatch: CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/DocDB \
  --metric-name DatabaseCpuUtilization \
  --dimensions Name=DBClusterIdentifier,Value=orders-docdb \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Change streams | Assumes automatic | Parameter group with change_streams_log_retention_duration + reboot | Change streams are disabled by default; must be explicitly enabled |
| Indexes | Created after deployment | Created BEFORE queries deployed | DocumentDB has no query optimizer; unindexed queries are full scans |
| Storage ceiling | Not set | 10 TB ceiling with 50% headroom | Hitting ceiling = STORAGE_FULL, all writes rejected |
| t3 vs r5 | May use t3 for cost | r5 for production, t3 for dev only | T3 is burstable; CPU credits deplete under sustained load |
| TLS | May forget CA bundle | TLS enabled, CA bundle path noted | TLS is required; connection fails without CA bundle |
| retryWrites | May leave default | retryWrites=false in connection string | DocumentDB does not support retryable writes |

---

## Related artifacts

- **Skill definition:** `skills/documentdb-cluster-deployer/SKILL.md`
- **Storage and change streams guide:** `skills/documentdb-cluster-deployer/references/storage-and-changestreams.md`
- **Global clusters and indexing guide:** `skills/documentdb-cluster-deployer/references/global-clusters-and-indexing.md`
- **Slash command:** `commands/aws/deploy-documentdb-cluster.md`
- **Eval suite:** `skills/documentdb-cluster-deployer/evals/evals.json`
- **Legacy test cases:** `skills/documentdb-cluster-deployer/eval/test-cases.yaml`
