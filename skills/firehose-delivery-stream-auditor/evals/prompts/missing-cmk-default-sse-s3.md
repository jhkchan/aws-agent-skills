# Eval prompt: missing-cmk-default-sse-s3

Audit the following Kinesis Data Firehose delivery stream for security
exposure. Emit the standard VERDICT block (STREAM, VERDICT, REASON,
FINDINGS, REMEDIATION).

Delivery stream name: firehose-missing-cmk-default-sse-s3
ARN: arn:aws:firehose:us-east-1:111111111111:deliverystream/firehose-missing-cmk-default-sse-s3
DeliveryStreamStatus: ACTIVE
DeliveryStreamType: DirectPut
LoggingConfig: {Enabled: true, LogGroupName: /aws/kinesisfirehose/firehose-missing-cmk-default-sse-s3}

ExtendedS3DestinationConfiguration:

```json
{
  "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
  "BucketARN": "arn:aws:s3:::firehose-delivery-prod",
  "Prefix": "events/",
  "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
  "CompressionFormat": "UNCOMPRESSED",
  "S3BackupMode": "Disabled"
}
```
