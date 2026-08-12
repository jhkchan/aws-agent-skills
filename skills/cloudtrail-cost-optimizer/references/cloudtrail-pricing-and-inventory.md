# CloudTrail Pricing and Inventory Reference

Supplementary reference for the CloudTrail Cost Optimizer skill. Loaded
on-demand when detailed pricing math, trail inventory CLI sequences,
event selector syntax, KMS key policy templates, or S3 lifecycle JSON
are needed.

## CloudTrail pricing (us-east-1, 2026, USD)

### Per-event pricing

| Event category | $/100k events | Notes |
|---|---|---|
| Management events (first trail per region) | $0.00 (free) | Includes IAM, STS, EC2 control plane, etc. |
| Management events (additional trail per region) | $2.00 | The #1 cost trap for multi-trail accounts |
| S3 data events | $0.10 | Per 100,000 S3 API calls (GetObject, PutObject, etc.) |
| Lambda data events | $0.10 | Per 100,000 Lambda invocations |
| DynamoDB data events | $0.10 | Per 100,000 DynamoDB API calls |
| Insights events analyzed | $0.50 | Per 100,000 management events analyzed (not per finding) |

### CloudTrail Lake pricing

| Dimension | Rate | Notes |
|---|---|---|
| Ingestion | $0.75/GB-month | One-time cost at ingest |
| Retention storage | $0.023/GB-month | Equivalent to S3 Standard |
| Queries | $0.00 (free) | Athena-style federation to EDS |

### S3 storage classes (for log buckets)

| Class | $/GB-month | Retrieval latency | Notes |
|---|---|---|---|
| Standard | $0.023 | ms | Default for new objects |
| Intelligent-Tiering | $0.023 (frequent) / $0.0025 (archive) | ms | Auto-tiering; small monitoring fee |
| Glacier Instant Retrieval | $0.004 | ms | 83% cheaper than Standard, ms latency |
| Glacier Flexible Retrieval | $0.0036 | 1-5 min | For archives < 1 query/quarter |
| Deep Archive | $0.00099 | 12 h | Lowest cost; long restore |

### Per-request pricing

| Operation | $/1k requests | Notes |
|---|---|---|
| S3 PUT | $0.005 | Each log file is a PUT |
| S3 GET | $0.0004 | Digest validation reads |
| KMS GenerateDataKey | $0.03/10k | Per CloudTrail log file (one call) |
| SNS publish | $0.50/1M | Per-trail topic |

## Trail inventory CLI

### List all trails (account-scoped)

```bash
aws cloudtrail describe-trails --include-shadow-trails \
  --query 'trailList[*].{
    Name: Name,
    IsOrg: IsOrganizationTrail,
    IsMultiRegion: IsMultiRegionTrail,
    KMS: KmsKeyId,
    S3: S3BucketName,
    LogsLogGroup: CloudWatchLogsLogGroupArn,
    Status: Status
  }' --output table
```

### Per-trail detail (event selectors + Insights)

```bash
TRAIL_NAME=aws-organizational-trail

aws cloudtrail get-event-selectors --trail-name $TRAIL_NAME
aws cloudtrail get-insights-selectors --trail-name $TRAIL_NAME
aws cloudtrail get-trail --name $TRAIL_NAME --query 'Trail.{Status: Status, LogFileValidationEnabled: LogFileValidationEnabled, IncludeGlobalServiceEvents: IncludeGlobalServiceEvents}'
```

### Organization context

```bash
aws organizations describe-organization \
  --query 'Organization.{ManagementAcct: MasterAccountId, Status: FeatureSet}'

aws organizations list-accounts \
  --query 'Accounts[*].{Id: Id, Name: Name, Status: Status}' \
  --output table
```

### S3 log bucket inventory

```bash
BUCKET=org-cloudtrail-logs-us-east-1

aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET
aws s3api get-bucket-versioning --bucket $BUCKET
aws s3api get-bucket-location --bucket $BUCKET

# Storage size (CloudWatch metric)
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=$BUCKET Name=StorageType,Value=StandardStorage \
  --start-time $(date -u -d '-30 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 86400 --statistics Average --output json
```

### CloudTrail Lake EDS inventory

```bash
aws cloudtrail list-event-data-stores \
  --query 'EventDataStores[*].{
    Name: Name,
    Id: EventDataStoreId,
    Status: Status,
    Retention: RetentionPeriod,
    SizeGB: TerminationProtection
  }' --output table
```

## Event selector syntax

### Basic event selectors (legacy but supported)

```json
[
  {
    "ReadWriteType": "All",
    "IncludeManagementEvents": true,
    "DataResources": [
      {
        "Type": "AWS::S3::Object",
        "Values": [
          "arn:aws:s3:::financial-records/",
          "arn:aws:s3:::pii-data/"
        ]
      }
    ]
  }
]
```

Limitations: basic selectors can't combine multiple resource types in
one selector, and don't support `readOnly` filtering at the field level.

### Advanced event selectors (recommended)

```json
[
  {
    "Name": "ManagementEvents",
    "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Management"]}
    ]
  },
  {
    "Name": "CuratedS3DataEvents",
    "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Data"]},
      {"Field": "resources.type", "Equals": ["AWS::S3::Object"]},
      {"Field": "resources.ARN", "StartsWith": [
        "arn:aws:s3:::financial-records/",
        "arn:aws:s3:::pii-data/",
        "arn:aws:s3:::transaction-logs/"
      ]}
    ]
  },
  {
    "Name": "ReadOnlyLambdaInvocations",
    "FieldSelectors": [
      {"Field": "eventCategory", "Equals": ["Data"]},
      {"Field": "resources.type", "Equals": ["AWS::Lambda::Function"]},
      {"Field": "readOnly", "Equals": ["false"]}
    ]
  }
]
```

Capabilities: multi-resource-type selectors, ARN prefix matching,
`readOnly` field filtering (eliminates read-side noise from
high-volume S3 GETs).

## KMS key policy template (shared CMK across trails)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Enable IAM User Permissions",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::MANAGEMENT_ACCT:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "AllowCloudTrailToUseKey",
      "Effect": "Allow",
      "Principal": {"Service": "cloudtrail.amazonaws.com"},
      "Action": ["kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:SourceArn": "arn:aws:cloudtrail:us-east-1:MANAGEMENT_ACCT:trail/aws-organizational-trail"
        }
      }
    },
    {
      "Sid": "AllowS3ToDecryptLogFiles",
      "Effect": "Allow",
      "Principal": {"Service": "s3.amazonaws.com"},
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```

## S3 lifecycle policy (CloudTrail-optimized)

```json
{
  "Rules": [
    {
      "Id": "cloudtrail-lifecycle",
      "Status": "Enabled",
      "Filter": {"Prefix": "AWSLogs/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "INTELLIGENT_TIERING"},
        {"Days": 90, "StorageClass": "GLACIER_IR"},
        {"Days": 180, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 365},
      "NoncurrentVersionTransitions": [
        {"NoncurrentDays": 30, "StorageClass": "GLACIER_IR"},
        {"NoncurrentDays": 90, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "NoncurrentVersionExpiration": {"NoncurrentDays": 180}
    }
  ]
}
```

Notes:
- `Filter: AWSLogs/` scopes the rule to CloudTrail's prefix only.
- Noncurrent version rules clean up `S3 Object Lock` retained-but-
  superseded versions.
- Expiration at 365 days matches a typical compliance retention SLA;
  adjust to your regulatory requirement.

## Athena partition projection DDL

```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
  eventversion STRING,
  useridentity STRUCT<
    type: STRING,
    principalid: STRING,
    arn: STRING,
    accountid: STRING,
    accesskeyid: STRING,
    sessioncontext: STRUCT<
      attributes: STRUCT<mfaauthenticated: STRING, creationdate: STRING>,
      sessionissuer: STRUCT<type: STRING, principalid: STRING, arn: STRING, accountid: STRING>
    >
  >,
  eventtime STRING,
  eventsource STRING,
  eventname STRING,
  awsregion STRING,
  sourceipaddress STRING,
  useragent STRING,
  errorcode STRING,
  errormessage STRING,
  requestparameters STRING,
  responseelements STRING,
  requestid STRING,
  eventid STRING,
  resources ARRAY<STRUCT<arn: STRING, accountid: STRING, type: STRING>>,
  eventtype STRING,
  apiversion STRING,
  readonly STRING,
  recipientaccountid STRING
)
PARTITIONED BY (
  accountid_hive STRING,
  region_hive STRING,
  year_hive STRING,
  month_hive STRING,
  day_hive STRING
)
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://org-cloudtrail-logs-us-east-1/AWSLogs/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.accountid_hive.type' = 'enum',
  'projection.accountid_hive.values' = '111111111111,222222222222',
  'projection.region_hive.type' = 'enum',
  'projection.region_hive.values' = 'us-east-1,us-west-2,eu-west-1',
  'projection.year_hive.type' = 'date',
  'projection.year_hive.range' = '2024-01-01,NOW',
  'projection.year_hive.format' = 'yyyy',
  'projection.month_hive.type' = 'date',
  'projection.month_hive.range' = '2024-01-01,NOW',
  'projection.month_hive.format' = 'MM',
  'projection.day_hive.type' = 'date',
  'projection.day_hive.range' = '2024-01-01,NOW',
  'projection.day_hive.format' = 'dd',
  'storage.location.template' = 's3://org-cloudtrail-logs-us-east-1/AWSLogs/${accountid_hive}/CloudTrail/${region_hive}/${year_hive}/${month_hive}/${day_hive}'
);
```

Cost-saving pattern:
- Without projection: a single exploratory query scans ALL historical
  logs (potentially TB-scale at $5/TB scanned).
- With projection: partition pruning is computed client-side (no Glue
  Data Catalog partitions needed); only matching partitions are scanned.

## Regional pricing multipliers (representative)

| Region | Multiplier vs us-east-1 | Notes |
|---|---|---|
| us-east-1 | 1.00 | Baseline |
| us-west-2 | 1.00 | Same pricing tier |
| eu-west-1 | 1.10 | Slight uplift |
| ap-south-1 | 1.05 | Mumbai |
| ap-southeast-2 | 1.15 | Sydney |
| sa-east-1 | 1.20 | Sao Paulo (highest) |

For multi-region orgs, the pricing matrix should be re-stated per trail
region; the global rollup multiplies each region's spend by its
multiplier.

## Cost calculation worked example

```
Inputs:
  Org trail exists, 10 redundant member trails
  Management event volume: 1.4M log files/month per trail
  S3 Standard storage for duplicates: 200 GB
  KMS keys: 11 (one per extra trail)
  SNS topics: 11
  Region: us-east-1

Duplicate-trail monthly cost:
  S3 PUT: 10 × 1,400,000 × $0.005/1000 = $70.00
  S3 storage: 200 GB × $0.023 = $4.60
  KMS requests: 10 × 1,400,000 × $0.03/10000 = $42.00
  KMS key monthly: 10 × $1.00 = $10.00
  SNS: 10 × 1,400,000 × $0.50/1M = $7.00
  Total: $133.60/month in duplicate-trail overhead

Projected (org trail only):
  All above = $0 for the duplicate dimension
  Monthly saving: $133.60
  Annual saving: $1,603.20
```

## AWS documentation

- CloudTrail pricing — https://aws.amazon.com/cloudtrail/pricing/
- CloudTrail event selectors — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/logging-data-events-with-cloudtrail.html
- S3 storage classes — https://aws.amazon.com/s3/storage-classes/
- Athena partition projection — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
