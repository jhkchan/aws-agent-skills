# Firehose S3 Export Pipeline Reference

Supplementary reference for the Log Retention Automator skill. Use
when designing a Kinesis Firehose-to-S3 archival pipeline for
CloudWatch Logs, including IAM roles, S3 lifecycle policies, Athena
table DDL, and cost analysis.

## Architecture overview

```
CloudWatch Logs Group
  └── Subscription Filter (destination: Firehose)
        └── Kinesis Firehose Delivery Stream
              ├── Buffer: 5 MB / 300 seconds
              ├── Compression: GZIP
              └── S3 Destination
                    ├── Prefix: year=YYYY/month=MM/day=DD/
                    ├── Lifecycle: Standard → Glacier (90d) → Deep Archive (180d)
                    └── Encryption: SSE-KMS
```

## IAM roles

### Firehose service role

Trust policy (`firehose-trust.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "firehose.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions policy (`firehose-s3-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:AbortMultipartUpload", "s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket", "s3:ListBucketMultipartUploads", "s3:PutObject"],
      "Resource": ["arn:aws:s3:::com-company-log-archive-*", "arn:aws:s3:::com-company-log-archive-*/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
      "Resource": "arn:aws:kms:us-east-1:111111111111:key/kms-key-id",
      "Condition": {"StringEquals": {"kms:ViaService": "s3.us-east-1.amazonaws.com"}}
    },
    {
      "Effect": "Allow",
      "Action": ["logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/kinesisfirehose/*"
    }
  ]
}
```

### CloudWatch Logs to Firehose role

Trust policy (`cwlogs-firehose-trust.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "logs.us-east-1.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["firehose:PutRecord", "firehose:PutRecordBatch"],
      "Resource": "arn:aws:firehose:us-east-1:111111111111:deliverystream/log-archive-*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:CreateServiceLinkedRole"],
      "Resource": "*",
      "Condition": {"StringLike": {"iam:AWSServiceName": "logs.us-east-1.amazonaws.com"}}
    }
  ]
}
```

## Delivery stream creation

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name log-archive-prod \
  --delivery-stream-type DirectPut \
  --extended-s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::111111111111:role/FirehoseS3Role",
    "BucketARN": "arn:aws:s3:::com-company-log-archive-prod",
    "Prefix": "firehose/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "ErrorOutputPrefix": "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
    "CompressionFormat": "GZIP",
    "EncryptionConfiguration": {
      "KMSEncryptionConfig": {"AWSKMSKeyARN": "arn:aws:kms:us-east-1:111111111111:key/kms-key-id"}
    },
    "CloudWatchLoggingOptions": {
      "Enabled": true,
      "LogGroupName": "/aws/kinesisfirehose/log-archive-prod",
      "LogStreamName": "DestinationDelivery"
    },
    "ProcessingConfiguration": {
      "Enabled": true,
      "Processors": [{
        "Type": "MetadataExtraction",
        "Parameters": [
          {"ParameterName": "JsonParsingEngine", "ParameterValue": "JQ-1.6"},
          {"ParameterName": "MetadataExtractionQuery", "ParameterValue": "{logSourceType:.logSourceType, accountId:.accountId}"}
        ]
      }]
    },
    "S3BackupMode": "Enabled",
    "S3BackupConfiguration": {
      "RoleARN": "arn:aws:iam::111111111111:role/FirehoseS3Role",
      "BucketARN": "arn:aws:s3:::com-company-log-archive-backup",
      "Prefix": "backup/",
      "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
      "CompressionFormat": "GZIP"
    }
  }'
```

## Subscription filter wiring

```bash
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/compliance-critical-function \
  --filter-name archive-to-firehose \
  --filter-pattern "" \
  --destination-arn "arn:aws:firehose:us-east-1:111111111111:deliverystream/log-archive-prod" \
  --role-arn "arn:aws:iam::111111111111:role/CWLogsToFirehoseRole" \
  --distribution "ByLogStream"
```

## S3 lifecycle policy

```json
{
  "Rules": [
    {
      "Id": "log-archive-lifecycle",
      "Status": "Enabled",
      "Filter": {"Prefix": "firehose/"},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"},
        {"Days": 180, "StorageClass": "DEEP_ARCHIVE"}
      ],
      "Expiration": {"Days": 3653}
    }
  ]
}
```

Apply:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket com-company-log-archive-prod \
  --lifecycle-configuration file://lifecycle.json
```

## Athena table DDL for archived logs

```sql
CREATE EXTERNAL TABLE IF NOT EXISTS cloudwatch_logs_archive (
  timestamp string,
  message string,
  logstream string
)
PARTITIONED BY (
  year string,
  month string,
  day string,
  loggroup string
)
STORED AS INPUTFORMAT 'com.amazon.emrs.cloudwatch.LogInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://com-company-log-archive-prod/firehose/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.year.type' = 'integer',
  'projection.year.range' = '2024,2030',
  'projection.month.type' = 'integer',
  'projection.month.range' = '1,12',
  'projection.day.type' = 'integer',
  'projection.day.range' = '1,31',
  'projection.loggroup.type' = 'injected',
  'storage.location.template' = 's3://com-company-log-archive-prod/firehose/year=${year}/month=${month}/day=${day}/'
);
```

## Cost crossover analysis

CloudWatch Logs storage: $0.03/GB/month
S3 Standard: $0.023/GB/month
S3 Glacier: $0.0036/GB/month
S3 Deep Archive: $0.00099/GB/month
Firehose delivery: $0.029/GB processed
Typical GZIP compression on logs: ~30% of original size

| Scenario | Daily ingest | Retention | CloudWatch-only | CloudWatch(90d) + S3(Glacier) | Savings |
|---|---|---|---|---|---|
| Small app | 1 GB/day | 1 year | $189/mo ingest + $11/mo storage = $200 | $15/mo ingest + $15/mo CW + $5/mo Firehose + $2/mo S3 = $37 | 82% |
| Medium fleet | 10 GB/day | 1 year | $1,500/mo + $110/mo = $1,610 | $150/mo + $15/mo + $9/mo + $11/mo = $185 | 89% |
| Compliance logs | 25 GB/day | 7 years | $3,750/mo + $770/mo = $4,520 | $375/mo + $15/mo + $22/mo + $25/mo = $437 | 90% |

**Break-even crossover:** For retention periods > 90 days, the
CloudWatch + S3 combo is cheaper once the daily ingest exceeds
~0.5 GB/day. Below that threshold, CloudWatch-only with the
appropriate tier is simpler.

## Verification checklist

- [ ] Firehose delivery stream status is ACTIVE
- [ ] Subscription filter destination ARN matches Firehose stream
- [ ] S3 bucket has lifecycle policy applied
- [ ] KMS key policy allows Firehose service role
- [ ] CloudWatch Logs backup for Firehose errors is enabled
- [ ] S3 backup mode enabled (for delivery error recovery)
- [ ] Athena partition projection configured for year/month/day
- [ ] Test query: verify logs arrive in S3 within 5 minutes of ingest
- [ ] DLQ configured on the Lambda if Lambda-to-Firehose is used
- [ ] Cross-account: destination role trusts source account's logs service
