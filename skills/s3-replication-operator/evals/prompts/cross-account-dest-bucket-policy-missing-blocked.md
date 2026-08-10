# Eval prompt: cross-account-dest-bucket-policy-missing-blocked

Diagnose the following cross-account S3 replication failure and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: configure-cross-account (diagnose mode)
Source: prod-logs-source-us-east-1 (us-east-1, account 111111111111)
Destination: audit-logs-dest (us-west-2, account 222222222222)

```json
{
  "ReplicationConfig": {
    "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Rules": [
      {
        "ID": "xaccount-audit",
        "Status": "Enabled",
        "Filter": {"Prefix": "audit/"},
        "Destination": {
          "Bucket": "arn:aws:s3:::audit-logs-dest",
          "Account": "222222222222",
          "AccessControlTranslation": {"Owner": "Destination"}
        }
      }
    ]
  },
  "DestinationObjectOwnership": "BucketOwnerPreferred",
  "IamRolePermissions": {
    "AccountId": "111111111111",
    "Grants": [
      "s3:ReplicateObject, s3:ReplicateDelete, s3:ObjectOwnerOverrideToBucketOwner on arn:aws:s3:::audit-logs-dest/*",
      "kms:Encrypt on arn:aws:kms:us-west-2:222222222222:key/dest-cmk"
    ]
  },
  "DestinationKmsKeyPolicy": {
    "Grants": "arn:aws:iam::111111111111:role/s3-repl-role kms:Encrypt (verified)"
  },
  "DestinationBucketPolicy": {
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::111111111111:role/s3-repl-role"},
        "Action": ["s3:ReplicateObject", "s3:ReplicateDelete"],
        "Resource": "arn:aws:s3:::audit-logs-dest/*"
      }
    ],
    "Missing": [
      "s3:ObjectOwnerOverrideToBucketOwner action",
      "s3:x-amz-source-account condition"
    ]
  },
  "DestinationCloudTrail": {
    "AccessDeniedEvents": 2341,
    "Window": "last 7 days, filtered for s3 Replication PutObject",
    "SampleError": "AccessDenied — s3-replication principal denied PutObject on arn:aws:s3:::audit-logs-dest/audit/2026-08-09.log"
  }
}
```
