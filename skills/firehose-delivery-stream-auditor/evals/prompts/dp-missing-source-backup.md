# Eval prompt: dp-missing-source-backup

Audit the following Kinesis Data Firehose delivery stream for security
exposure. Emit the standard VERDICT block (STREAM, VERDICT, REASON,
FINDINGS, REMEDIATION).

Delivery stream name: firehose-dp-missing-source-backup
ARN: arn:aws:firehose:us-east-1:111111111111:deliverystream/firehose-dp-missing-source-backup
DeliveryStreamStatus: ACTIVE
DeliveryStreamType: DirectPut
LoggingConfig: {Enabled: true, LogGroupName: /aws/kinesisfirehose/firehose-dp-missing-source-backup}

ExtendedS3DestinationConfiguration:

```json
{
  "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
  "BucketARN": "arn:aws:s3:::firehose-delivery-prod",
  "Prefix": "events/!{partitionKeyFromQuery:tenant}/",
  "ErrorOutputPrefix": "errors/!{firehose:errorType}/!{timestamp:yyyy-MM-dd}/",
  "BufferingHints": {"SizeInMBs": 64, "IntervalInSeconds": 300},
  "CompressionFormat": "UNCOMPRESSED",
  "EncryptionConfiguration": {
    "KMSEncryptionConfig": {
      "AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"
    }
  },
  "S3BackupMode": "Disabled",
  "DynamicPartitioningConfiguration": {"Enabled": true, "RetryDuration": 0},
  "ProcessingConfiguration": {
    "Enabled": true,
    "Processors": [
      {
        "Type": "MetadataExtraction",
        "Parameters": [
          {"ParameterName": "JsonParsingEngine", "ParameterValue": "JQ-1.6"},
          {"ParameterName": "MetaDataExtractionQuery", "ParameterValue": ".tenant"}
        ]
      }
    ]
  }
}
```
