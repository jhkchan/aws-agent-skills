# Eval prompt: buffering-hints-out-of-range

Audit the following Kinesis Data Firehose delivery stream for security
exposure. Emit the standard VERDICT block (STREAM, VERDICT, REASON,
FINDINGS, REMEDIATION).

Delivery stream name: firehose-buffering-hints-out-of-range
ARN: arn:aws:firehose:us-east-1:111111111111:deliverystream/firehose-buffering-hints-out-of-range
DeliveryStreamStatus: ACTIVE
DeliveryStreamType: DirectPut
LoggingConfig: {Enabled: true, LogGroupName: /aws/kinesisfirehose/firehose-buffering-hints-out-of-range}

ExtendedS3DestinationConfiguration:

```json
{
  "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
  "BucketARN": "arn:aws:s3:::firehose-delivery-prod",
  "Prefix": "events/",
  "BufferingHints": {"SizeInMBs": 256, "IntervalInSeconds": 30},
  "CompressionFormat": "UNCOMPRESSED",
  "EncryptionConfiguration": {
    "KMSEncryptionConfig": {
      "AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"
    }
  },
  "S3BackupMode": "Disabled"
}
```
