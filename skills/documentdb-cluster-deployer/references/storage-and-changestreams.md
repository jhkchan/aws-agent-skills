# Storage Autoscaling and Change Streams — DocumentDB Cluster Deployer

Deep reference on DocumentDB storage autoscaling (auto-growth mechanics,
ceiling configuration, STORAGE_FULL prevention) and change streams
(retention configuration, CDC pipeline patterns, resume tokens). Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Storage autoscaling fundamentals

### How DocumentDB storage works

DocumentDB separates compute (instances) from storage (cluster volume).
The cluster volume is a shared, auto-expanding storage layer:

```text
Cluster volume lifecycle:
  1. Created at 10 GB (minimum) when the cluster is created.
  2. Auto-grows as data is inserted (no manual provisioning needed).
  3. Growth is in 10 GB increments.
  4. Bills per GB-month for allocated storage (not just used storage).

  Maximum: up to 64 TB (configurable ceiling per cluster).
```

### The autoscaling ceiling problem

DocumentDB auto-grows storage, but there is a ceiling. When storage hits
the ceiling, the cluster enters `STORAGE_FULL` state:

```text
STORAGE_FULL consequences:
  → ALL write operations rejected (INSERT, UPDATE, DELETE fail)
  → Read operations may continue (but writes are blocked)
  → Application errors: "WriteError: storage is full"
  → No automatic resolution — requires manual intervention

Resolution options:
  1. Increase the ceiling: modify-db-cluster with higher storage allocation
  2. Delete data to free space (requires writes — which are blocked!)
     → Must increase ceiling first, then delete data
  3. Snapshot + restore to a new cluster with higher ceiling (downtime)
```

### Setting and monitoring the ceiling

```bash
# Check current storage allocation
aws docdb describe-db-clusters \
  --db-cluster-identifier my-docdb-cluster \
  --query 'DBClusters[0].[StorageAllocated,DbClusterResourceId]' \
  --region us-east-1 --output table

# CloudWatch: monitor free storage space (bytes)
aws cloudwatch get-metric-statistics \
  --namespace AWS/DocDB \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBClusterIdentifier,Value=my-docdb-cluster \
  --start-time $(date -u -v-24H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 --statistics Average,Minimum \
  --region us-east-1

# CloudWatch alarm: alert when free storage < 20% of ceiling
aws cloudwatch put-metric-alarm \
  --alarm-name docdb-low-storage \
  --namespace AWS/DocDB \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBClusterIdentifier,Value=my-docdb-cluster \
  --threshold 2000000000000 \
  --comparison-operator LessThanThreshold \
  --period 300 --evaluation-periods 1 \
  --statistic Minimum \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:alerts \
  --region us-east-1
```

### Storage sizing expert rules

```text
Sizing methodology:
  1. Estimate current data size (run db.collection.stats())
  2. Project 12-month growth: current_size × monthly_growth_rate × 12
  3. Add 50% headroom: projected = projected_12mo × 1.5
  4. Set ceiling to nearest TB above projected value
  5. Monitor monthly; adjust ceiling if growth rate changes

  Expert thresholds:
    Free storage > 40% of ceiling: GREEN
    Free storage 20-40% of ceiling: YELLOW (plan ceiling increase)
    Free storage < 20% of ceiling: RED (increase ceiling immediately)
    Free storage = 0: STORAGE_FULL (writes blocked — emergency)
```

## Change streams for CDC

### Enabling change streams

Change streams are DISABLED by default. Enable via parameter group:

```bash
# Create parameter group (or modify existing)
aws docdb create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name cdc-params \
  --db-parameter-group-family docdb5.0 \
  --description "Change streams enabled" \
  --region us-east-1

# Set retention (1-3 days in seconds)
# 1 day = 86400, 2 days = 172800, 3 days = 259200
aws docdb modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name cdc-params \
  --parameters \
    ParameterName=change_streams_log_retention_duration,ParameterValue=172800,ApplyMethod=immediate \
  --region us-east-1

# Apply to cluster (requires reboot)
aws docdb modify-db-cluster \
  --db-cluster-identifier my-docdb-cluster \
  --db-cluster-parameter-group-name cdc-params \
  --apply-immediately \
  --region us-east-1

# Reboot the primary instance for parameter to take effect
aws docdb reboot-db-instance \
  --db-instance-identifier my-docdb-primary \
  --region us-east-1
```

### Change stream event structure

```json
{
  "_id": {
    "_data": "0263abc..."
  },
  "operationType": "insert",
  "clusterTime": {
    "$timestamp": "7111111111"
  },
  "fullDocument": {
    "_id": { "$oid": "64a1b2c3..." },
    "status": "pending",
    "amount": 1500.00
  },
  "ns": {
    "db": "orders",
    "coll": "transactions"
  },
  "documentKey": {
    "_id": { "$oid": "64a1b2c3..." }
  }
}
```

### Operation types

| operationType | Description |
|---|---|
| insert | New document inserted |
| update | Existing document modified |
| replace | Document replaced |
| delete | Document deleted (fullDocument not available) |
| invalidate | Collection/database dropped |

### Resume tokens and checkpointing

Change streams provide resume tokens for fault-tolerant processing:

```javascript
const { MongoClient } = require('mongodb');

const client = await MongoClient.connect(
  'mongodb://admin:password@cluster-endpoint:27017/?tls=true&replicaSet=rs0&retryWrites=false',
  { tlsCAFile: 'rds-combined-ca-bundle.pem' }
);

const collection = client.db('orders').collection('transactions');

// Option 1: Start from a specific timestamp
const stream = collection.watch([], {
  startAtOperationTime: Timestamp(7111111111, 1)
});

// Option 2: Resume from a saved token
const savedToken = loadTokenFromStore(); // your durable store
const stream = collection.watch([], {
  resumeAfter: savedToken
});

stream.on('change', (next) => {
  // Process the change event
  console.log('Operation:', next.operationType);
  console.log('Document:', next.fullDocument);

  // Save the resume token for crash recovery
  saveTokenToStore(next._id); // _id is the resume token
});

stream.on('error', (err) => {
  console.error('Stream error:', err);
  // Reconnect and resume from last saved token
});
```

### CDC pipeline architecture

```text
DocumentDB Change Stream → Application/Lambda → Downstream Systems

  DocumentDB Cluster
    ├── Change Stream (retention: 2 days)
    │     ├── Event: insert on transactions
    │     ├── Event: update on transactions
    │     └── Event: delete on transactions
    │
    └── Consumer Application (Lambda / ECS / EC2)
          ├── Read events via watch()
          ├── Process each event (transform, enrich)
          ├── Checkpoint resume token to DynamoDB/S3
          └── Write to downstream:
                ├── Elasticsearch (search index)
                ├── Redshift (analytics)
                ├── S3 (data lake)
                └── SNS/SQS (event notification)

  Expert rule:
    Always checkpoint resume tokens in a DURABLE store.
    On consumer restart, resume from the last checkpoint.
    The 2-day retention gives 48h of buffer for consumer recovery.
```

### Change streams vs DMS vs polling

| Approach | Latency | Overhead | Use case |
|---|---|---|---|
| Change streams | Near real-time (seconds) | Low (streaming) | Recommended for CDC |
| AWS DMS | Seconds to minutes | Medium (DMS infrastructure) | Migration, batch CDC |
| Polling | Minutes to hours | High (full scans) | Last resort — expensive and imprecise |

**Expert rule:** always prefer change streams. They are purpose-built,
ordered, resumable, and the lowest-overhead CDC mechanism for
DocumentDB.

## Terraform examples

```hcl
# Cluster parameter group with change streams
resource "aws_docdb_cluster_parameter_group" "prod" {
  family      = "docdb5.0"
  name        = "docdb-prod-params"
  description = "Production DocumentDB parameters"

  parameter {
    name         = "change_streams_log_retention_duration"
    value        = "172800"
    apply_method = "immediate"
  }

  parameter {
    name         = "audit_logs"
    value        = "enabled"
    apply_method = "immediate"
  }
}

# Cluster with KMS encryption and deletion protection
resource "aws_docdb_cluster" "main" {
  cluster_identifier              = "orders-docdb"
  engine                          = "docdb"
  engine_version                  = "5.0.0"
  master_username                 = "admin"
  master_password                 = var.docdb_password
  db_subnet_group_name            = aws_docdb_subnet_group.main.name
  vpc_security_group_ids          = [aws_security_group.docdb.id]
  db_cluster_parameter_group_name = aws_docdb_cluster_parameter_group.prod.name
  kms_key_id                      = aws_kms_key.docdb.arn
  storage_encrypted               = true
  backup_retention_period         = 7
  deletion_protection             = true
  preferred_backup_window         = "03:00-05:00"
  preferred_maintenance_window    = "sun:05:00-sun:07:00"

  tags = {
    Environment = "production"
    Application = "orders"
  }
}

# Primary instance
resource "aws_docdb_cluster_instance" "primary" {
  identifier              = "orders-docdb-primary"
  cluster_identifier      = aws_docdb_cluster.main.id
  instance_class          = "db.r5.large"
  promotion_tier          = 0
}

# Replicas in different AZs
resource "aws_docdb_cluster_instance" "replica_1" {
  identifier              = "orders-docdb-replica-1"
  cluster_identifier      = aws_docdb_cluster.main.id
  instance_class          = "db.r5.large"
  availability_zone       = "us-east-1b"
  promotion_tier          = 1
}

resource "aws_docdb_cluster_instance" "replica_2" {
  identifier              = "orders-docdb-replica-2"
  cluster_identifier      = aws_docdb_cluster.main.id
  instance_class          = "db.r5.large"
  availability_zone       = "us-east-1c"
  promotion_tier          = 2
}
```
## Expert heuristic: the storage autoscaling ceiling (moved from SKILL.md)


A baseline model says "storage auto-grows." The correct heuristic
recognizes that autoscaling has a ceiling, and hitting it stops writes.

```text
DocumentDB storage autoscaling:
  Cluster volume starts at 10 GB (minimum), auto-grows in 10 GB increments.
  Ceiling: configurable up to 64 TB.

  When storage hits the ceiling:
    → Cluster enters STORAGE_FULL state
    → ALL writes are rejected (inserts, updates, deletes fail)
    → Resolution: increase the ceiling (modify-db-cluster) or delete data

  Expert rule:
    Set ceiling = projected_growth_12_months × 1.5 (50% headroom)
    Alert when free storage < 20% of ceiling
```


## Expert heuristic: change streams for CDC (moved from SKILL.md)


Change streams provide ordered, resumable change events. They are the
recommended CDC mechanism for real-time data pipelines.

```text
Change stream flow:
  1. Enable change_streams_log_retention_duration (1-3 days) in parameter group
  2. Application opens a change stream via MongoDB driver:
     const stream = db.collection.watch([], { startAtOperationTime: timestamp })
  3. DocumentDB emits events: insert, update, delete, replace
  4. Application processes events and checkpoints resume token
  5. On restart, application resumes from last checkpoint token

  Expert rule:
    Enable change streams at CLUSTER CREATION (parameter group).
    Retention: 2 days (gives 48h of buffer for pipeline recovery).
    Always checkpoint resume tokens in a durable store.
```

**Resume-token invalidation gotcha:** the change stream resume token
encodes the cluster timestamp and log sequence number. If the change
stream log retention period expires (e.g., the consumer was offline
longer than `change_streams_log_retention_duration`), the token
becomes invalid — `resumeAfter` throws a `ChangeStreamHistoryLost`
error. The consumer must restart with `startAtOperationTime` set to
a timestamp within the current retention window. Expert rule: set
retention to 3 days (maximum) for critical CDC pipelines, and
checkpoint tokens to a durable store (DynamoDB, SQS) after each
batch, not in memory.


## Step 9 — Change streams for CDC (moved from SKILL.md)


Change streams must be enabled in the parameter group (see Step 6). Once
enabled, applications subscribe via the MongoDB driver.

```bash
# Enable change streams + reboot for parameter to take effect
aws docdb modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-param-group \
  --parameters \
    ParameterName=change_streams_log_retention_duration,ParameterValue=172800,ApplyMethod=immediate \
  --region us-east-1

aws docdb reboot-db-instance \
  --db-instance-identifier my-docdb-primary \
  --region us-east-1
```

```javascript
// Consume change streams (Node.js)
const { MongoClient } = require('mongodb');
const client = await MongoClient.connect(
  'mongodb://admin:password@cluster-endpoint:27017/?tls=true&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false',
  { tlsCAFile: 'rds-combined-ca-bundle.pem' }
);
const stream = client.db('mydb').collection('orders').watch();
stream.on('change', (next) => {
  console.log('Change event:', JSON.stringify(next));
  // Process and checkpoint resume token
});
```

