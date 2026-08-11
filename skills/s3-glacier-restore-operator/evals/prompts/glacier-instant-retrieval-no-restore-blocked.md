# Eval prompt: glacier-instant-retrieval-no-restore-blocked

User requests a restore for an object in Glacier Instant Retrieval.
GIR is directly readable — no restore is required. Plan the VERDICT
block explaining GIR is not archived and recommending GetObject.

Operation: restore-object
Bucket: warm-archive-bucket
Key: user-events-2025-07.parquet
Source storage class: Glacier Instant Retrieval (GLACIER_IR)
Tier: Expedited
Days: 7

```json
{
  "ObjectState": {
    "head-object.warm-archive-bucket/user-events-2025-07.parquet": {
      "StorageClass": "GLACIER_IR",
      "ArchiveStatus": null,
      "Restore": null
    },
    "caller_iam": {
      "role": "S3RestoreOperatorRole",
      "permissions": ["s3:RestoreObject", "s3:GetObject", "s3:HeadObject"]
    }
  }
}
```
