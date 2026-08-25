# S3 Transfer Acceleration Operator — Worked Examples (Secondary)

Secondary worked examples, moved verbatim from SKILL.md. The primary enable-acceleration example stays in SKILL.md.

### Worked example — disable-acceleration (with in-flight check)

```text
OPERATION: disable-acceleration
VERDICT: READY
TARGET: prod-data-lake (region us-east-1, account 111111111111)
PRE_CHECKS:
  - [PASS] Bucket exists
  - [PASS] Calling role has s3:PutAccelerateConfiguration
  - [PASS] No in-flight multipart uploads via accelerate endpoint
    (list-multipart-uploads returned 0 uploads)
  - [INFO] Current Status: Enabled
STEPS:
  1. CONFIRM: About to disable Transfer Acceleration on bucket
     prod-data-lake (us-east-1). The accelerate endpoint will stop
     accepting uploads. SDK clients configured with
     use_accelerate_endpoint: true will fail. Proceed? (yes/no)
  2. aws s3api put-bucket-accelerate-configuration \
       --bucket prod-data-lake \
       --accelerate-configuration Status=Suspended
  3. Verify:
     aws s3api get-bucket-accelerate-configuration \
       --bucket prod-data-lake
POST_VERIFY:
  - (pending execution)
COST: $0.00 (acceleration disabled — no further accelerate charges)
NOTES:
  - The standard endpoint (prod-data-lake.s3.us-east-1.amazonaws.com)
    remains fully functional. Existing applications using the standard
    endpoint are unaffected.
  - The accelerate endpoint DNS may continue to resolve for several
    hours after disabling, but uploads will be rejected. Update SDK
    client configurations to remove use_accelerate_endpoint: true.
  - If re-enabling later, DNS propagation will again take 20-30
    minutes.
```

### Worked example — plan-multipart-upload with acceleration

```text
OPERATION: plan-multipart-upload
VERDICT: READY
TARGET: prod-data-lake (region us-east-1, accelerated endpoint)
PRE_CHECKS:
  - [PASS] Bucket exists, acceleration Enabled
  - [PASS] Object size: 50 GB (multipart upload required)
  - [PASS] Checksum algorithm: CRC32C (recommended for performance)
  - [INFO] Part size: 128 MB (390 parts for 50 GB)
  - [INFO] Estimated cost: $0.025/GB x 50 GB = $1.25 (acceleration)
    + $0.005/1000 PUT x 390 = $0.002 (PUT requests)
STEPS:
  1. Configure SDK with accelerate endpoint:
     endpoint_url = https://prod-data-lake.s3-accelerate.amazonaws.com
  2. Initiate multipart upload with checksum:
     aws s3api create-multipart-upload \
       --bucket prod-data-lake \
       --key large-dataset-2026-08.bin \
       --checksum-algorithm CRC32C
  3. Upload parts in parallel (recommended: 10-20 concurrent parts):
     aws s3api upload-part \
       --bucket prod-data-lake \
       --key large-dataset-2026-08.bin \
       --part-number <N> \
       --body part-<N>.bin \
       --upload-id <upload-id> \
       --checksum-algorithm CRC32C \
       --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com
  4. Complete multipart upload:
     aws s3api complete-multipart-upload \
       --bucket prod-data-lake \
       --key large-dataset-2026-08.bin \
       --upload-id <upload-id> \
       --multipart-upload file://parts.json
  5. Verify checksum:
     aws s3api head-object \
       --bucket prod-data-lake \
       --key large-dataset-2026-08.bin \
       --query 'ChecksumCRC32C'
POST_VERIFY:
  - (pending execution)
COST: $1.25 (acceleration) + $0.002 (PUT requests) = ~$1.25
NOTES:
  - Use 10-20 concurrent part uploads to maximize throughput.
  - Each part has its own CRC32C checksum; the complete-multipart-
    upload aggregates them into a single checksum on the final object.
  - If any part fails, retry that part only — do not restart the
    entire upload. The upload-id remains valid for aborted parts.
  - Set part size to 128 MB or larger for optimal performance with
    acceleration. Smaller parts increase per-part overhead; larger
    parts reduce parallelism.
```

### Worked example — directory bucket BLOCKED

```text
OPERATION: enable-acceleration
VERDICT: BLOCKED
TARGET: my-express-bucket--xaz-use1-az1 (region us-east-1,
        S3 Express One Zone)
PRE_CHECKS:
  - [PASS] Bucket exists
  - [FAIL] Directory bucket detected (--xaz- suffix). S3 Express One
    Zone directory buckets do NOT support Transfer Acceleration.
    Transfer Acceleration requires a standard S3 bucket.
STEPS: (none — bucket type not supported)
POST_VERIFY: (none)
COST: N/A (acceleration not available)
NOTES:
  - Root cause: S3 Express One Zone (directory buckets) have their
    own low-latency architecture and do not support Transfer
    Acceleration. The put-bucket-accelerate-configuration API returns
    UnsupportedArgument for directory buckets.
  - Fix: use a standard S3 bucket in the target region if
    acceleration is required. S3 Express One Zone is designed for
    ultra-low-latency single-AZ access from within the same AZ.
```

