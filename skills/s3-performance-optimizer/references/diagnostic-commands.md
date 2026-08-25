# Diagnostic Commands — S3 Performance Optimizer

Pre-flight and per-layer probe commands moved from SKILL.md. Load on demand.

## Pre-flight: workload state and gather-info gate (commands)

```bash
# 1. Bucket location and key features
aws s3api get-bucket-location --bucket <bucket> --output json
aws s3api get-bucket-accelerate-configuration --bucket <bucket> --output json
aws s3api list-objects-v2 --bucket <bucket> --prefix <prefix> --max-items 10 \
  --query 'Contents[].{Key: Key, Size: Size}'

# 2. CloudWatch request metrics (must be enabled on the bucket)
aws cloudwatch get-metric-statistics --namespace AWS/S3 \
  --metric-name FirstByteLatency \
  --dimensions Name=BucketName,Value=<bucket> Name=FilterId,Value=EntireBucket \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,p99 --output json

aws cloudwatch get-metric-statistics --namespace AWS/S3 \
  --metric-name 4xxErrors \
  --dimensions Name=BucketName,Value=<bucket> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json

# 3. Storage Lens (if configured)
aws s3control get-storage-lens-configuration --config-id <id> \
  --account-id <account-id> --output json

# 4. S3 Select probe (for CSV/JSON/Parquet workloads)
aws s3api select-object-content \
  --bucket <bucket> --key <key> \
  --expression "SELECT * FROM s3object s LIMIT 10" \
  --expression-type SQL \
  --input-serialization '{"CSV": {"FileHeaderInfo": "USE"}}' \
  --output-serialization '{"CSV": {}}' /dev/stdout

# 5. Byte-range fetch probe (measure latency of partial read)
curl -sv -H 'Range: bytes=0-1023' \
  "https://<bucket>.s3.<region>.amazonaws.com/<key>" \
  -o /dev/null -w '%{time_total}s %{size_download}b\n'
```

## Step 3 probe: current upload method and multipart timing

```bash
# Verify current upload method
aws s3api head-object --bucket <bucket> --key <key> --output json | \
  jq '.ContentLength'

# Time the current upload
time aws s3 cp <large-file> s3://<bucket>/<key> --expected-size <size>

# Multipart upload with explicit part size and parallelism
time aws s3 cp <large-file> s3://<bucket>/<key> \
  --expected-size <size> \
  --multipart-chunksize 100MB \
  --max-concurrent-requests 10
```

