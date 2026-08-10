# Eval prompt: add-rule-crr-kms-rtc-ready

Plan the following S3 cross-region replication rule add and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: add-rule
Source: prod-logs-source-us-east-1 (us-east-1, account 111111111111)
Destination: prod-logs-dr-eu-west-1 (eu-west-1, account 111111111111)
Filter: prefix "logs/"
RTC: enabled (15 min SLA)

```json
{
  "SourceBucket": {
    "Name": "prod-logs-source-us-east-1",
    "Region": "us-east-1",
    "Account": "111111111111",
    "Versioning": "Enabled",
    "Encryption": "SSE-KMS",
    "KmsKeyArn": "arn:aws:kms:us-east-1:111111111111:key/source-cmk"
  },
  "DestinationBucket": {
    "Name": "prod-logs-dr-eu-west-1",
    "Region": "eu-west-1",
    "Account": "111111111111",
    "Versioning": "Enabled",
    "ObjectOwnership": "BucketOwnerEnforced",
    "Encryption": "SSE-KMS",
    "KmsKeyArn": "arn:aws:kms:eu-west-1:111111111111:key/dest-cmk"
  },
  "IamRole": {
    "Arn": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Permissions": [
      "s3:GetReplicationConfiguration on arn:aws:s3:::prod-logs-source-us-east-1",
      "s3:GetObjectVersion on arn:aws:s3:::prod-logs-source-us-east-1/*",
      "s3:ReplicateObject, s3:ReplicateDelete on arn:aws:s3:::prod-logs-dr-eu-west-1/*",
      "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/source-cmk",
      "kms:Encrypt on arn:aws:kms:eu-west-1:111111111111:key/dest-cmk"
    ]
  },
  "DestinationKmsKeyPolicy": {
    "Grants": "arn:aws:iam::111111111111:role/s3-repl-role kms:Encrypt"
  },
  "ExistingReplicationConfig": {
    "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Rules": [
      {
        "ID": "existing-rule-app",
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {"Prefix": "app/"},
        "Destination": {"Bucket": "arn:aws:s3:::app-dr-eu-west-1"}
      }
    ]
  }
}
```
