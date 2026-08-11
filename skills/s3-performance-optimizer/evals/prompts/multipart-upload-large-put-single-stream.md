# Eval prompt: multipart-upload-large-put-single-stream

Optimise the S3 workload described below. Walk the workload-driven
optimisation tree and emit the standard optimisation block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: We upload a daily 5 GB CSV file to a single S3 bucket from an
on-prem server over a 500 Mbps Direct Connect. The upload takes ~80
seconds; we want it under 15 seconds.

```text
Bucket: multipart-upload-large-put-single-stream-prod
Region: us-east-1
Workload: write-once daily bulk upload
ObjectSize: 5 GB
ClientGeography: on-prem over Direct Connect (us-east-1)
TargetLatency: complete upload in <15 s

Current upload command:
  aws s3api put-object --bucket \
    multipart-upload-large-put-single-stream-prod \
    --key daily_export.csv --body daily_export.csv

CloudWatch metrics (last 7 days, last upload):
  - BytesUploaded: 5 GB over 81 seconds (~500 Mbps)
  - FirstByteLatency p99: 45 ms
  - 4xxErrors: 0
  - 5xxErrors: 0

Transfer Acceleration: not enabled
Multipart upload: NOT in use (single PUT)
```

The bottleneck is the single-stream throughput ceiling. S3 multipart
upload with 10 parallel parts at 500 MB each would saturate multiple
TCP streams and approach the Direct Connect link bandwidth.
