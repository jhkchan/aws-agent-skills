# Journal Export and Kinesis Streaming — QLDB Ledger Deployer

Deep reference on QLDB journal export to S3 (compliance audit, output
format, IAM roles, export lifecycle) and Kinesis Data Streams streaming
(real-time CDC, stream configuration, record format, aggregation).
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Journal export to S3

### Purpose

Journal export writes the entire journal (or a time range) to S3 in Ion
format. It is for:
- Compliance audit (periodic snapshots for regulators)
- Data lake ingestion (downstream analytics)
- Disaster recovery (off-ledger copy of the journal)
- Migration (export to another ledger or system)

### Export vs streaming comparison

| Feature | Export to S3 | Stream to Kinesis |
|---|---|---|
| Purpose | Compliance audit, snapshot | Real-time CDC, continuous |
| Trigger | On-demand or scheduled | Continuous (start/end time) |
| Latency | Hours (for large journals) | Near real-time (seconds) |
| Output format | Ion blocks in S3 objects | Kinesis records (JSON/Ion) |
| Coverage | Full journal or time range | Incremental changes |
| Cost | S3 storage + one-time API | Kinesis shard hours + PUT cost |

**Expert rule:** use BOTH for a complete data pipeline. Export provides
the audit trail; streaming provides real-time CDC.

### Creating a journal export

```bash
# Prerequisites: S3 bucket + IAM role

# Create the S3 bucket
aws s3api create-bucket \
  --bucket qldb-audit-export \
  --region us-east-1

# Enable Object Lock (WORM) for compliance
aws s3api put-object-lock-configuration \
  --bucket qldb-audit-export \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 2555
      }
    }
  }'

# Create IAM role for QLDB export
aws iam create-role \
  --role-name QLDBExportRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "qldb.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach S3 permissions
aws iam put-role-policy \
  --role-name QLDBExportRole \
  --policy-name QLDBExportS3Policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
        "Resource": [
          "arn:aws:s3:::qldb-audit-export",
          "arn:aws:s3:::qldb-audit-export/*"
        ]
      }
    ]
  }'

# Start the export
aws qldb export-journal-to-s3 \
  --name audit-ledger \
  --export-name audit-export-2026-08 \
  --role-arn arn:aws:iam::123456789012:role/QLDBExportRole \
  --output-s3-prefix s3://qldb-audit-export/audit-ledger/2026-08/ \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-31T23:59:59Z \
  --region us-east-1
```

### Monitoring export progress

```bash
# Check export status
aws qldb describe-journal-s3-export \
  --name audit-ledger \
  --export-id <export-id> \
  --region us-east-1

# List all exports for a ledger
aws qldb list-journal-s3-exports-for-ledger \
  --name audit-ledger \
  --region us-east-1
```

Export statuses: `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `FAILED`.

### Export output format

The S3 bucket contains Ion-formatted journal blocks:

```text
s3://qldb-audit-export/audit-ledger/2026-08/
  ├── 2026-08-01/
  │   ├── block-1.ion
  │   ├── block-2.ion
  │   └── ...
  ├── 2026-08-02/
  │   └── ...
  └── manifest.json
```

Each Ion block file contains:

```ion
{
  blockAddress: {
    strandId: "ABC123...",
    sequenceNo: 42
  },
  blockHash: "base64...",
  previousBlockHash: "base64...",
  entries: [
    {
      entryHash: "base64...",
      entryType: "txn",
      ledgerTime: 2026-08-05T12:00:00Z,
      revision: {
        data: { transactionId: "txn-001", amount: 1500.0, ... },
        hash: "base64...",
        metadata: { id: "doc-123", version: 3, txTime: ... }
      }
    }
  ]
}
```

### Scheduled export (EventBridge + Lambda)

```python
import boto3
from datetime import datetime, timedelta

qldb = boto3.client('qldb')

def lambda_handler(event, context):
    # Triggered monthly by EventBridge schedule
    today = datetime.utcnow()
    last_month_start = today.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_start.replace(day=1)
    last_month_end = today.replace(day=1) - timedelta(seconds=1)

    qldb.export_journal_to_s3(
        Name='audit-ledger',
        ExportName=f'audit-export-{last_month_start.strftime("%Y-%m")}',
        RoleArn='arn:aws:iam::123456789012:role/QLDBExportRole',
        OutputS3Prefix=f's3://qldb-audit-export/audit-ledger/{last_month_start.strftime("%Y-%m")}/',
        StartTime=last_month_start,
        EndTime=last_month_end
    )
    return {'statusCode': 200}
```

## Kinesis Data Streams integration

### Purpose

QLDB streaming sends journal data to Kinesis Data Streams in near
real-time. It is for:
- Real-time change data capture (CDC)
- Downstream system synchronization (search index, cache, analytics)
- Event-driven architectures (trigger actions on ledger changes)
- Audit dashboards (live monitoring of ledger activity)

### Creating a QLDB stream

```bash
# Prerequisites: Kinesis stream + IAM role

# Create Kinesis stream
aws kinesis create-stream \
  --stream-name qldb-audit-stream \
  --shard-count 1 \
  --region us-east-1

aws kinesis wait stream-active \
  --stream-name qldb-audit-stream \
  --region us-east-1

# Create IAM role
aws iam create-role \
  --role-name QLDBStreamRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "qldb.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach Kinesis write policy
aws iam put-role-policy \
  --role-name QLDBStreamRole \
  --policy-name QLDBStreamKinesisPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
        "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/qldb-audit-stream"
      }
    ]
  }'

# Start the QLDB stream
aws qldb stream-journal-to-kinesis \
  --ledger-name audit-ledger \
  --role-arn arn:aws:iam::123456789012:role/QLDBStreamRole \
  --inclusive-start-time 2026-08-05T00:00:00Z \
  --exclusive-end-time 2026-12-31T23:59:59Z \
  --kinesis-configuration StreamName=qldb-audit-stream,AggregationEnabled=true \
  --stream-name audit-ledger-cdc-stream \
  --region us-east-1
```

### Stream record format

Each Kinesis record contains a QLDB revision event:

```json
{
  "qldbStreamArn": "arn:aws:qldb:us-east-1:123456789012:stream/...",
  "recordType": "REVISION",
  "payload": {
    "tableInfo": {
      "tableName": "transactions",
      "tableId": "table-abc123"
    },
    "revision": {
      "blockAddress": {
        "strandId": "ABC123",
        "sequenceNo": 42
      },
      "hash": "base64...",
      "data": {
        "transactionId": "txn-001",
        "amount": 1500.0,
        "status": "confirmed"
      },
      "metadata": {
        "id": "doc-123",
        "version": 2,
        "txTime": 1628164800,
        "txId": "tx-abc123"
      }
    }
  }
}
```

### Aggregation

When `AggregationEnabled=true`, QLDB batches multiple revisions into a
single Kinesis record using Kinesis Producer Library (KPL) aggregation:

```text
Without aggregation:
  Revision 1 → Kinesis record 1
  Revision 2 → Kinesis record 2
  Revision 3 → Kinesis record 3
  → 3 PUT calls, 3 records

With aggregation:
  Revisions 1+2+3 → Kinesis record 1 (KPL aggregated)
  → 1 PUT call, 1 record (containing 3 sub-records)
  → Lower cost, higher throughput

  Expert rule:
    Enable aggregation for high-throughput ledgers.
    Disable aggregation if you need per-record ordering guarantees
    or if downstream consumers cannot deaggregate.
```

### Monitoring streams

```bash
# List active streams for a ledger
aws qldb list-journal-kinesis-streams-for-ledger \
  --ledger-name audit-ledger \
  --region us-east-1

# Describe a specific stream
aws qldb describe-journal-kinesis-stream \
  --ledger-name audit-ledger \
  --stream-id <stream-id> \
  --region us-east-1

# CloudWatch: monitor Kinesis throughput
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name IncomingRecords \
  --dimensions Name=StreamName,Value=qldb-audit-stream \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Sum \
  --region us-east-1
```

### Stream lifecycle

```text
Stream states:
  ACTIVE → stream is running and sending data to Kinesis
  COMPLETED → stream reached its exclusive end time
  CANCELED → stream was manually canceled
  FAILED → stream encountered an error
  IMPAIRED → stream is running but some records failed to deliver

Stream time semantics:
  InclusiveStartTime: the journal time from which streaming begins
    → Must be within the journal's history
    → Events BEFORE this time are NOT streamed
  ExclusiveEndTime: the journal time at which streaming stops
    → Use far-future date for continuous streaming
    → Stream transitions to COMPLETED when this time is reached

Expert rule:
  For continuous CDC, set ExclusiveEndTime to a far-future date.
  Monitor for IMPAIRED state (indicates delivery issues).
  If the stream fails, restart with InclusiveStartTime at the
  last processed event's txTime.
```

### Consuming the Kinesis stream (Lambda)

```python
import base64
import json

def lambda_handler(event, context):
    for record in event['Records']:
        # Decode the Kinesis record
        payload = base64.b64decode(record['kinesis']['data'])

        # Parse the QLDB stream event
        qldb_event = json.loads(payload)

        if qldb_event['recordType'] == 'REVISION':
            revision = qldb_event['payload']['revision']
            table_name = qldb_event['payload']['tableInfo']['tableName']

            # Process the revision
            print(f"Table: {table_name}")
            print(f"Document ID: {revision['metadata']['id']}")
            print(f"Version: {revision['metadata']['version']}")
            print(f"Data: {revision['data']}")

            # Route to downstream system
            if table_name == 'transactions':
                process_transaction(revision)
            elif table_name == 'accounts':
                process_account(revision)

    return {'statusCode': 200}

def process_transaction(revision):
    # Sync to Elasticsearch, S3 data lake, analytics, etc.
    pass
```

## Terraform examples

```hcl
# QLDB Stream to Kinesis
resource "aws_qldb_stream" "cdc" {
  ledger_name          = aws_qldb_ledger.audit.name
  stream_name          = "audit-ledger-cdc-stream"
  role_arn             = aws_iam_role.qldb_stream.arn
  inclusive_start_time = "2026-08-05T00:00:00ZZ"
  exclusive_end_time   = "2026-12-31T23:59:59ZZ"

  kinesis_configuration {
    stream_arn           = aws_kinesis_stream.qldb_cdc.arn
    aggregation_enabled  = true
  }

  depends_on = [
    aws_iam_role_policy.qldb_stream_kinesis,
    aws_kinesis_stream.qldb_cdc
  ]
}

# Kinesis stream
resource "aws_kinesis_stream" "qldb_cdc" {
  name             = "qldb-audit-stream"
  shard_count      = 1
  retention_period = 168  # 7 days

  shard_level_metrics = [
    "IncomingRecords",
    "GetRecords.IteratorAgeMilliseconds"
  ]
}

# IAM role for QLDB to write to Kinesis
resource "aws_iam_role" "qldb_stream" {
  name = "QLDBStreamRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "qldb.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "qldb_stream_kinesis" {
  name = "QLDBStreamKinesisPolicy"
  role = aws_iam_role.qldb_stream.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["kinesis:PutRecord", "kinesis:PutRecords"]
        Resource = aws_kinesis_stream.qldb_cdc.arn
      }
    ]
  })
}
```


## Step 8 — Journal export to S3: commands

```bash
# Create IAM role that QLDB assumes to write to S3
aws iam create-role \
  --role-name QLDBExportRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"qldb.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name QLDBExportRole \
  --policy-name QLDBExportS3Policy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:PutObject","s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::qldb-audit-export","arn:aws:s3:::qldb-audit-export/*"]}]}'

# Export the journal to S3
aws qldb export-journal-to-s3 \
  --name audit-ledger \
  --export-name audit-export-2026-08 \
  --role-arn arn:aws:iam::123456789012:role/QLDBExportRole \
  --output-s3-prefix s3://qldb-audit-export/audit-ledger/2026-08/ \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-31T23:59:59Z \
  --region us-east-1
```

**Export output:** S3 objects in Ion-formatted journal blocks. Each
block includes the block hash, transaction metadata, and document
revisions.


## Step 9 — Stream to Kinesis: commands

```bash
# Prerequisite: create the Kinesis stream
aws kinesis create-stream --stream-name qldb-audit-stream --shard-count 1 --region us-east-1
aws kinesis wait stream-active --stream-name qldb-audit-stream --region us-east-1

# Create IAM role for QLDB to write to Kinesis
aws iam create-role \
  --role-name QLDBStreamRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"qldb.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name QLDBStreamRole \
  --policy-name QLDBStreamKinesisPolicy \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["kinesis:PutRecord","kinesis:PutRecords"],"Resource":"arn:aws:kinesis:us-east-1:123456789012:stream/qldb-audit-stream"}]}'

# Start streaming journal data to Kinesis
aws qldb stream-journal-to-kinesis \
  --ledger-name audit-ledger \
  --role-arn arn:aws:iam::123456789012:role/QLDBStreamRole \
  --inclusive-start-time 2026-08-05T00:00:00Z \
  --exclusive-end-time 2026-12-31T23:59:59Z \
  --kinesis-configuration StreamName=qldb-audit-stream,AggregationEnabled=true \
  --stream-name audit-ledger-cdc-stream \
  --region us-east-1
```
