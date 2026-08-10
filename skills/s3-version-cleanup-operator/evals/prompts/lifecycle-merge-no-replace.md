# Eval prompt: lifecycle-merge-no-replace

Plan the following S3 lifecycle configuration update and emit the
standard VERDICT block. The bucket already has 3 lifecycle rules —
the new rule must be MERGED into the existing config (not replace it).

Operation: configure-lifecycle
Bucket: prod-logs-bucket
Region: us-east-1
Account: 111111111111
New rule intent: keep 3 most recent noncurrent versions; expire the
rest; transition kept versions to STANDARD_IA at 30d and GLACIER_IR
at 90d.

```json
{
  "BucketVersioning": {
    "Status": "Enabled",
    "MFADelete": "Disabled"
  },
  "ObjectLockConfiguration": null,
  "BucketEncryption": {
    "ServerSideEncryptionConfiguration": {
      "Rules": [
        {
          "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"},
          "BucketKeyEnabled": true
        }
      ]
    }
  },
  "ExistingLifecycle": {
    "Rules": [
      {
        "ID": "current-version-tier-to-ia",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Transitions": [{"Days": 30, "StorageClass": "STANDARD_IA"}]
      },
      {
        "ID": "current-version-expire-365d",
        "Status": "Enabled",
        "Filter": {"Prefix": "temp/"},
        "Expiration": {"Days": 365}
      },
      {
        "ID": "abort-multipart-7d",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  },
  "StorageLensSample": {
    "NoncurrentVersionCount": 540000,
    "NoncurrentVersionStorageBytes": 13500000000000
  },
  "IamPermissions": "Caller has s3:GetLifecycleConfiguration + s3:PutLifecycleConfiguration on the bucket"
}
```
