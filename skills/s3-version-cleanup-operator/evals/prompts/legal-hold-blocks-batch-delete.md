# Eval prompt: legal-hold-blocks-batch-delete

Plan the following S3 Batch Operations cleanup and emit the standard
VERDICT block. The bucket has no Object Lock, but 12 of the 1,000
manifest objects have per-object LegalHold: ON.

Operation: batch-delete-versions
Bucket: litigation-hold-bucket
Region: us-east-1
Account: 111111111111
Manifest: 1,000 noncurrent versions. Legal-hold sampling (1000
objects) found 12 with LegalHold: ON, 988 with LegalHold: OFF.

```json
{
  "BucketVersioning": {"Status": "Enabled"},
  "ObjectLockConfiguration": null,
  "ExistingLifecycle": {"Rules": []},
  "ManifestSummary": {
    "TotalNoncurrentVersions": 1000,
    "LegalHoldOn": 12,
    "LegalHoldOff": 988
  },
  "LegalHoldSample": {
    "ObjectsSampled": 1000,
    "LegalHoldOnCount": 12,
    "LegalHoldOffCount": 988
  },
  "IamPermissions": "Caller has s3control:CreateJob, s3:DeleteObjectVersion, iam:PassRole"
}
```
