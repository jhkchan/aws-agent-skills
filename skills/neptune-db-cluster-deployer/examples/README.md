# End-to-End Example: Neptune DB Cluster Deployment

A walkthrough showing how to use the `neptune-db-cluster-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production Neptune DB graph database cluster
for a Gremlin property-graph workload. The cluster needs:

- Service: Neptune DB (NOT Analytics — transactional OLTP workload)
- Engine version: 1.3.2.0 (pinned)
- Topology: 1 writer + 2 readers across 3 AZs (Multi-AZ failover)
- Instance class: db.r6g.8xlarge
- Encryption at rest: customer-managed CMK (alias/prod-graph-kms)
- TLS: neptune_enforce_ssl=1
- IAM database auth: enabled
- neptune_query_timeout=30000 (OLTP)
- Neptune Streams: enabled (CDC)
- Snapshot retention: 7 days
- Deletion protection: enabled

Cluster name: `prod-graph`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-neptune-db-cluster
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production Neptune DB cluster named prod-graph in
      us-east-1. Gremlin property-graph workload, ~200M vertices +
      1B edges. 1 writer + 2 readers across 3 AZs for Multi-AZ.
      db.r6g.8xlarge. Engine 1.3.2.0. Customer CMK alias/prod-graph-kms.
      neptune_enforce_ssl=1, IAM database auth, neptune_query_timeout=30000,
      Streams enabled. Snapshots 7 days. Deletion protection.
      Subnet group prod-neptune-subnet. Security group sg-neptune123
      inbound 8182 from sg-app456. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a neptune db cluster"
```

Output:

```
[Phase: Deploy | Skills routed: neptune-db-cluster-deployer]

Primary route: neptune-db-cluster-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
NEPTUNE: prod-graph
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service: Neptune DB (NOT Analytics)
  [✓] Engine version: 1.3.2.0 (pinned)
  [✓] Writer instance: db.r6g.8xlarge
  [✓] Reader instances: 2 (across us-east-1b, us-east-1c for Multi-AZ)
  [✓] Multi-AZ with reader promotion: Enabled
  [✓] Subnet group: prod-neptune-subnet (3 AZs)
  [✓] Security group: sg-neptune123 (inbound 8182 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-graph-kms)
  [✓] TLS / neptune_enforce_ssl: Enabled
  [✓] IAM database auth: Enabled
  [✓] Parameter group: prod-neptune-pg (neptune_query_timeout=30000, neptune_streams=1)
  [✓] Snapshot retention: 7 days
  [✓] Deletion protection: Enabled
  [✓] Query languages: Gremlin
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier prod-graph
  aws neptune describe-db-instances --db-instance-identifier prod-graph-instance-1
  aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name prod-neptune-pg
  aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc
  aws kms describe-key --key-id alias/prod-graph-kms
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the subnet group (must span >=2 AZs for Multi-AZ)
aws neptune create-db-subnet-group \
  --db-subnet-group-name prod-neptune-subnet \
  --db-subnet-group-description "Multi-AZ subnet group for prod Neptune" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc

# Step 2: Create the cluster parameter group
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --db-parameter-group-family neptune1 \
  --description "Production Neptune cluster parameter group"

aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=immediate \
    ParameterName=neptune_query_timeout,ParameterValue=30000,ApplyMethod=immediate \
    ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot

# Step 3: Create the DB cluster — encryption immutable at creation
aws neptune create-db-cluster \
  --db-cluster-identifier prod-graph \
  --engine neptune \
  --engine-version 1.3.2.0 \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --db-subnet-group-name prod-neptune-subnet \
  --vpc-security-group-ids sg-neptune123 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-graph-kms \
  --enable-iam-database-authentication \
  --backup-retention-period 7 \
  --deletion-protection \
  --tags Key=Environment,Value=production Key=Workload,Value=graph

# Step 4: Create writer + reader instances across 3 AZs
aws neptune create-db-instance \
  --db-instance-identifier prod-graph-instance-1 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier prod-graph \
  --availability-zone us-east-1a

aws neptune create-db-instance \
  --db-instance-identifier prod-graph-instance-2 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier prod-graph \
  --availability-zone us-east-1b

aws neptune create-db-instance \
  --db-instance-identifier prod-graph-instance-3 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier prod-graph \
  --availability-zone us-east-1c

# Step 5: Wait for available
aws neptune wait db-instance-available --db-instance-identifier prod-graph-instance-1

# Step 6: Bulk load initial data from S3 (same region)
curl -X POST \
  -H 'Content-Type: application/json' \
  https://prod-graph.cluster-xxxxxxxxxxxx.us-east-1.neptune.amazonaws.com:8182/loader \
  -d '{
    "source": "s3://prod-graph-bucket/initial-load/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::123456789012:role/NeptuneLoadRole",
    "mode": "NEW",
    "region": "us-east-1",
    "failOnError": "TRUE",
    "parallelism": "MEDIUM"
  }'
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Cluster — Status, MultiAZ, StorageEncrypted, KmsKeyId,
# BackupRetentionPeriod, DeletionProtection, IamDatabaseAuthEnabled
aws neptune describe-db-clusters --db-cluster-identifier prod-graph

# Instance — DBInstanceClass, DBInstanceStatus, AvailabilityZone
aws neptune describe-db-instances --db-instance-identifier prod-graph-instance-1

# Parameter group — neptune_enforce_ssl, neptune_query_timeout, neptune_streams
aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name prod-neptune-pg

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/prod-graph-kms
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Service boundary | Provisions Neptune DB for PageRank | Redirects to Neptune Analytics | Neptune DB has no built-in algorithm library. Neptune Analytics is a separate service for OLAP workloads. |
| Encryption immutability | "Enable encryption later" | `--storage-encrypted` + `--kms-key-id` at creation | A non-encrypted Neptune cluster CANNOT be encrypted without snapshot/restore. |
| TLS at creation | Skips neptune_enforce_ssl | `neptune_enforce_ssl=1` in parameter group at creation | Enabling on an existing cluster requires a rolling reboot that drops plaintext clients. |
| Single-writer bottleneck | Adds readers to scale writes | Scales UP writer instance class | Neptune has exactly one writer per cluster. Readers scale reads only. |
| Multi-AZ subnet group | Forgets to verify | Confirms subnet group spans >=2 AZs | Multi-AZ cannot place the reader in a different AZ without a multi-AZ subnet group. |
| Memory budgeting | Quotes spec-sheet memory | 60% buffer cache rule | Neptune needs ~40% overhead for OS, JVM, connection state, copy-on-write. |
| Bulk load via per-vertex Gremlin | Loops `g.addV()` calls | Uses Neptune Loader (10-100x faster) | Per-vertex inserts are for incremental app writes only, not bulk ingest. |
| S3 same-region | Forgets | Confirms bucket is in same region | Cross-region S3 fails silently or with a generic permissions error. |

---

## Related artifacts

- **Skill definition:** `skills/neptune-db-cluster-deployer/SKILL.md`
- **Instance and topology guide:** `skills/neptune-db-cluster-deployer/references/instance-and-topology.md`
- **Provisioning CLI commands:** `skills/neptune-db-cluster-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-neptune-db-cluster.md`
- **Eval suite:** `skills/neptune-db-cluster-deployer/evals/evals.json`
- **Legacy test cases:** `skills/neptune-db-cluster-deployer/eval/test-cases.yaml`
