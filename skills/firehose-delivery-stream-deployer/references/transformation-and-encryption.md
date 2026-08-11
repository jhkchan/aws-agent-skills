# Transformation and Encryption — Firehose Delivery Stream Deployer

Deep reference on Lambda transformation (blueprints, input/output
contract, error handling), format conversion (Parquet/ORC via Glue
schema, dynamic schema evolution), KMS server-side encryption (buffer
encryption, S3 delivery encryption, IAM role permissions), and IAM
role configuration. Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## Lambda transformation

### Input/output contract

Firehose invokes the Lambda function with a batch of records. The
function receives a base64-encoded event and must return a response
with transformed records.

**Input event structure:**

```json
{
  "invocationId": "abc-123",
  "deliveryStreamArn": "arn:aws:firehose:us-east-1:...:deliverystream/events",
  "region": "us-east-1",
  "records": [
    {
      "recordId": "49546986683135544286507257936321625675700192471156224010",
      "approximateArrivalTimestamp": 1700000000000,
      "data": "eyJldmVudCI6ICJsb2dpbiIsICJ1c2VyIjogImFsaWNlIn0="
    }
  ]
}
```

**Output response structure:**

```json
{
  "records": [
    {
      "recordId": "49546986683135544286507257936321625675700192471156224010",
      "result": "Ok",
      "data": "eyJldmVudCI6ICJsb2dpbiIsICJ1c2VyIjogImFsaWNlIiwgInRzIjogIjIwMjYtMDEtMTUifQ=="
    }
  ]
}
```

**Result values:**

| Result | Behavior |
|---|---|
| `Ok` | Record is transformed and continues to the destination |
| `Dropped` | Record is silently discarded (not delivered, not backed up) |
| `ProcessingFailed` | Record is treated as a processing error (goes to error prefix) |

### Common transformation blueprints

#### 1. JSON parsing + field extraction

```python
import base64
import json

def lambda_handler(event, context):
    output = []
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        transformed = {
            'event': payload.get('event'),
            'user': payload.get('user'),
            'timestamp': payload.get('ts')
        }
        encoded = base64.b64encode(json.dumps(transformed).encode()).decode()
        output.append({
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': encoded
        })
    return {'records': output}
```

#### 2. Enrichment (add computed fields)

```python
import base64
import json
import socket

def lambda_handler(event, context):
    output = []
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        # Enrich with hostname
        payload['hostname'] = socket.gethostname()
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        output.append({
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': encoded
        })
    return {'records': output}
```

#### 3. Filtering (drop records not matching criteria)

```python
import base64
import json

def lambda_handler(event, context):
    output = []
    for record in event['records']:
        payload = json.loads(base64.b64decode(record['data']))
        if payload.get('level') == 'DEBUG':
            # Drop DEBUG logs
            output.append({
                'recordId': record['recordId'],
                'result': 'Dropped',
                'data': record['data']
            })
        else:
            output.append({
                'recordId': record['recordId'],
                'result': 'Ok',
                'data': record['data']
            })
    return {'records': output}
```

#### 4. Format conversion prep (ensure valid JSON for Parquet)

```python
import base64
import json

def lambda_handler(event, context):
    output = []
    for record in event['records']:
        raw = base64.b64decode(record['data'])
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Fix malformed JSON or drop
            payload = {'raw': raw.decode('utf-8', errors='replace'), 'error': 'malformed_json'}
        # Ensure all Glue schema fields exist
        payload.setdefault('event', 'unknown')
        payload.setdefault('user', 'unknown')
        payload.setdefault('timestamp', None)
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        output.append({
            'recordId': record['recordId'],
            'result': 'Ok',
            'data': encoded
        })
    return {'records': output}
```

### Lambda + format conversion interaction

When BOTH Lambda transformation and Parquet format conversion are
enabled, the data flow is:

```text
Source → Lambda transformation → format conversion (Glue schema) → S3 (Parquet)
```

**Critical:** the Lambda output MUST be valid JSON with fields matching
the Glue table schema. If Lambda returns malformed JSON or missing
fields, format conversion fails and records go to the S3 error prefix.

### Lambda transformation errors

If the Lambda function throws an exception or returns a non-200
response, Firehose retries the invocation (up to the retry limit).
After retries are exhausted, the batch of records goes to the S3
backup bucket.

## Format conversion (Parquet/ORC)

### How format conversion works

Format conversion uses a Glue Data Catalog table schema to serialize
JSON records into columnar formats (Parquet or ORC). No custom code
is needed.

**Requirements:**
- A Glue database and table with a defined schema.
- The Firehose IAM role must have `glue:GetTable` permissions.
- Input records must be valid JSON matching the table schema.

### Glue table schema for Firehose

```bash
# Create a Glue table matching the Firehose record schema
aws glue create-table \
  --database-name analytics \
  --table-input '{
    "Name": "events_table",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "event", "Type": "string"},
        {"Name": "user", "Type": "string"},
        {"Name": "timestamp", "Type": "string"},
        {"Name": "hostname", "Type": "string"}
      ]
    },
    "Parameters": {
      "classification": "json"
    }
  }'
```

### Schema evolution

When the record schema changes (new fields added), update the Glue
table to include the new columns. Firehose will then serialize the new
fields into the Parquet output.

**Missing fields in records:** if a record does not have a field
defined in the Glue schema, the field is set to NULL in the Parquet
output.

**Extra fields in records:** if a record has fields not in the Glue
schema, they are silently dropped during format conversion.

### OpenX JSON SerDe vs Hive JSON SerDe

Firehose supports two JSON deserializers for format conversion:

| Deserializer | Pros | Cons |
|---|---|---|
| OpenXJsonSerDe (recommended) | Tolerant of schema variations; handles missing/extra fields | Slightly different timestamp parsing |
| HiveJsonSerDe | Standard Hive compatibility | Stricter; fails on extra fields |

Use OpenXJsonSerDe for most cases — it is more forgiving of schema
variations.

## KMS server-side encryption

### What KMS encrypts

KMS encryption applies to two stages:

1. **Buffer encryption:** data buffered in Firehose memory/disk before
   delivery to the destination is encrypted with the specified KMS key.
2. **S3 delivery encryption:** data delivered to S3 is encrypted with
   the specified KMS key (server-side encryption).

### Configuration

```bash
# In the S3 destination config:
EncryptionConfiguration:
  KMSEncryptionConfig:
    AWSKMSKeyARN: arn:aws:kms:us-east-1:123456789012:key/abc123
```

### KMS key options

| Key type | ARN format | Cost | When to use |
|---|---|---|---|
| AWS managed key | `aws/s3` (alias) | Free | Simplest, default S3 encryption |
| Customer managed key | `arn:aws:kms:...:key/<id>` | $1/month + per-API-call | Fine-grained access control, audit trail |

For compliance-sensitive data, use a customer-managed key. For
simplicity, use the AWS managed key.

### IAM role permissions for KMS

The Firehose IAM role must have:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abc123"
    }
  ]
}
```

## IAM role configuration

### Trust policy

The Firehose IAM role must trust `firehose.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "firehose.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Permissions policy (S3 + Parquet + Lambda + KMS)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:AbortMultipartUpload", "s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket", "s3:ListBucketMultipartUploads", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::my-data-lake", "arn:aws:s3:::my-data-lake/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction", "lambda:GetFunctionConfiguration"],
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:firehose-transform"
    },
    {
      "Effect": "Allow",
      "Action": ["glue:GetTable", "glue:GetDatabase"],
      "Resource": ["arn:aws:glue:us-east-1:123456789012:database/analytics", "arn:aws:glue:us-east-1:123456789012:table/analytics/events_table"]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abc123"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/kinesisfirehose/*"
    }
  ]
}
```

### Common IAM pitfalls

1. **Missing Glue permissions for format conversion.** The role needs
   `glue:GetTable` and `glue:GetDatabase` for the specified Glue table
   and database. Without these, format conversion fails.

2. **Missing Lambda invoke permission.** The role needs
   `lambda:InvokeFunction` for the transformation Lambda ARN.

3. **Missing KMS permissions.** If KMS encryption is enabled, the role
   needs `kms:Decrypt` and `kms:GenerateDataKey` for the KMS key ARN.

4. **Missing S3 backup bucket permissions.** The role needs S3 write
   permissions for the backup bucket, separate from the main delivery
   bucket.

5. **Missing CloudWatch Logs permissions.** The role needs
   `logs:PutLogEvents` for the log group ARN.
