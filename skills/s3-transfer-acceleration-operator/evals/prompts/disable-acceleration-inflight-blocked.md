# Eval prompt: disable-acceleration-inflight-blocked

Plan the following S3 Transfer Acceleration disable operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COST, NOTES).

Operation: disable-acceleration
BucketName: prod-data-lake
Region: us-east-1

```json
{
  "AccelerateConfiguration": {"Status": "Enabled"},
  "InFlightMultipartUploads": {
    "Uploads": [
      {
        "UploadId": "abc123-initiated-2026-08-10T15:00Z",
        "Key": "large-dataset-part1.bin",
        "StorageClass": "STANDARD"
      },
      {
        "UploadId": "def456-initiated-2026-08-10T15:15Z",
        "Key": "large-dataset-part2.bin",
        "StorageClass": "STANDARD"
      }
    ]
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/S3Admin",
  "IAMPermissions": ["s3:PutAccelerateConfiguration"]
}
```
