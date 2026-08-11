# Eval prompt: speed-comparison-acceleration-completed

Verify that Transfer Acceleration is enabled and working on the
following bucket and emit the standard VERDICT block (post-
verification form: OPERATION, VERDICT, TARGET, PRE_CHECKS,
POST_VERIFY, COST, NOTES).

Operation: speed-comparison
BucketName: prod-data-lake
Region: us-east-1

```json
{
  "AccelerateConfiguration": {"Status": "Enabled"},
  "SpeedComparison": {
    "DirectUpload": {"Source": "Tokyo", "Speed": "12.3 MB/s"},
    "AcceleratedUpload": {"Source": "Tokyo", "Speed": "58.7 MB/s"},
    "Speedup": "4.8x"
  },
  "EndpointReachability": {
    "Endpoint": "https://prod-data-lake.s3-accelerate.amazonaws.com",
    "Result": "OK (bucket listing returned)"
  },
  "CloudWatchMetrics": {
    "BytesUploadedAccelerate": "42.3 GB",
    "BytesUploadedStandard": "1.2 GB"
  },
  "ChecksumVerification": {
    "Object": "test-upload-2026-08.bin",
    "Algorithm": "CRC32C",
    "Result": "matches local CRC32C"
  }
}
```
