# Eval prompt: deep-archive-expedited-blocked

User requests Expedited tier on a Deep Archive object. Deep Archive
does not support Expedited. Plan the VERDICT block explaining the
compatibility matrix and recommending the correct tier.

Operation: restore-object
Bucket: compliance-archive
Key: audit-2024.parquet
Source storage class: Glacier Deep Archive
Requested tier: Expedited
Days: 30
RTO: 5 minutes

```json
{
  "ObjectState": {
    "head-object.compliance-archive/audit-2024.parquet": {
      "StorageClass": "DEEP_ARCHIVE",
      "ArchiveStatus": "DEEP_ARCHIVE_ACCESS",
      "Restore": null
    },
    "caller_iam": {
      "role": "S3RestoreOperatorRole",
      "permissions": ["s3:RestoreObject", "s3:GetObject", "s3:HeadObject"]
    }
  }
}
```
