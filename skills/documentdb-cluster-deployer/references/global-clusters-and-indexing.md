# Global Clusters and Indexing — DocumentDB Cluster Deployer

Deep reference on DocumentDB global clusters (cross-region replication,
failover procedures, managed promotion) and indexing strategy (no query
optimizer, single vs compound vs text indexes, ESR rule, background
index builds). Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Global cluster fundamentals

### Architecture

A DocumentDB global cluster spans multiple AWS regions with one primary
region (read-write) and up to 5 secondary regions (read-only):

```text
Global Cluster: orders-global

  Primary Region: us-east-1
    └── Cluster: orders-docdb-primary
          ├── Primary instance (read-write)
          ├── Replica 1 (read-only)
          └── Replica 2 (read-only)
          │
          │ Replication (typically < 1 second)
          ▼
  Secondary Region: eu-west-1
    └── Cluster: orders-docdb-secondary
          ├── Instance 1 (read-only until promoted)
          └── Instance 2 (read-only until promoted)

  Key properties:
    1. Secondary clusters are READ-ONLY
    2. Replication is asynchronous (typically < 1 second lag)
    3. Failover is NOT automatic — must be scripted
    4. Data is encrypted in transit between regions
```

### Creating a global cluster

```bash
# Step 1: Create the global cluster (after the primary cluster exists)
aws docdb create-global-cluster \
  --global-cluster-identifier orders-global \
  --source-db-cluster-identifier arn:aws:rds:us-east-1:123456789012:cluster:orders-docdb-primary \
  --region us-east-1

# Step 2: Create the secondary cluster in another region
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb-secondary \
  --engine docdb \
  --engine-version 5.0.0 \
  --global-cluster-identifier orders-global \
  --master-username admin \
  --master-user-password 'UseAStrongPassword123!' \
  --db-subnet-group-name docdb-subnet-group-eu \
  --region eu-west-1

# Step 3: Add instances to the secondary cluster
aws docdb create-db-instance \
  --db-instance-identifier orders-docdb-eu-1 \
  --db-instance-class db.r5.2xlarge \
  --engine docdb \
  --db-cluster-identifier orders-docdb-secondary \
  --region eu-west-1
```

### Failover procedure

Global cluster failover is NOT automatic. The procedure is:

```text
Failover steps:
  1. Verify the primary region is truly down (not a transient issue)
  2. Wait for secondary replication to catch up (check replica lag)
  3. Remove the primary cluster from the global cluster:
     aws docdb delete-db-cluster \
       --db-cluster-identifier orders-docdb-primary \
       --final-db-snapshot-identifier orders-docdb-primary-final \
       --region us-east-1
     (If the primary region is down, this step may fail — skip to step 4)
  4. Promote the secondary cluster:
     aws docdb failover-db-cluster \
       --db-cluster-identifier orders-docdb-secondary \
       --region eu-west-1
  5. Update application connection strings to point to the new primary
  6. (Later) Set up a new secondary in another region for continued DR

  Expert rule:
    Script the failover with Lambda + EventBridge.
    Test failover quarterly (DR drill).
    Application must support connection-string updates (use Route 53 CNAME).
```

### Automated failover with EventBridge + Lambda

```python
import boto3

docdb = boto3.client('docdb', region_name='eu-west-1')
sns = boto3.client('sns')

def lambda_handler(event, context):
    # Triggered by EventBridge when primary health check fails
    try:
        # Promote the secondary cluster
        response = docdb.failover_db_cluster(
            DBClusterIdentifier='orders-docdb-secondary'
        )
        print(f"Failover initiated: {response}")

        # Notify operations team
        sns.publish(
            TopicArn='arn:aws:sns:eu-west-1:123456789012:failover-alerts',
            Subject='DocumentDB Global Cluster Failover',
            Message='Failover initiated for orders-global. Secondary promoted.'
        )
        return {'statusCode': 200}
    except Exception as e:
        print(f"Failover failed: {e}")
        raise
```

## Indexing strategy (no query optimizer)

### The fundamental difference

DocumentDB does NOT have a query optimizer. This is the single most
important difference from MongoDB for application developers:

```text
Query execution comparison:

  MongoDB:
    db.collection.find({status: "active"})
    → Query optimizer evaluates available indexes
    → If index on {status: 1} exists → uses it → fast
    → If no index → decides to scan or error
    → Can choose between multiple indexes

  DocumentDB:
    db.collection.find({status: "active"})
    → NO query optimizer
    → If index on {status: 1} exists → uses it → fast
    → If no index → FULL COLLECTION SCAN → slow (seconds on large collections)
    → Cannot choose between indexes (uses first matching)

  Expert rule:
    Create ALL needed indexes BEFORE deploying queries.
    There is no "the optimizer will figure it out" safety net.
```

### Index types

#### Single-field index

```javascript
// For queries filtering on one field
db.users.createIndex({ email: 1 })    // ascending
db.users.createIndex({ createdAt: -1 }) // descending

// Good for:
//   db.users.find({ email: "user@example.com" })
//   db.users.find().sort({ createdAt: -1 })
```

#### Compound index and the ESR rule

```javascript
// For queries filtering on multiple fields
// ESR rule: Equality fields first, Sort fields second, Range fields last
db.orders.createIndex({ status: 1, created_at: -1 })

// Good for:
//   db.orders.find({ status: "active" }).sort({ created_at: -1 })
//   db.orders.find({ status: "active", created_at: { $gte: ISODate("...") } })

// ESR explained:
//   E (Equality): status = "active" → exact match
//   S (Sort): created_at: -1 → sort order
//   R (Range): created_at: { $gte: ... } → range filter
//   Put E fields first, then S, then R in the compound index
```

#### Text index

```javascript
// For full-text search
db.products.createIndex({ name: "text", description: "text" })

// Good for:
//   db.products.find({ $text: { $search: "wireless headphones" } })

// Limitations:
//   One text index per collection
//   Does not support all MongoDB text search features
//   For advanced search, use Amazon OpenSearch instead
```

#### Unique index

```javascript
// Enforce uniqueness
db.accounts.createIndex({ accountId: 1 }, { unique: true })

// Prevents duplicate accountId values
// DocumentDB enforces uniqueness at insert/update time
```

#### TTL index

```javascript
// Auto-expire documents after N seconds
db.sessions.createIndex({ lastAccess: 1 }, { expireAfterSeconds: 3600 })

// Documents where lastAccess is older than 1 hour are automatically deleted
// TTL monitor runs periodically (set via ttl_monitor parameter)
```

### Index management best practices

```text
1. Create indexes BEFORE inserting large data volumes
   → Indexing an empty collection is instant
   → Indexing 10M documents takes minutes and consumes resources

2. Use background index builds for existing large collections
   → db.collection.createIndex({ field: 1 }, { background: true })
   → Non-blocking (does not lock the collection)
   → Slower but does not disrupt production

3. Monitor index usage
   → Use $indexStats to see if indexes are being used:
     db.collection.aggregate([{ $indexStats: {} }])
   → Remove unused indexes (they consume storage and slow writes)

4. Avoid over-indexing
   → Each index adds write overhead (every insert/update updates ALL indexes)
   → Rule of thumb: 3-5 indexes per collection for typical workloads
   → High-write collections should have fewer indexes

5. Cover all query patterns
   → Map every query pattern to an index
   → Any query without a matching index = full scan
```

### Common indexing pitfalls

| Pitfall | Impact | Fix |
|---|---|---|
| No index on a filtered field | Full collection scan, seconds of latency | Create index before deploying the query |
| Compound index in wrong order | Index not used for the query | Follow ESR rule (Equality, Sort, Range) |
| Too many indexes | Slow writes (every write updates all indexes) | Remove unused indexes via $indexStats |
| Missing index on sort field | In-memory sort (slow for large results) | Include sort field in compound index |
| Text index on wrong fields | Full-text search misses relevant docs | Index all searchable string fields |

### Terraform indexing (via null_resource)

Terraform cannot create DocumentDB indexes directly. Use a
`null_resource` with local-exec:

```hcl
resource "null_resource" "create_indexes" {
  depends_on = [aws_docdb_cluster_instance.replica_2]

  triggers = {
    cluster_endpoint = aws_docdb_cluster.main.endpoint
    always_run       = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOF
      mongosh "${aws_docdb_cluster.main.endpoint}:27017" \
        --username admin \
        --password '${var.docdb_password}' \
        --tls --tlsCAFile rds-combined-ca-bundle.pem \
        --eval '
          db = db.getSiblingDB("orders");
          db.orders.createIndex({ status: 1, created_at: -1 });
          db.users.createIndex({ email: 1 });
          print("Indexes created successfully");
        '
    EOF
  }
}
```
