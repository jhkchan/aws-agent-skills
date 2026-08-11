# Eval prompt: expedited-single-object-ready

Plan the following Glacier restore and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY,
STATE, NOTES).

Operation: restore-object
Bucket: prod-archive-bucket
Key: quarterly-report-2025-Q1.parquet
Source storage class: Glacier Flexible Retrieval
Tier: Expedited
Days: 7
RTO: 5 minutes

```json
{
  "ObjectState": {
    "head-object.prod-archive-bucket/quarterly-report-2025-Q1.parquet": {
      "StorageClass": "GLACIER",
      "ArchiveStatus": "ARCHIVE_ACCESS",
      "Restore": null
    },
    "provisioned_capacity": {
      "us-east-1": {"units": 1}
    },
    "caller_iam": {
      "role": "S3RestoreOperatorRole",
      "permissions": ["s3:RestoreObject", "s3:GetObject", "s3:HeadObject"]
    }
  }
}
```
