# S3 Multipart Upload with Acceleration and Checksum Reference

Load this reference when planning an accelerated multipart upload to
S3. The procedures below cover the full lifecycle: initiate, upload
parts in parallel, complete, and verify checksums.

## When to use multipart upload

| Object size | Recommendation | Rationale |
|---|---|---|
| < 100 MB | Single PUT | Multipart overhead exceeds benefit |
| 100 MB - 5 GB | Multipart (8-16 MB parts) | Parallelism improves throughput |
| 5 GB - 5 TB | Multipart (128 MB parts) | Required for reliability |
| > 5 TB | Multipart (256 MB parts) | Maximum part count is 10,000 |

**With acceleration:** always use multipart for files > 100 MB.
Parallel parts over accelerated connections maximize throughput.

## Part size selection

| Part size | Max object size (10,000 parts) | Parallelism | Overhead |
|---|---|---|---|
| 8 MB | 80 GB | High (many small parts) | Higher (more PUT requests) |
| 16 MB | 160 GB | High | Moderate |
| 64 MB | 640 GB | Moderate | Low |
| 128 MB | 1.28 TB | Moderate | Low (recommended) |
| 256 MB | 2.56 TB | Lower (fewer, larger parts) | Lowest |
| 500 MB | 5 TB | Lowest | Lowest |

**Recommendation for accelerated uploads:** 128 MB parts. Balances
parallelism (10-20 concurrent parts) with per-part overhead. For a
50 GB upload: 390 parts at 128 MB each.

## Checksum algorithms

| Algorithm | Header | Performance | AWS SDK support | Recommendation |
|---|---|---|---|---|
| CRC32C | `x-amz-checksum-crc32c` | Fastest (hardware-accelerated on modern CPUs) | AWS SDK v2 (all languages) | Best for performance |
| CRC32 | `x-amz-checksum-crc32` | Fast | AWS SDK v2 | Legacy compatibility |
| SHA-1 | `x-amz-checksum-sha1` | Moderate | AWS SDK v2 | Compliance |
| SHA-256 | `x-amz-checksum-sha256` | Slower | AWS SDK v2 | Compliance, widest support |
| MD5 | `Content-MD5` | Fast | All SDKs | Legacy; being deprecated |

**Recommendation:** CRC32C for performance-critical uploads. SHA-256
for compliance-critical uploads where the algorithm is mandated.

## Multipart upload procedure with acceleration

```bash
BUCKET="prod-data-lake"
KEY="large-dataset-2026-08.bin"
ENDPOINT="https://${BUCKET}.s3-accelerate.amazonaws.com"

# 1. Initiate multipart upload with checksum
UPLOAD_ID=$(aws s3api create-multipart-upload \
  --bucket $BUCKET \
  --key $KEY \
  --checksum-algorithm CRC32C \
  --endpoint-url $ENDPOINT \
  --query 'UploadId' --output text)

# 2. Upload parts (example: part 1)
aws s3api upload-part \
  --bucket $BUCKET \
  --key $KEY \
  --part-number 1 \
  --body part-001.bin \
  --upload-id $UPLOAD_ID \
  --checksum-algorithm CRC32C \
  --endpoint-url $ENDPOINT \
  --query '[ETag, ChecksumCRC32C]' --output text

# 3. For parallel uploads (Python with boto3):
python3 << 'EOF'
import boto3
import concurrent.futures
import os

s3 = boto3.client('s3', endpoint_url='https://prod-data-lake.s3-accelerate.amazonaws.com')
bucket = 'prod-data-lake'
key = 'large-dataset-2026-08.bin'
upload_id = '<from-step-1>'
part_size = 128 * 1024 * 1024  # 128 MB

file_size = os.path.getsize('large-dataset.bin')
part_count = (file_size + part_size - 1) // part_size

def upload_part(part_num):
    offset = (part_num - 1) * part_size
    remaining = file_size - offset
    size = min(part_size, remaining)
    with open('large-dataset.bin', 'rb') as f:
        f.seek(offset)
        data = f.read(size)
    response = s3.upload_part(
        Bucket=bucket, Key=key, PartNumber=part_num,
        UploadId=upload_id, Body=data,
        ChecksumAlgorithm='CRC32C'
    )
    return {
        'PartNumber': part_num,
        'ETag': response['ETag'],
        'ChecksumCRC32C': response.get('ChecksumCRC32C')
    }

# Upload 15 parts concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
    results = list(executor.map(upload_part, range(1, part_count + 1)))

# 4. Complete multipart upload
parts = {'Parts': sorted(results, key=lambda p: p['PartNumber'])}
response = s3.complete_multipart_upload(
    Bucket=bucket, Key=key, UploadId=upload_id,
    MultipartUpload=parts
)
print(f"Completed. ChecksumCRC32C: {response.get('ChecksumCRC32C')}")
EOF
```

## Multipart copy between accelerated buckets

```bash
# Copy a large object from one accelerated bucket to another
# using multipart upload-part-copy

SRC_BUCKET="source-bucket"
DST_BUCKET="dest-bucket"
SRC_KEY="large-file.bin"
DST_KEY="large-file-copy.bin"
SRC_ENDPOINT="https://${SRC_BUCKET}.s3-accelerate.amazonaws.com"
DST_ENDPOINT="https://${DST_BUCKET}.s3-accelerate.amazonaws.com"

# 1. Get source object size
OBJ_SIZE=$(aws s3api head-object \
  --bucket $SRC_BUCKET \
  --key $SRC_KEY \
  --endpoint-url $SRC_ENDPOINT \
  --query 'ContentLength' --output text)

# 2. Initiate multipart upload on destination
UPLOAD_ID=$(aws s3api create-multipart-upload \
  --bucket $DST_BUCKET \
  --key $DST_KEY \
  --endpoint-url $DST_ENDPOINT \
  --query 'UploadId' --output text)

# 3. Copy parts (server-side copy through the edge network)
PART_SIZE=$((128 * 1024 * 1024))  # 128 MB
PART_NUM=1
OFFSET=0

while [ $OFFSET -lt $OBJ_SIZE ]; do
  COPY_RANGE="bytes=$((OFFSET))-$((OFFSET + PART_SIZE - 1))"
  if [ $((OFFSET + PART_SIZE)) -gt $OBJ_SIZE ]; then
    COPY_RANGE="bytes=$((OFFSET))-$((OBJ_SIZE - 1))"
  fi

  aws s3api upload-part-copy \
    --bucket $DST_BUCKET \
    --key $DST_KEY \
    --part-number $PART_NUM \
    --upload-id $UPLOAD_ID \
    --copy-source "$SRC_BUCKET/$SRC_KEY" \
    --copy-source-range "$COPY_RANGE" \
    --endpoint-url $DST_ENDPOINT \
    --query '[CopyPartResult.ETag, CopyPartResult.ChecksumCRC32C]' \
    --output text

  OFFSET=$((OFFSET + PART_SIZE))
  PART_NUM=$((PART_NUM + 1))
done

# 4. Complete the multipart copy
aws s3api complete-multipart-upload \
  --bucket $DST_BUCKET \
  --key $DST_KEY \
  --upload-id $UPLOAD_ID \
  --multipart-upload file://parts.json \
  --endpoint-url $DST_ENDPOINT
```

## Abort and cleanup

```bash
# List all in-flight multipart uploads
aws s3api list-multipart-uploads \
  --bucket prod-data-lake \
  --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com

# Abort a specific multipart upload
aws s3api abort-multipart-upload \
  --bucket prod-data-lake \
  --key large-dataset.bin \
  --upload-id <upload-id> \
  --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com

# Abort all in-flight uploads (cleanup script)
for UPLOAD in $(aws s3api list-multipart-uploads \
  --bucket prod-data-lake \
  --query 'Uploads[*].[Key,UploadId]' --output text); do
  KEY=$(echo $UPLOAD | awk '{print $1}')
  UID=$(echo $UPLOAD | awk '{print $2}')
  aws s3api abort-multipart-upload \
    --bucket prod-data-lake \
    --key $KEY \
    --upload-id $UID
done
```

## Checksum verification

```bash
# Verify object checksum after upload
aws s3api head-object \
  --bucket prod-data-lake \
  --key large-dataset-2026-08.bin \
  --query 'ChecksumCRC32C' \
  --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com

# Compare with locally computed CRC32C
python3 -c "
import hashlib
# For CRC32C, use the google-crc32c library
import google_crc32c
with open('large-dataset.bin', 'rb') as f:
    checksum = google_crc32c.value(f.read())
import base64
print(base64.b64encode(checksum.to_bytes(4, 'big')).decode())
"
```
