# Revision Lifecycle and Export Jobs — Data Exchange Dataset Deployer

Deep reference on revision lifecycle (create, add assets, finalize,
publish), export job creation and asynchronous behavior, auto-export
EventBridge orchestration, and asset type export semantics. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Revision lifecycle

### Revision states

```text
DRAFT → FINALIZED → PUBLISHED (visible to subscribers)

  DRAFT:     revision created by provider; assets being added
             NOT visible to subscribers
             CAN add/remove assets
             CAN be deleted

  FINALIZED: provider has committed the revision
             ONE-WAY operation — cannot revert to DRAFT
             Cannot add/remove/modify assets
             Becomes visible to subscribers

  PUBLISHED: In some flows, finalization automatically publishes
             Subscribers can see and export the revision
```

### Creating and finalizing revisions (provider flow)

```bash
# Create a revision
REVISION_ID=$(aws dataexchange create-revision \
  --data-set-id <data-set-id> \
  --comment "Q3 2026 market data" \
  --query 'Id' --output text \
  --region us-east-1)

# Add assets to the revision (before finalizing)
aws dataexchange put-data-set-revision-assets \
  --data-set-id <data-set-id> \
  --revision-id "$REVISION_ID" \
  --assets '[{"Bucket": "my-source-bucket", "Key": "data/q3-2026.csv"}]' \
  --region us-east-1

# Finalize the revision (ONE-WAY — verify assets first!)
aws dataexchange update-revision \
  --data-set-id <data-set-id> \
  --revision-id "$REVISION_ID" \
  --finalized \
  --region us-east-1
```

**Critical:** finalization is irreversible. Verify all assets are
present before finalizing. Once finalized, the revision is committed
and cannot be modified.

### Discovering revisions (subscriber flow)

```bash
# List all revisions for a subscribed data set
aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --region us-east-1

# Get the latest revision
LATEST_REVISION=$(aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --query 'Revisions[0].Id' --output text \
  --region us-east-1)

# Get revision details (including asset list)
aws dataexchange get-revision \
  --data-set-id <data-set-id> \
  --revision-id "$LATEST_REVISION" \
  --region us-east-1
```

## Export job lifecycle

### Job types

| Job type | Direction | Use case |
|---|---|---|
| EXPORT_ASSETS_TO_S3 | Data Exchange → subscriber S3 | Subscriber pulls data |
| IMPORT_ASSETS_FROM_S3 | Subscriber S3 → Data Exchange | Provider publishes data |

### Creating an export job

```bash
# Create the job
JOB_ID=$(aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{
    "ExportAssetsToS3": {
      "DataSetId": "<data-set-id>",
      "RevisionId": "<revision-id>",
      "AssetDestination": {
        "Bucket": "my-subscriber-bucket",
        "Key": "data-exchange/exports/latest/"
      }
    }
  }' \
  --query 'Id' --output text \
  --region us-east-1)

# Start the job
aws dataexchange start-job \
  --job-id "$JOB_ID" \
  --region us-east-1
```

### Job states (asynchronous)

```text
PENDING → IN_PROGRESS → COMPLETED
                    → ERROR
                    → CANCELLED

  PENDING:     job created, waiting to start
  IN_PROGRESS: job actively copying data
  COMPLETED:   all assets exported successfully
  ERROR:       job failed (check errors array in GetJob response)
  CANCELLED:   job was cancelled

Duration: minutes to hours depending on data volume.
```

### Polling job status

```bash
# Poll until COMPLETED or ERROR
while true; do
  STATE=$(aws dataexchange get-job \
    --job-id "$JOB_ID" \
    --query 'State' --output text \
    --region us-east-1)

  echo "Job state: $STATE"

  if [ "$STATE" = "COMPLETED" ] || [ "$STATE" = "ERROR" ]; then
    break
  fi

  sleep 30
done

# Get full job details including errors
aws dataexchange get-job \
  --job-id "$JOB_ID" \
  --region us-east-1
```

### EventBridge job completion notification

```bash
# EventBridge rule for job completion
aws events put-rule \
  --name "DataExchangeJobCompleted" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Job Status Change"],
    "detail": {
      "state": ["COMPLETED"]
    }
  }' \
  --region us-east-1

# Target: SNS topic or Lambda for downstream processing
aws events put-targets \
  --rule "DataExchangeJobCompleted" \
  --targets '[{"Id": "1", "Arn": "arn:aws:sns:us-east-1:123456789012:dx-job-complete"}]' \
  --region us-east-1
```

## Auto-export orchestration

### Why auto-export is needed

Without auto-export, when a provider publishes a new revision:

1. The revision appears in the subscriber's Data Exchange view.
2. The subscriber is NOT notified (no default notification).
3. The subscriber must manually create and start an export job.
4. Data does NOT appear in the subscriber's S3 bucket automatically.

Auto-export solves this by automating steps 2-4.

### Auto-export architecture

```text
Provider publishes revision
  ↓
EventBridge emits "Data Update" event
  ↓
EventBridge rule matches event for this data set
  ↓
Lambda function triggered
  ↓
Lambda calls CreateJob (EXPORT_ASSETS_TO_S3) + StartJob
  ↓
Export job copies assets to subscriber S3
  ↓
S3 PUT event triggers downstream processing (optional)
```

### Complete auto-export Lambda function

```python
import boto3
import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dataexchange = boto3.client('dataexchange')

DESTINATION_BUCKET = os.environ['DESTINATION_BUCKET']
DATA_SET_ID = os.environ['DATA_SET_ID']
EXPORT_PREFIX = os.environ.get('EXPORT_PREFIX', 'auto-export/')

def lambda_handler(event, context):
    """Triggered by EventBridge on Data Exchange Data Update event."""
    logger.info(f"Event: {json.dumps(event)}")

    # Extract revision info from the event
    detail = event.get('detail', {})
    revision_id = detail.get('revision-id', '')
    data_set_id = detail.get('data-set-id', '')

    if not revision_id or not data_set_id:
        logger.error("Missing revision-id or data-set-id in event")
        return {'statusCode': 400, 'body': 'Missing required fields'}

    # Verify this is the data set we care about
    if data_set_id != DATA_SET_ID:
        logger.info(f"Ignoring event for data set {data_set_id}")
        return {'statusCode': 200, 'body': 'Ignored (different data set)'}

    try:
        # Create export job
        job = dataexchange.create_job(
            type='EXPORT_ASSETS_TO_S3',
            details={
                'ExportAssetsToS3': {
                    'DataSetId': data_set_id,
                    'RevisionId': revision_id,
                    'AssetDestination': {
                        'Bucket': DESTINATION_BUCKET,
                        'Key': f'{EXPORT_PREFIX}{revision_id}/'
                    }
                }
            }
        )

        job_id = job['Id']
        logger.info(f"Created export job: {job_id}")

        # Start the job
        dataexchange.start_job(JobId=job_id)
        logger.info(f"Started export job: {job_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'revision_id': revision_id,
                'destination': f's3://{DESTINATION_BUCKET}/{EXPORT_PREFIX}{revision_id}/'
            })
        }

    except Exception as e:
        logger.error(f"Failed to create/start export job: {e}")
        return {'statusCode': 500, 'body': str(e)}
```

### EventBridge rule for auto-export

```bash
aws events put-rule \
  --name "DataExchangeAutoExport" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Data Update"],
    "detail": {
      "data-set-id": ["ds-auto123"]
    }
  }' \
  --region us-east-1

# Add Lambda as target
aws events put-targets \
  --rule "DataExchangeAutoExport" \
  --targets '[{
    "Id": "1",
    "Arn": "arn:aws:lambda:us-east-1:123456789012:function:dx-auto-export",
    "InputTransformer": {
      "InputPathsMap": {
        "data-set-id": "$.detail.data-set-id",
        "revision-id": "$.detail.revision-id"
      },
      "InputTemplate": "{\"detail\": {\"data-set-id\": <data-set-id>, \"revision-id\": <revision-id>}}"
    }
  }]' \
  --region us-east-1
```

## Asset type export semantics

### S3_SNAPSHOT assets

S3_SNAPSHOT assets are S3 objects (CSV, JSON, Parquet, etc.) that
get copied from the provider to the subscriber's S3 bucket.

```bash
# Export maps each asset to a key in the destination bucket
# Provider S3: s3://provider-bucket/data/file.csv
# Exported to: s3://subscriber-bucket/exports/file.csv
```

### REDSHIFT_SNAPSHOT assets

REDSHIFT_SNAPSHOT assets are Redshift cluster snapshots. These are
NOT exported to S3 — they are restored to a Redshift cluster.

```bash
# Requires a Redshift cluster in the subscriber account
# Snapshot is restored to the cluster, not to S3
aws redshift restore-from-cluster-snapshot \
  --cluster-identifier my-dx-cluster \
  --snapshot-identifier <snapshot-id> \
  --region us-east-1
```

### API assets

API assets are REST endpoints accessed LIVE through the Data Exchange
API gateway. They are NOT exported to S3.

```python
# Access API asset live
import boto3
import requests

dataexchange = boto3.client('dataexchange')

# Get the API asset details
response = dataexchange.get_asset(
    DataSetId='<data-set-id>',
    RevisionId='<revision-id>',
    AssetId='<asset-id>'
)

api_url = response['ApiDescription']['Url']

# Sign the request with Data Exchange credentials
# (Data Exchange provides signing keys for authentication)
```

### QUERY assets (Lake Formation)

QUERY assets are Lake Formation-backed SQL query results. The query
runs against the provider's Lake Formation data, and results are
exported to the subscriber's S3 bucket.

## Terraform export job example

```hcl
resource "aws_dataexchange_job" "export" {
  type = "EXPORT_ASSETS_TO_S3"

  details = jsonencode({
    ExportAssetsToS3 = {
      DataSetId   = var.data_set_id
      RevisionId  = var.revision_id
      AssetDestination = {
        Bucket = aws_s3_bucket.export.id
        Key    = "exports/latest/"
      }
    }
  })
}
```
