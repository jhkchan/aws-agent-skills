# Entitlements and Lake Formation — Data Exchange Dataset Deployer

Deep reference on entitlements (the sharing mechanism for Data
Exchange, NOT IAM), cross-account data sharing flows, Lake Formation
integration for governed fine-grained access, and CloudWatch
monitoring for job status and data freshness. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Entitlements: the sharing mechanism

### Why entitlements, not IAM

Data Exchange uses entitlements to control which AWS accounts can
access which data sets. This is fundamentally different from IAM:

```text
IAM:        "Principal Z can call dataexchange:StartJob"
            → Controls API access within an account

Entitlement: "Account X is entitled to data set Y"
              → Controls data set access across accounts

Both are needed:
  1. Entitlement grants account-level access to the data set
  2. IAM grants principal-level access to call Data Exchange APIs
  3. Together: the principal in the entitled account can export the data
```

Adding an IAM bucket policy for the receiving account does NOT grant
access to the Data Exchange data set. The provider must create an
entitlement.

### How entitlements are created

Entitlements are typically managed through the AWS Marketplace
product listing:

```text
Provider publishes a data product in AWS Marketplace
  ↓
Subscriber finds and subscribes to the product
  ↓
AWS Marketplace creates the entitlement automatically
  ↓
Subscriber account can now access the data set via Data Exchange API

For direct (non-marketplace) sharing:
  Provider creates the data set
  ↓
  Provider creates an entitlement for a specific AWS account
  ↓
  Receiving account accesses the data set
```

### Verifying entitlements

```bash
# As the subscriber, check if you have access to a data set
aws dataexchange get-data-set \
  --data-set-id <data-set-id> \
  --region us-east-1

# The Origin field indicates:
#   PROVIDER  → you are the provider (you own this data set)
#   SUBSCRIBER → you subscribed to this data set (entitled)

# List all data sets you have access to
aws dataexchange list-data-sets \
  --region us-east-1 \
  --query 'DataSets[?Origin==`SUBSCRIBER`]'
```

### Cross-account sharing flow

```text
Provider account (123456789012):
  1. Creates data set ds-share789
  2. Publishes to AWS Marketplace (or direct entitlement)
  3. Creates entitlement for account 999999999999

Subscriber account (999999999999):
  1. Subscribes to the product (accepts entitlement)
  2. Verifies access: get-data-set shows Origin=SUBSCRIBER
  3. Creates export job to their own S3 bucket
  4. Data flows: Data Exchange → subscriber's S3 bucket

IAM roles needed:
  Provider account:
    - dataexchange:CreateJob (IMPORT, to publish data)
    - s3:GetObject (to read source data for import)

  Subscriber account:
    - dataexchange:CreateJob, StartJob, GetJob (to export)
    - s3:PutObject (to write exported data to their bucket)
    - iam:PassRole (to pass the export role to the job)
```

## Lake Formation integration

### When to use Lake Formation

Lake Formation provides governed, fine-grained access control over
data exported from Data Exchange. Use LF when:

- Multiple teams need different levels of access to the same data.
- Column-level or row-level access control is required.
- Audit logging of data access is needed.
- Integration with Athena, Redshift Spectrum, or EMR for querying.

### Lake Formation setup for Data Exchange data

```text
Step 1: Export data from Data Exchange to S3
Step 2: Register the S3 location with Lake Formation
Step 3: Create a Data Catalog database and table over the S3 data
Step 4: Grant LF permissions (SELECT, ALTER, etc.) to principals
Step 5: Query via Athena, Redshift Spectrum, or EMR
```

### Step-by-step Lake Formation configuration

**Step 1: Export data (already covered in main SKILL.md)**

**Step 2: Register S3 location**

```bash
aws lakeformation register-resource \
  --resource-arn "arn:aws:s3:::my-subscriber-bucket/data-exchange/" \
  --role-arn "arn:aws:iam::123456789012:role/LFServiceRole" \
  --region us-east-1
```

**Step 3: Create Data Catalog database and table**

```bash
# Create database
aws glue create-database \
  --database-input '{"Name": "data_exchange_db"}' \
  --region us-east-1

# Use a Glue Crawler to auto-discover schema
aws glue create-crawler \
  --name dx-crawler \
  --role AWSGlueServiceRole \
  --database-name data_exchange_db \
  --targets '{"S3Targets": [{"Path": "s3://my-subscriber-bucket/data-exchange/"}]}' \
  --region us-east-1

aws glue start-crawler \
  --name dx-crawler \
  --region us-east-1

# Or create the table manually (see main SKILL.md)
```

**Step 4: Grant Lake Formation permissions**

```bash
# Grant SELECT on the entire table
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalystRole"}' \
  --permissions ["SELECT"] \
  --resource '{"Table": {"DatabaseName": "data_exchange_db", "Name": "market_data"}}' \
  --region us-east-1

# Grant SELECT on specific columns only (column-level access)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/RestrictedAnalyst"}' \
  --permissions ["SELECT"] \
  --resource '{
    "TableWithColumns": {
      "DatabaseName": "data_exchange_db",
      "Name": "market_data",
      "ColumnNames": ["date", "symbol", "volume"]
    }
  }' \
  --region us-east-1

# Grant with row-level filter (LF tag-based or named range)
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/RegionAnalyst"}' \
  --permissions ["SELECT"] \
  --resource '{"Table": {"DatabaseName": "data_exchange_db", "Name": "market_data"}}' \
  --region us-east-1
# Combine with a row-level security filter
```

**Step 5: Query via Athena**

```bash
# Run a query (Athena uses Lake Formation for access control)
aws athena start-query-execution \
  --query-string "SELECT * FROM data_exchange_db.market_data LIMIT 10" \
  --query-execution-context '{"Database": "data_exchange_db"}' \
  --result-configuration '{"OutputLocation": "s3://my-query-results/athena/"}' \
  --region us-east-1
```

### Lake Formation + auto-export refresh

When auto-export delivers new data, the Data Catalog table needs to
be refreshed to pick up new partitions or schema changes:

```python
import boto3

glue = boto3.client('glue')

def lambda_handler(event, context):
    """Triggered after Data Exchange export job completes."""
    
    # Trigger Glue Crawler to update the Data Catalog
    glue.start_crawler(Name='dx-crawler')
    
    return {'statusCode': 200, 'body': 'Crawler started'}
```

## CloudWatch monitoring

### Key metrics to monitor

| Metric | Source | Description |
|---|---|---|
| JobState | Data Exchange / EventBridge | Export job state changes |
| JobDuration | CloudWatch custom | Time from job start to completion |
| RevisionAge | CloudWatch custom | Days since last revision |
| ExportVolume | CloudWatch custom | Data volume per export (bytes) |
| AutoExportInvocations | Lambda | Auto-export Lambda invocations |
| AutoExportErrors | Lambda | Auto-export Lambda errors |

### Stale data alarm

```bash
# Custom metric: days since last revision
# Published by a daily Lambda that checks ListRevisions

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

### Job failure alarm

```bash
# Alarm on export job failures via EventBridge
aws events put-rule \
  --name "DataExchangeJobFailed" \
  --event-pattern '{
    "source": ["aws.dataexchange"],
    "detail-type": ["Job Status Change"],
    "detail": {
      "state": ["ERROR"]
    }
  }' \
  --region us-east-1

aws events put-targets \
  --rule "DataExchangeJobFailed" \
  --targets '[{"Id": "1", "Arn": "arn:aws:sns:us-east-1:123456789012:dx-alerts"}]' \
  --region us-east-1
```

### Daily freshness check Lambda

```python
import boto3
import json
from datetime import datetime, timezone, timedelta

dataexchange = boto3.client('dataexchange')
cloudwatch = boto3.client('cloudwatch')

DATA_SET_ID = os.environ['DATA_SET_ID']

def lambda_handler(event, context):
    """Daily check: emit RevisionAge metric."""
    
    # Get the latest revision
    revisions = dataexchange.list_data_set_revisions(
        DataSetId=DATA_SET_ID
    )
    
    if not revisions.get('Revisions'):
        # No revisions at all — very stale
        age_days = 999
    else:
        latest = revisions['Revisions'][0]
        # Parse the revision creation timestamp
        created = latest.get('CreatedAt', datetime.now(timezone.utc))
        if isinstance(created, str):
            created = datetime.fromisoformat(created.replace('Z', '+00:00'))
        age_days = (datetime.now(timezone.utc) - created).days
    
    # Emit metric
    cloudwatch.put_metric_data(
        Namespace='DataExchange',
        MetricData=[{
            'MetricName': 'RevisionAge',
            'Value': age_days,
            'Unit': 'Count'
        }]
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'revision_age_days': age_days})
    }
```

## Terraform Lake Formation example

```hcl
# Register S3 location with Lake Formation
resource "aws_lakeformation_resource" "dx_data" {
  arn = "arn:aws:s3:::my-subscriber-bucket/data-exchange/"
}

# Grant permissions to analyst role
resource "aws_lakeformation_permissions" "analyst" {
  principal = "arn:aws:iam::123456789012:role/AnalystRole"
  
  permissions = ["SELECT"]
  
  table {
    database_name = aws_glue_catalog_table.dx_table.database_name
    name          = aws_glue_catalog_table.dx_table.name
  }
}
```

## Step 6 — entitlement creation and verification commands (moved from SKILL.md)



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



## Step 8 — Lake Formation integration commands (moved from SKILL.md)



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



## Step 11 — CloudWatch and EventBridge monitoring commands (moved from SKILL.md)



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


