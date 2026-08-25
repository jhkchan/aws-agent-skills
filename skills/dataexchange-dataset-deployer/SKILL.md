---
name: dataexchange-dataset-deployer
description: 'Deploys AWS Data Exchange data sets with production defaults: subscription creation (data product from providers), asset export to S3, revision auto-export (EventBridge triggered on new data revision), data set entitlement (share with specific AWS accounts — entitlement is the sharing mechanism, NOT IAM), job creation (export jobs, import jobs), asset structure (S3 objects, DynamoDB tables, REST API assets), Lake Formation integration for governed data access, auto-export to S3 for BI tool consumption, revision lifecycle (create revision, add assets, finalize, publish), CloudWatch monitoring for job status and data freshness. Emits a READY_TO_DEPLOY checklist with verification commands. Use when subscribing. Triggers: create data exchange subscription, data exchange asset export, data exchange revision auto-export, data exchange entitlement, data exchange export job, data exchange import job, data exchange lake formation, data exchange API asset, data exchange revision lifecycle, data exchange S3...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with dataexchange and s3 access, plus EventBridge for auto-export rules. Works with Terraform aws_dataexchange_dataset / aws_dataexchange_revision resources and CloudFormation AWS::DataExchange::DataSet / AWS::DataExchange::Job templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, data-exchange, analytics, cloudops, deploy, provisioning, subscription, revision, entitlement, auto-export, lake-formation, eventbridge
  dependencies: aws-orchestrator
  keywords: aws, data exchange, dataexchange, data set, dataset, subscription, analytics, cloudops, deploy, provisioning, revision, asset, entitlement, auto-export, lake formation, export job, api asset, eventbridge
  when_to_use: Invoke when the user wants to subscribe to an AWS Data Exchange data product, export data exchange assets to S3, set up auto- export for new revisions, share a data set with another AWS account via entitlement, create an export or import job, integrate Data Exchange with Lake Formation for governed data, consume API assets as REST endpoints, or configure revision auto-export with EventBridge. Do NOT invoke for AWS Glue data catalogs (use Glue skills), AWS Lake Formation table grants without Data Exchange (use Lake Formation skills), or S3 data transfer without Data Exchange (use S3 skills).
---

# Data Exchange Dataset Deployer

An AWS CloudOps agent skill that deploys AWS Data Exchange data sets
with correct defaults. The skill walks the operator through
subscription creation, asset structure (S3 objects, DynamoDB tables,
API assets), revision lifecycle (create, add assets, finalize,
publish), export job creation, auto-export rule configuration
(EventBridge triggered on new revisions), entitlement-based sharing
(NOT IAM), Lake Formation integration for governed access, and
CloudWatch monitoring for job status and data freshness, captures all
provisioning decisions, explains why each default matters, and emits
a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Data Exchange subscription, Data Exchange asset export, Data
Exchange revision auto-export, Data Exchange entitlement, Data
Exchange export job, Data Exchange import job, Data Exchange Lake
Formation, Data Exchange API asset, Data Exchange revision lifecycle,
Data Exchange S3 auto-export.

## STRICT output contract

When this skill is invoked with a Data Exchange deployment request
(subscribe to a data product, export assets, set up auto-export,
share via entitlement, create a job, integrate Lake Formation, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `DATA_EXCHANGE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Subscription creation | Data product from providers |
| Step 2 — Asset structure | S3, DynamoDB, API assets |
| Step 3 — Revision lifecycle | Create, finalize, publish |
| Step 4 — Asset export to S3 | Export job creation |
| Step 5 — Revision auto-export (EventBridge) | Auto-export on new revision |
| Step 6 — Data set entitlement | Sharing mechanism |
| Step 7 — Job creation (export, import) | Job lifecycle |
| Step 8 — Lake Formation integration | Governed data access |
| Step 9 — Auto-export to S3 for BI tools | BI consumption |
| Step 10 — API assets (REST endpoints) | API as data product |
| Step 11 — CloudWatch monitoring | Job + freshness monitoring |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/revision-and-export.md | Revision + export detail |
| references/entitlement-and-lake-formation.md | Entitlement + LF detail |

## Mindset

**One-line takeaway:** AWS Data Exchange is a marketplace for data
products. A subscription grants access to a data set. Revisions are
versioned snapshots of the data — each revision contains assets (S3
objects, DynamoDB table exports, API endpoints). Auto-export
(EventBridge rule) triggers an export job when a new revision is
published, automatically delivering fresh data to your S3 bucket.
Entitlements are the sharing mechanism — NOT IAM. Lake Formation
integration provides governed, fine-grained access to the exported
data.

Three misconceptions dominate Data Exchange misdesign at provisioning
time:

- **"IAM policies control data access."** They do NOT for Data
  Exchange sharing. Entitlements are the sharing mechanism. A data
  set is shared with a specific AWS account via an entitlement, not
  via IAM role trust or bucket policy. The receiving account accesses
  the data through the Data Exchange API or auto-export, not through
  direct S3 access. IAM controls who can call Data Exchange APIs,
  but entitlements control which data sets an account can access.

- **"Revisions auto-export by default."** They do NOT. By default,
  when a provider publishes a new revision, the subscriber must
  manually trigger an export job to get the new data. Auto-export
  requires an EventBridge rule that triggers on the
  "Data Update" event from Data Exchange, which then calls
  StartJob to export the new revision to the subscriber's S3 bucket.
  Without this rule, new revisions sit in Data Exchange and are
  never delivered to the subscriber's analytics pipeline.

- **"Export jobs are synchronous."** They are NOT. Export jobs are
  asynchronous — they run in the background and can take minutes to
  hours depending on data volume. The job status transitions from
  PENDING to IN_PROGRESS to COMPLETED (or ERROR). Polling job status
  via GetJob or monitoring via EventBridge/CloudWatch is required.
  Scripts that start a job and immediately try to read the exported
  data will fail.

## Configuration dependency graph (novel heuristic)

Data Exchange configurations are NOT independent. The subscription
must exist before revisions are visible. Revisions must be finalized
before assets can be exported. Auto-export rules must reference the
correct job definition. Entitlements must be set before the receiving
account can access the data set. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subscription | data product exists in marketplace; subscriber account approved | subscription terms accepted at creation; cannot be partially scoped | access to data set revisions |
| Data set | subscription active; data set ID known | data set belongs to the provider; subscribers cannot modify the data set | revisions |
| Revision | data set exists; revision created by provider | revision must be FINALIZED before assets can be exported; drafts are invisible to subscribers | asset export |
| Assets | revision exists; asset type matches export destination | S3 snapshot assets export to S3; API assets are accessed live (not exported); DynamoDB exports as S3 objects | export job |
| Export job | revision FINALIZED; destination S3 bucket exists; IAM role with s3:PutObject | job is ASYNCHRONOUS; polling required; job definition specifies mapping of assets to S3 keys | data in subscriber S3 |
| Auto-export rule | EventBridge rule on "Data Update" event; Lambda or Step Functions to call StartJob | auto-export does NOT exist by default; must be explicitly configured; wrong job definition = silent failure | automatic data delivery on new revisions |
| Entitlement | data set exists; target AWS account ID known; entitlement created by provider (or via product) | entitlement is the SHARING mechanism — not IAM; receiving account cannot access without entitlement; target account must accept | data sharing across accounts |
| Lake Formation | exported data in S3; Lake Formation enabled; Data Catalog database/table created | LF grants control column/row-level access; without LF, IAM bucket policy is the only access control | governed, fine-grained data access |
| API asset | subscription active; API asset type in data set | API assets are accessed LIVE via Data Exchange API gateway; NOT exported to S3; auth via Data Exchange credentials | REST endpoint data consumption |

**The auto-export-rule row is the one a baseline model misses.**
Without an EventBridge auto-export rule, new revisions are published
but never delivered to the subscriber's S3 bucket. The data sits in
Data Exchange and the subscriber never knows a new revision arrived.
The procedure below forces an explicit decision on auto-export.

**Cross-dependency gotchas:**
- Export jobs are asynchronous. Scripts that start a job and
  immediately read from the destination S3 bucket will fail. Poll
  job status or use EventBridge to trigger downstream processing
  only after job completion.
- Entitlements are the sharing mechanism, NOT IAM. Adding IAM
  policies for the receiving account does NOT grant access to the
  data set. The provider must create an entitlement for the target
  account.
- API assets are accessed LIVE through the Data Exchange API
  gateway — they are NOT exported to S3. S3 auto-export rules do
  not apply to API assets.
- Lake Formation grants apply to the exported data in the Data
  Catalog, not to Data Exchange itself. LF integration requires the
  data to be exported to S3 first, then registered as a LF-managed
  table.
- Revision finalization is a one-way operation. Once finalized, a
  revision cannot be modified. All assets must be added BEFORE
  finalization.

## Expert heuristic: auto-export revision rule

A baseline model says "subscribe and export." The correct heuristic
recognizes that auto-export is a separate EventBridge-triggered
workflow that must be explicitly configured.

```text
Auto-export flow:
  1. Provider publishes new revision (finalize + publish)
  2. EventBridge emits "Data Update" event
     → Event source: aws.dataexchange
     → Detail type: Data Update
     → Contains: data set ID, revision ID
  3. EventBridge rule matches the event
     → Routes to Lambda / Step Functions target
  4. Lambda calls StartJob with:
     → Job type: EXPORT_ASSETS_TO_S3
     → Revision ID from the event
     → Destination S3 bucket (subscriber's)
     → Asset-to-key mapping
  5. Export job runs asynchronously
     → Status: PENDING → IN_PROGRESS → COMPLETED
  6. Data appears in subscriber's S3 bucket
  7. Downstream EventBridge/Step Functions triggered by S3 PUT

Without steps 2-4: revision sits in Data Exchange, never delivered.
```

**Key implication:** auto-export is NOT a Data Exchange feature
that you toggle on. It is an EventBridge + Lambda orchestration
that you build. The skill provides the template for this
orchestration.

## Expert heuristic: entitlement is the sharing mechanism

A baseline model says "share via IAM role." The correct heuristic
recognizes that entitlements control data set access across
accounts.

```text
Sharing decision tree:
  ├── Provider shares with subscriber → entitlement (provider creates)
  │     └── Subscriber accepts → accesses data via Data Exchange API or auto-export
  ├── Internal account sharing → Lake Formation grants (after export to S3)
  │     └── LF controls column/row-level access for IAM principals
  └── Cross-account S3 access (post-export) → S3 bucket policy or cross-account IAM
        └── This is for the EXPORTED data only, not the Data Exchange data set

Entitlement vs IAM:
  Entitlement: "Account X is allowed to access data set Y"
  IAM:         "Principal Z is allowed to call dataexchange:StartJob"
  Both needed: entitlement (what you can access) + IAM (what you can call)
```

**Key implication:** to share a Data Exchange data set with another
account, create an entitlement. IAM alone does not grant data set
access.

## Expert heuristic: asset types determine export behavior

A baseline model says "export the data." The correct heuristic
recognizes that different asset types have different export behavior.

```text
Asset type → Export behavior:
  S3_SNAPSHOT  → Exported to subscriber's S3 bucket as objects
                  Export job copies S3 objects from provider to subscriber
                  Mapping: asset name → S3 key prefix

  REDSHIFT_SNAPSHOT → Exported as Redshift snapshot (must have Redshift cluster)
                       NOT exported to S3

  API         → Accessed LIVE via Data Exchange API gateway
                NOT exported to S3
                Auth via Data Exchange signing key
                Rate-limited per entitlement

  QUERY       → Lake Formation-backed SQL query results
                Requires LF integration
                Results exported to S3
```

**Key implication:** S3 auto-export works for S3_SNAPSHOT assets.
API assets are consumed live and cannot be auto-exported. Redshift
snapshots require a Redshift cluster.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Data product exists in marketplace | Subscription requires a valid product | `aws dataexchange list-data-sets` |
| Subscriber account approved | Some products require provider approval | Check subscription status |
| Destination S3 bucket exists | Export jobs write to a subscriber-owned S3 bucket | `aws s3 ls s3://<bucket>` |
| IAM role for export jobs | Export job needs s3:PutObject on destination bucket | Check IAM role policy |
| EventBridge rule (for auto-export) | Auto-export requires event-driven orchestration | `aws events list-rules --name-pattern "*dataexchange*"` |
| Lambda function (for auto-export) | EventBridge target that calls StartJob | `aws lambda list-functions` |
| Entitlement created (for sharing) | Sharing mechanism — NOT IAM | `aws dataexchange list-data-set-revisions` |
| Lake Formation enabled (for governed access) | LF controls fine-grained access | `aws lakeformation describe-resource` |
| Data Catalog database (for LF integration) | LF tables live in a Data Catalog database | `aws glue get-database --name <db>` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Subscription creation

A subscription grants access to a data product from a provider. The
data product contains one or more data sets.

**Create a subscription (subscribe to a product):**

```bash
# List available data sets
aws dataexchange list-data-sets \
  --region us-east-1

# Create a subscription (from AWS marketplace product)
aws marketplace subscribe \
  --product-id <product-id> \
  --region us-east-1
```

**View subscription details:**

```bash
# List revisions for a subscribed data set
aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --region us-east-1

# Get revision details
aws dataexchange get-revision \
  --data-set-id <data-set-id> \
  --revision-id <revision-id> \
  --region us-east-1
```

**Subscription states:**

| State | Description |
|---|---|
| ACTIVE | Subscription is active; revisions accessible |
| EXPIRED | Subscription expired; no new revisions |
| CANCELED | Subscription canceled by subscriber or provider |

## Step 2 — Asset structure

Each revision in a data set contains assets. Asset types determine
how the data is consumed.

| Asset type | Content | Export destination | Auto-exportable |
|---|---|---|---|
| S3_SNAPSHOT | S3 objects (CSV, JSON, Parquet, etc.) | Subscriber's S3 bucket | YES |
| REDSHIFT_SNAPSHOT | Amazon Redshift cluster snapshot | Redshift (not S3) | NO |
| API | REST API endpoints (live access) | Data Exchange API gateway (live) | NO |
| QUERY | Lake Formation SQL query results | S3 (via LF) | YES |

**List assets in a revision:**

```bash
aws dataexchange list-data-set-revisions \
  --data-set-id <data-set-id> \
  --region us-east-1

# Get assets for a specific revision
aws dataexchange get-revision \
  --data-set-id <data-set-id> \
  --revision-id <revision-id> \
  --region us-east-1
```

## Step 3 — Revision lifecycle

Revisions are versioned snapshots of the data set. Each revision
follows a lifecycle.

```text
Revision lifecycle:
  1. Create revision → status: DRAFT
  2. Add assets → attach S3, API, or query assets
  3. Finalize → status: FINALIZED (one-way operation — cannot modify after)
  4. Publish → visible to subscribers
  5. Subscriber exports → creates export job
```

**Create a revision (provider):**

```bash
aws dataexchange create-revision \
  --data-set-id <data-set-id> \
  --comment "Monthly data update - August 2026" \
  --region us-east-1
```

**Finalize a revision:**

```bash
aws dataexchange update-revision \
  --data-set-id <data-set-id> \
  --revision-id <revision-id> \
  --finalized \
  --region us-east-1
```

**Critical:** finalization is a ONE-WAY operation. Once finalized,
assets cannot be added or removed. Verify all assets are present
before finalizing.

## Step 4 — Asset export to S3

Export jobs copy S3_SNAPSHOT assets from the provider to the
subscriber's S3 bucket.

**Create an export job:**

```bash
aws dataexchange start-job \
  --job-id <job-id> \
  --region us-east-1

# Or create and start a job
aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{
    "ExportAssetsToS3": {
      "DataSetId": "<data-set-id>",
      "RevisionId": "<revision-id>",
      "AssetDestination": {
        "AssetSources": [
          {
            "Bucket": "provider-bucket",
            "Key": "data/file.csv"
          }
        ],
        "Destination": {
          "Bucket": "subscriber-bucket",
          "Key": "exports/data-exchange/file.csv"
        }
      }
    }
  }' \
  --region us-east-1
```

**Job is asynchronous — poll for completion:**

```bash
aws dataexchange get-job \
  --job-id <job-id> \
  --region us-east-1
# Expected: state: COMPLETED
```

## Step 5 — Revision auto-export (EventBridge)

Auto-export delivers new revisions to the subscriber's S3 bucket
automatically. This requires an EventBridge rule + Lambda function.

**EventBridge rule (triggers on new revision):**

```bash
aws events put-rule \
  --name "DataExchangeAutoExport" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Data Update"],
    "detail": {
      "data-set-id": ["<data-set-id>"]
    }
  }' \
  --region us-east-1
```

**Lambda function (starts export job):**

```python
import boto3
import json
import os

dataexchange = boto3.client('dataexchange')
s3 = boto3.client('s3')

DESTINATION_BUCKET = os.environ['DESTINATION_BUCKET']
DATA_SET_ID = os.environ['DATA_SET_ID']

def lambda_handler(event, context):
    # Extract revision info from EventBridge event
    revision_id = event['detail']['revision-id']
    data_set_id = event['detail']['data-set-id']

    # Get the revision's assets
    revision = dataexchange.get_revision(
        DataSetId=data_set_id,
        RevisionId=revision_id
    )

    # Create an export job
    job = dataexchange.create_job(
        type='EXPORT_ASSETS_TO_S3',
        details={
            'ExportAssetsToS3': {
                'DataSetId': data_set_id,
                'RevisionId': revision_id,
                'AssetDestination': {
                    'Bucket': DESTINATION_BUCKET,
                    'Key': f'auto-export/{revision_id}/'
                }
            }
        }
    )

    # Start the job
    dataexchange.start_job(JobId=job['Id'])

    return {
        'statusCode': 200,
        'body': json.dumps({
            'job_id': job['Id'],
            'revision_id': revision_id
        })
    }
```

**Deploy the Lambda + EventBridge target:**

```bash
# Add EventBridge target (Lambda)
aws events put-targets \
  --rule "DataExchangeAutoExport" \
  --targets '{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:dx-auto-export"}' \
  --region us-east-1

# Add Lambda permission for EventBridge
aws lambda add-permission \
  --function-name dx-auto-export \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region us-east-1
```

## Step 6 — Data set entitlement

Entitlements are the sharing mechanism for Data Exchange. They
control which AWS accounts can access a data set. This is NOT done
via IAM.

**Create an entitlement (provider shares with subscriber):**

```bash
aws dataexchange create-data-set \
  --asset-type S3_SNAPSHOT \
  --name "My Data Product" \
  --region us-east-1

# Entitlements are typically managed through the product listing
# in AWS Marketplace. When a subscriber subscribes to the product,
# the entitlement is automatically created.
```

**Entitlement verification:**

```bash
# Check if the subscriber account has access
aws dataexchange get-data-set \
  --data-set-id <data-set-id> \
  --region us-east-1
# The Origin field shows "PROVIDER" (you are the provider)
# or "SUBSCRIBER" (you subscribed to it)
```

**Key:** entitlements grant account-level access to the data set.
Within the account, IAM controls which principals can call Data
Exchange APIs. Both are needed: entitlement (what data you can
access) + IAM (what API calls you can make).

## Step 7 — Job creation (export, import)

Data Exchange supports two job types:

| Job type | Description | Direction |
|---|---|---|
| EXPORT_ASSETS_TO_S3 | Copy assets from Data Exchange to subscriber S3 | Provider → Subscriber |
| IMPORT_ASSETS_FROM_S3 | Copy assets from subscriber S3 to Data Exchange (for providers publishing data) | Subscriber → Provider |

**Export job (subscriber gets data):**

```bash
JOB_ID=$(aws dataexchange create-job \
  --type EXPORT_ASSETS_TO_S3 \
  --details '{
    "ExportAssetsToS3": {
      "DataSetId": "<data-set-id>",
      "RevisionId": "<revision-id>",
      "AssetDestination": {
        "Bucket": "my-subscriber-bucket",
        "Key": "data-exchange/exports/"
      }
    }
  }' \
  --query 'Id' --output text \
  --region us-east-1)

# Start the job
aws dataexchange start-job \
  --job-id "$JOB_ID" \
  --region us-east-1

# Poll for completion
aws dataexchange get-job \
  --job-id "$JOB_ID" \
  --region us-east-1
```

**Job states:**

| State | Description |
|---|---|
| PENDING | Job created, not yet started |
| IN_PROGRESS | Job running |
| COMPLETED | Job finished successfully |
| ERROR | Job failed (check errors array) |
| CANCELLED | Job cancelled |

**Import job (provider publishes data):**

```bash
JOB_ID=$(aws dataexchange create-job \
  --type IMPORT_ASSETS_FROM_S3 \
  --details '{
    "ImportAssetsFromS3": {
      "DataSetId": "<data-set-id>",
      "RevisionId": "<revision-id>",
      "AssetSources": [
        {
          "Bucket": "my-source-bucket",
          "Key": "data/new-dataset.csv"
        }
      ]
    }
  }' \
  --query 'Id' --output text \
  --region us-east-1)

aws dataexchange start-job \
  --job-id "$JOB_ID" \
  --region us-east-1
```

## Step 8 — Lake Formation integration

Lake Formation provides governed, fine-grained access to data
exported from Data Exchange. After exporting data to S3, register
the S3 location with Lake Formation and create a Data Catalog
table.

**Register S3 location with Lake Formation:**

```bash
aws lakeformation register-resource \
  --resource-arn "arn:aws:s3:::my-subscriber-bucket/data-exchange/" \
  --use-iam-role-access \
  --region us-east-1
```

**Create Data Catalog database and table:**

```bash
# Create database
aws glue create-database \
  --database-input '{"Name": "data_exchange_db"}' \
  --region us-east-1

# Create table (Crawler or manual)
aws glue create-table \
  --database-name data_exchange_db \
  --table-input '{
    "Name": "market_data",
    "StorageDescriptor": {
      "Columns": [
        {"Name": "date", "Type": "date"},
        {"Name": "symbol", "Type": "string"},
        {"Name": "price", "Type": "double"}
      ],
      "Location": "s3://my-subscriber-bucket/data-exchange/exports/",
      "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
      "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    },
    "TableType": "EXTERNAL_TABLE"
  }' \
  --region us-east-1
```

**Grant Lake Formation permissions:**

```bash
# Grant SELECT on table to a principal
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalystRole"}' \
  --permissions ["SELECT"] \
  --resource '{"Table": {"DatabaseName": "data_exchange_db", "Name": "market_data"}}' \
  --region us-east-1

# Grant with column-level (fine-grained)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalystRole"}' \
  --permissions ["SELECT"] \
  --permissions-with-grant-option [] \
  --resource '{"Table": {"DatabaseName": "data_exchange_db", "Name": "market_data", "ColumnWildcard": {}}}' \
  --region us-east-1
```

## Step 9 — Auto-export to S3 for BI tools

For BI tool consumption (QuickSight, Tableau, PowerBI), export
Data Exchange data to S3 in a BI-friendly format (CSV or Parquet)
and configure the BI tool to read from S3.

**Auto-export with Parquet partitioning:**

```python
import boto3
import json
import os

dataexchange = boto3.client('dataexchange')
athena = boto3.client('athena')

DESTINATION_BUCKET = os.environ['DESTINATION_BUCKET']

def lambda_handler(event, context):
    revision_id = event['detail']['revision-id']
    data_set_id = event['detail']['data-set-id']

    # Export to S3
    job = dataexchange.create_job(
        type='EXPORT_ASSETS_TO_S3',
        details={
            'ExportAssetsToS3': {
                'DataSetId': data_set_id,
                'RevisionId': revision_id,
                'AssetDestination': {
                    'Bucket': DESTINATION_BUCKET,
                    'Key': f'bi-exports/year={2026}/month={8}/'
                }
            }
        }
    )

    dataexchange.start_job(JobId=job['Id'])

    return {
        'statusCode': 200,
        'body': json.dumps({
            'job_id': job['Id'],
            's3_path': f's3://{DESTINATION_BUCKET}/bi-exports/year=2026/month=8/'
        })
    }
```

**QuickSight integration:**

Point QuickSight to the exported S3 data:
- Create a QuickSight data set pointing to
  `s3://my-subscriber-bucket/bi-exports/`
- Enable SPICE (Super-fast, Parallel, In-memory Calculation Engine)
  for fast queries
- Schedule SPICE refresh to match Data Exchange revision cadence

## Step 10 — API assets (REST endpoints)

API assets provide live REST endpoints as data products. Unlike S3
assets, API assets are NOT exported — they are accessed live through
the Data Exchange API gateway.

**Accessing an API asset:**

```python
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.credentials import get_credentials

# Data Exchange provides API signing keys for authentication
dataexchange = boto3.client('dataexchange')

# Get API asset details
asset = dataexchange.get_asset(
    DataSetId='<data-set-id>',
    RevisionId='<revision-id>',
    AssetId='<asset-id>'
)

# API assets require Data Exchange-specific authentication
# Use the Data Exchange API gateway URL from the asset details
api_url = asset['ApiDescription']['Url']

# Sign request with Data Exchange credentials
session = boto3.Session()
credentials = session.get_credentials()
# Make authenticated API call
response = requests.get(
    f'{api_url}/endpoint',
    auth=aws_auth  # Data Exchange signing
)
```

**Key differences from S3 assets:**

| Feature | S3_SNAPSHOT | API |
|---|---|---|
| Data freshness | Updated on revision publish | Live (real-time) |
| Export | Exported to subscriber S3 | NOT exported (accessed live) |
| Auto-export | YES (EventBridge rule) | NO (accessed on-demand) |
| Rate limiting | Unlimited (your S3) | Per-entitlement rate limits |
| Cost | Export + S3 storage | Per-API-call pricing |

## Step 11 — CloudWatch monitoring

Monitor Data Exchange job status and data freshness using
CloudWatch and EventBridge.

**CloudWatch metrics for Data Exchange:**

| Metric | Description |
|---|---|
| JobCount | Number of jobs by state |
| JobDuration | Job execution time |
| AssetCount | Number of assets per revision |
| RevisionAge | Time since last revision (custom metric) |

**EventBridge job completion rule:**

```bash
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
```

**CloudWatch alarm for stale data:**

```bash
# Alarm if no revision in 7 days (custom metric via Lambda)
aws cloudwatch put-metric-alarm \
  --alarm-name "DataExchangeStaleData" \
  --metric-name RevisionAge \
  --namespace DataExchange \
  --statistic Maximum \
  --period 86400 \
  --threshold 7 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions ["arn:aws:sns:us-east-1:123456789012:data-alerts"] \
  --region us-east-1
```

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **Data Exchange for Amazon S3 (2023-2024):** Direct S3 access for
  subscribed data products without manual export jobs. Subscribers
  can read directly from the provider's S3 bucket via Data Exchange-
  managed access, eliminating the need for export job orchestration.

- **Data Exchange API assets (2023-2024):** Providers can now offer
  REST API endpoints as data products. Subscribers access live data
  via authenticated API calls, enabling real-time data consumption
  without export latency.

- **Lake Formation fine-grained access control (2023-2024):**
  Enhanced integration between Data Exchange and Lake Formation
  enables column-level and row-level access control on exported
  data, supporting multi-tenant analytics with per-tenant visibility
  rules.

- **EventBridge auto-export templates (2023-2024):** AWS introduced
  pre-built EventBridge + Lambda templates for auto-export, reducing
  the setup overhead for subscribers who want automatic data
  delivery.

- **Data Exchange for API Gateway (2024-2025):** Providers can
  monetize API endpoints through Data Exchange, with built-in rate
  limiting, usage tracking, and per-subscriber authentication.

- **CloudWatch dashboards for Data Exchange (2024-2025):** Pre-built
  CloudWatch dashboard templates for monitoring export job health,
  revision freshness, and data volume across subscriptions.

- **Step Functions integration for multi-step exports (2024-2025):**
  Step Functions state machines for orchestrating multi-step export
  pipelines (export → transform → load into Redshift/Athena),
  replacing custom Lambda orchestration.

## NEVER do these things

1. **NEVER use IAM policies as the sharing mechanism.** Entitlements
   control which accounts can access a data set, NOT IAM. IAM
   controls which principals within an account can call Data Exchange
   APIs. Both are needed, but only entitlements grant data set
   access.

2. **NEVER assume auto-export exists by default.** Without an
   EventBridge rule + Lambda, new revisions sit in Data Exchange
   and are never delivered to the subscriber's S3. Auto-export must
   be explicitly configured.

3. **NEVER treat export jobs as synchronous.** Export jobs are
   asynchronous and can take minutes to hours. Poll job status or
   use EventBridge to trigger downstream processing only after
   COMPLETED status.

4. **NEVER try to export API assets to S3.** API assets are accessed
   live through the Data Exchange API gateway. S3 auto-export rules
   do not apply to API assets.

5. **NEVER finalize a revision before all assets are added.**
   Finalization is a one-way operation. Once finalized, assets
   cannot be added, modified, or removed. Verify asset completeness
   before finalizing.

6. **NEVER skip the destination S3 bucket IAM policy.** The export
   job assumes a role that needs `s3:PutObject` on the destination
   bucket. Without this, the job fails silently (state: ERROR with
   an IAM error in the details).

7. **NEVER configure Lake Formation grants without first exporting
   data to S3.** Lake Formation governs data in the Data Catalog,
   which reads from S3. The data must be exported from Data Exchange
   to S3 before LF grants can apply.

8. **NEVER assume Redshift snapshot assets export to S3.**
   REDSHIFT_SNAPSHOT assets are restored to a Redshift cluster,
   not exported to S3. The subscriber must have a Redshift cluster
   to consume these assets.

9. **NEVER hardcode revision IDs in downstream pipelines.** Revision
   IDs change with each new revision. Use EventBridge events or the
   ListRevisions API to dynamically discover the latest revision.

10. **NEVER skip CloudWatch monitoring for production data
    pipelines.** Set up alarms for stale data (no revision in N
    days), job failures, and export duration anomalies. Data
    freshness SLAs require proactive monitoring.

## Output format

```text
DATA_EXCHANGE: <data-set-id> (subscription: <subscription-id>) → S3: <destination-bucket>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Subscription: <subscription-id> — ACTIVE
  [✓|✗] Data set: <data-set-id> — <asset-type> (S3_SNAPSHOT | API | REDSHIFT_SNAPSHOT | QUERY)
  [✓|✗] Revision: <revision-id> — FINALIZED
  [✓|✗] Assets: <count> assets of type <asset-type>
  [✓|✗] Destination S3 bucket: <bucket-name> — exists
  [✓|✗] IAM role: export job role with s3:PutObject on <bucket> — configured
  [✓|✗] Export job: <job-id> — type EXPORT_ASSETS_TO_S3
  [✓|✗] Auto-export: EventBridge rule "<rule-name>" → Lambda "<function-name>" — configured | not configured
  [✓|✗] Entitlement: target account <account-id> — entitled | not required
  [✓|✗] Lake Formation: S3 location registered, Data Catalog table "<table-name>" — configured | not required
  [✓|✗] API asset access: <api-url> — live access via Data Exchange gateway | not applicable
  [✓|✗] CloudWatch monitoring: job status alarm + stale data alarm — configured
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws dataexchange get-data-set --data-set-id <data-set-id> --region <region>
  aws dataexchange get-job --job-id <job-id> --region <region>
  aws events describe-rule --name <rule-name> --region <region>
```

### Worked example — S3 auto-export with Lake Formation

```text
DATA_EXCHANGE: ds-abc12345 (subscription: sub-def67890) → S3: my-analytics-bucket
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Subscription: sub-def67890 — ACTIVE
  [✓] Data set: ds-abc12345 — S3_SNAPSHOT (CSV files)
  [✓] Revision: r-ghi11122 — FINALIZED
  [✓] Assets: 5 assets of type S3_SNAPSHOT
  [✓] Destination S3 bucket: my-analytics-bucket — exists
  [✓] IAM role: dx-export-role with s3:PutObject on my-analytics-bucket — configured
  [✓] Export job: j-xyz33344 — type EXPORT_ASSETS_TO_S3
  [✓] Auto-export: EventBridge rule "DataExchangeAutoExport" → Lambda "dx-auto-export" — configured
  [✓] Entitlement: not required (same account)
  [✓] Lake Formation: S3 location registered, Data Catalog table "market_data" — configured
  [✓] API asset access: not applicable
  [✓] CloudWatch monitoring: job status alarm + stale data alarm (7 days) — configured
  [✓] Tags: Environment=production, DataSource=market-data
VERIFICATION_COMMANDS:
  aws dataexchange get-data-set --data-set-id ds-abc12345 --region us-east-1
  aws dataexchange get-job --job-id j-xyz33344 --region us-east-1
  aws events describe-rule --name DataExchangeAutoExport --region us-east-1
```

## Error handling

### Export job fails with ERROR state
- The IAM role may lack `s3:PutObject` on the destination bucket.
  Check the job errors array for IAM-related messages. Verify the
  export job's role has the correct S3 permissions.

### Auto-export not triggering on new revisions
- The EventBridge rule may not match the event pattern. Verify the
  rule's event pattern includes the correct data-set-id. Check
  CloudWatch Metrics for EventBridge invocations. Ensure the Lambda
  function has permission to be invoked by EventBridge.

### Revision not visible to subscriber
- The revision may not be finalized. Only FINALIZED revisions are
  visible to subscribers. Verify revision state via
  `get-revision`. If the revision is still DRAFT, the provider must
  finalize it.

### Lake Formation table not accessible
- The S3 location may not be registered with Lake Formation. Run
  `register-resource` for the S3 path. Verify the Data Catalog
  table points to the correct S3 location. Check LF grants for the
  principal.

### API asset authentication fails
- The API signing key may be expired. Regenerate the Data Exchange
  API key via the console or API. Verify the API URL from the asset
  details. Ensure rate limits are not exceeded.

## Domain

AWS CloudOps / AWS Data Exchange Data Set Subscription, Export, and
Governed Analytics.

## AWS documentation

- **Data Exchange User Guide** — https://docs.aws.amazon.com/data-exchange/latest/userguide/what-is.html
- **Subscribing to data products** — https://docs.aws.amazon.com/data-exchange/latest/userguide/subscribe-to-data-sets.html
- **Exporting assets** — https://docs.aws.amazon.com/data-exchange/latest/userguide/export-jobs.html
- **Auto-export** — https://docs.aws.amazon.com/data-exchange/latest/userguide/auto-export.html
- **Entitlements** — https://docs.aws.amazon.com/data-exchange/latest/userguide/entitlements.html
- **API assets** — https://docs.aws.amazon.com/data-exchange/latest/userguide/api-assets.html
- **Lake Formation integration** — https://docs.aws.amazon.com/data-exchange/latest/userguide/lake-formation.html
- **Job lifecycle** — https://docs.aws.amazon.com/data-exchange/latest/userguide/jobs.html
- **EventBridge events** — https://docs.aws.amazon.com/data-exchange/latest/userguide/event-bridge.html
- **CloudWatch monitoring** — https://docs.aws.amazon.com/data-exchange/latest/userguide/monitoring.html
