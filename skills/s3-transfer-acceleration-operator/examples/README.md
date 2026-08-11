# End-to-end usage scenario: s3-transfer-acceleration-operator

A walkthrough showing the skill planning an enable-acceleration
operation on a standard S3 bucket, with all pre-checks passing and
the operator confirming at the CONFIRM gate. Contrasted with the
BLOCKED case where a directory bucket cannot use acceleration.

## Input (user prompt)

> Enable Transfer Acceleration on `prod-data-lake` (us-east-1).
> We have uploaders in Tokyo, Singapore, Sydney, and Sao Paulo
> that need faster upload speeds.

```json
{
  "Operation": "enable-acceleration",
  "BucketName": "prod-data-lake",
  "Region": "us-east-1",
  "HeadBucket": {"Status": 200},
  "BucketLocation": {"LocationConstraint": "us-east-1"},
  "AccelerateConfiguration": {"Status": "Suspended"},
  "InFlightMultipartUploads": {"Uploads": []},
  "Uploaders": ["Tokyo", "Singapore", "Sydney", "Sao Paulo"]
}
```

## Skill output

```text
OPERATION: enable-acceleration
VERDICT: READY
TARGET: prod-data-lake (region us-east-1, account 111111111111)
PRE_CHECKS:
  - [PASS] Bucket exists (head-bucket: 200 OK)
  - [PASS] Not a directory bucket (standard bucket)
  - [PASS] Region us-east-1 supports acceleration
  - [PASS] Calling role has s3:PutAccelerateConfiguration
  - [PASS] Bucket name is DNS-compatible
  - [INFO] Current Status: Suspended
  - [INFO] Uploaders: Tokyo, Singapore, Sydney (APAC $0.025/GB),
    Sao Paulo (SA $0.025/GB)
STEPS:
  1. CONFIRM: About to enable Transfer Acceleration on bucket
     prod-data-lake (us-east-1). Uploaders in APAC and SA will pay
     $0.025/GB. The accelerate endpoint will become available within
     20-30 minutes. Proceed? (yes/no)
  2. aws s3api put-bucket-accelerate-configuration \
       --bucket prod-data-lake \
       --accelerate-configuration Status=Enabled
  3. Verify:
     aws s3api get-bucket-accelerate-configuration \
       --bucket prod-data-lake
POST_VERIFY:
  - (pending execution)
COST: $0.025/GB (APAC/SA uploaders), $0.004/GB (EU/NA uploaders)
NOTES:
  - DNS propagation for the accelerate endpoint takes 20-30 minutes.
  - Configure SDK clients with use_accelerate_endpoint: true.
  - Use multipart upload for files > 100 MB.
  - Run the speed comparison tool for each uploader region.
```

## Contrast — BLOCKED case (directory bucket)

If the operator tried to enable acceleration on an S3 Express One
Zone directory bucket, the pre-check gate would fire:

```text
OPERATION: enable-acceleration
VERDICT: BLOCKED
TARGET: my-express-bucket--xaz-use1-az1 (region us-east-1,
        S3 Express One Zone)
PRE_CHECKS:
  - [PASS] Bucket exists
  - [FAIL] Directory bucket detected (--xaz- suffix). S3 Express One
    Zone directory buckets do NOT support Transfer Acceleration.
STEPS: (none — bucket type not supported)
POST_VERIFY: (none)
COST: N/A (acceleration not available)
NOTES:
  - Root cause: S3 Express One Zone directory buckets have their own
    low-latency architecture and do not support Transfer Acceleration.
  - Fix: use a standard S3 bucket in the target region if acceleration
    is required.
```

## What the skill caught that a generic assistant misses

1. **Directory bucket detection.** A generic assistant emits
   `put-bucket-accelerate-configuration` directly, which returns
   `UnsupportedArgument`. The skill detects the `--xaz-` suffix and
   blocks before execution.

2. **In-flight multipart upload check.** A generic assistant disables
   acceleration without checking for active uploads. The skill checks
   `list-multipart-uploads` first and blocks if uploads are active.

3. **Cost analysis by source region.** A generic assistant does not
   mention per-GB costs or distinguish APAC ($0.025) from EU/NA
   ($0.004). The skill surfaces the estimated cost per uploader
   region.

4. **Endpoint configuration awareness.** A generic assistant enables
   acceleration and says "you're done." The skill explicitly notes
   that SDK clients must use `use_accelerate_endpoint: true` or the
   accelerate endpoint URL — otherwise the standard endpoint is used
   and acceleration has no effect.

5. **DNS propagation delay.** A generic assistant omits the 20-30
   minute DNS propagation delay for the first enable. The skill warns
   the operator to test with a small upload before production use.

6. **Direct Connect comparison.** For large migrations, a generic
   assistant recommends acceleration without comparing to Direct
   Connect. The skill surfaces the crossover threshold (~50 TB/month
   for APAC) and recommends Direct Connect for sustained high-volume
   transfers.

7. **Checksum verification.** A generic assistant omits checksum
   verification. The skill specifies CRC32C for each part and the
   aggregated object checksum on complete-multipart-upload.

## Slash-command invocation

```
/aws:operate-s3-transfer-acceleration
```

Or via the orchestrator:

```
/aws:pipeline
You: "enable transfer acceleration on prod-data-lake"
```

The orchestrator emits
`[Phase: Operate | Skills routed: s3-transfer-acceleration-operator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "enable s3 transfer acceleration on prod-data-lake"
# [Phase: Operate | Skills routed: s3-transfer-acceleration-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After enabling acceleration:

```bash
# Verify acceleration status
aws s3api get-bucket-accelerate-configuration \
  --bucket prod-data-lake \
  --profile default

# Test accelerate endpoint (after 20-30 min DNS propagation)
aws s3 ls s3://prod-data-lake/ \
  --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com \
  --profile default

# Run speed comparison from an APAC uploader
# Open: https://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html

# Upload a test file with multipart + CRC32C via accelerate endpoint
aws s3 cp test-file.bin s3://prod-data-lake/test-file.bin \
  --endpoint-url https://prod-data-lake.s3-accelerate.amazonaws.com \
  --profile default

# Monitor acceleration traffic via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BytesUploaded \
  --dimensions Name=BucketName,Value=prod-data-lake \
  --start-time $(date -u -v-1h +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum \
  --profile default
```
