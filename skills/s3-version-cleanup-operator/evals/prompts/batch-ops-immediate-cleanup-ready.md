# Eval prompt: batch-ops-immediate-cleanup-ready

Plan the following S3 Batch Operations immediate cleanup and emit the
standard VERDICT block. All pre-checks should pass.

Operation: batch-delete-versions
Bucket: staging-uploads-bucket
Region: us-east-1
Account: 111111111111
Manifest: 2,500,000 noncurrent versions via S3 Inventory
(2026-08-08 snapshot, manifest.json in manifest-bucket)

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
  "LegalHoldSample": {
    "ObjectsSampled": 1000,
    "LegalHoldOnCount": 0,
    "LegalHoldOffCount": 1000
  },
  "InventoryManifest": {
    "Format": "S3InventoryReports",
    "Bucket": "arn:aws:s3:::manifest-bucket",
    "Prefix": "staging-uploads-inventory/2026-08-08/",
    "ManifestObject": "arn:aws:s3:::manifest-bucket/staging-uploads-inventory/2026-08-08/manifest.json"
  },
  "NoncurrentBytesEstimate": 35000000000000,
  "IamPermissions": "Caller has s3control:CreateJob, s3:DeleteObjectVersion, iam:PassRole on the execution role"
}
```
