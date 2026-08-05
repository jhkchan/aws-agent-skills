# Eval prompt: cw-logging-disabled-with-lambda

Audit the following Kinesis Data Firehose delivery stream for security
exposure. Emit the standard VERDICT block (STREAM, VERDICT, REASON,
FINDINGS, REMEDIATION).

Delivery stream name: firehose-cw-logging-disabled-with-lambda
ARN: arn:aws:firehose:us-east-1:111111111111:deliverystream/firehose-cw-logging-disabled-with-lambda
DeliveryStreamStatus: ACTIVE
DeliveryStreamType: DirectPut
LoggingConfig: {Enabled: false, LogGroupName: /aws/kinesisfirehose/firehose-cw-logging-disabled-with-lambda}

ExtendedS3DestinationConfiguration:

```json
{
  "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
  "BucketARN": "arn:aws:s3:::firehose-delivery-prod",
  "Prefix": "events/",
  "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
  "CompressionFormat": "UNCOMPRESSED",
  "EncryptionConfiguration": {
    "KMSEncryptionConfig": {
      "AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"
    }
  },
  "S3BackupMode": "Enabled",
  "S3BackupConfiguration": {
    "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
    "BucketARN": "arn:aws:s3:::firehose-backup-prod",
    "Prefix": "lambda-source/",
    "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300}
  },
  "ProcessingConfiguration": {
    "Enabled": true,
    "Processors": [
      {
        "Type": "Lambda",
        "Parameters": [
          {"ParameterName": "LambdaArn", "ParameterValue": "arn:aws:lambda:us-east-1:111111111111:function:firehose-transform"},
          {"ParameterName": "BufferSizeInMBs", "ParameterValue": "1"},
          {"ParameterName": "BufferIntervalInSeconds", "ParameterValue": "60"}
        ]
      }
    ]
  }
}
```
