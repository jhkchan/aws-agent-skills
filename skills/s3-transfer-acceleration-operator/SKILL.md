---
name: s3-transfer-acceleration-operator
description: >-
  Operates S3 Transfer Acceleration workflows — enable/disable
  acceleration per bucket (put-bucket-accelerate-configuration),
  cost analysis by source region ($0.004-0.025/GB depending on
  edge location), speed comparison tool (CloudFront edge vs
  direct S3 endpoint), multipart upload with acceleration endpoints
  (<bucket>.s3-accelerate.amazonaws.com), checksum verification
  (CRC32C, SHA-256) on accelerated uploads, S3 multipart copy
  between accelerated buckets, Direct Connect comparison, and
  diagnostic loops (get-bucket-accelerate-configuration,
  CloudWatch BytesUploaded). Runs deterministic pre-checks (bucket
  exists, not a directory bucket, caller has
  s3:PutAccelerateConfiguration, region supports acceleration,
  cost acknowledgment) behind a CONFIRM gate and emits a READY,
  BLOCKED, or COMPLETED verdict. Use when enabling/disabling
  acceleration, comparing transfer speeds, planning multipart
  uploads over acceleration, or diagnosing slow transfers.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan
  classification. Live-account operations use aws s3api
  put-bucket-accelerate-configuration,
  get-bucket-accelerate-configuration, s3api create-multipart-upload
  / upload-part / complete-multipart-upload (with accelerate
  endpoint), aws s3 ls --endpoint-url, CloudWatch GetMetricStatistics
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - S3 Transfer Acceleration
  - accelerate endpoint
  - s3-accelerate.amazonaws.com
  - multipart upload
  - checksum verification
  - CRC32
  - CRC32C
  - SHA-256
  - Direct Connect
  - edge network
  - put-bucket-accelerate-configuration
  - get-bucket-accelerate-configuration
  - BytesUploaded
  - speed comparison
  - cost per GB
  - multipart copy
  - bucket configuration
tags: [aws, s3, storage, transfer-acceleration, upload, networking, operate]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Enabling or disabling S3 Transfer Acceleration on a bucket,
    comparing transfer speed between accelerated and direct S3
    endpoints, planning a multipart upload over the accelerate
    endpoint, verifying checksums on accelerated uploads, performing
    a multipart copy between accelerated buckets, comparing Transfer
    Acceleration vs Direct Connect for large data transfers, or
    diagnosing why accelerated transfers are slower than expected.
  activation_triggers:
    - "enable S3 Transfer Acceleration"
    - "disable S3 Transfer Acceleration"
    - "accelerate endpoint"
    - "s3-accelerate.amazonaws.com"
    - "put-bucket-accelerate-configuration"
    - "get-bucket-accelerate-configuration"
    - "S3 speed comparison"
    - "accelerated multipart upload"
    - "S3 checksum verification"
    - "CRC32C upload"
    - "S3 multipart copy accelerated"
    - "Transfer Acceleration cost"
    - "Direct Connect vs Transfer Acceleration"
    - "slow S3 transfer"
    - "S3 edge network upload"
  invocation_schema: >-
    Input: either (a) a bucket configuration
    (get-bucket-accelerate-configuration, get-bucket-location,
    head-bucket output) plus the intended operation
    (enable-acceleration, disable-acceleration, speed-comparison,
    plan-multipart-upload, compare-direct-connect,
    diagnose-transfer), OR (b) a bucket-name + operation for live-
    account execution. Output: deterministic OPERATION / VERDICT /
    PRE_CHECKS / STEPS / POST_VERIFY / COST / NOTES block per
    operation, where VERDICT is one of READY, BLOCKED, COMPLETED.
---

# S3 Transfer Acceleration Operator

## What this skill does

Executes S3 Transfer Acceleration operations correctly and
cost-effectively. Runs deterministic pre-checks before any
state-changing CLI (bucket exists, not a directory bucket, caller has
`s3:PutAccelerateConfiguration`, region supports acceleration), then
executes `put-bucket-accelerate-configuration` behind a CONFIRM gate,
and verifies the result via `get-bucket-accelerate-configuration`.
Every enable-acceleration produces a cost analysis (source region to
S3 region at $0.004-0.025/GB), a speed comparison recommendation
(accelerated endpoint vs direct endpoint), and a multipart upload plan
with checksum verification. Disabling acceleration includes
verification that no in-flight multipart uploads depend on the
accelerate endpoint.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why acceleration routes through edge, the cost-by-region model, the Direct Connect crossover | Understanding the cost/speed model |
| **§ Pre-flight** | Bucket metadata gate — exists, not directory bucket, region, caller IAM | Before executing any CLI |
| **§ Process** | Per-operation planning: enable, disable, speed-comparison, plan-multipart, compare-DC, diagnose | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/COST template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — top mistakes that waste money or corrupt transfers | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, verify no in-flight uploads, cost capture | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (bucket is a directory bucket, region does not support acceleration, caller lacks `s3:PutAccelerateConfiguration`, bucket does not exist, cost threshold exceeded without acknowledgment) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Acceleration enable/disable finished and post-verification passed (`get-bucket-accelerate-configuration` matches intent, accelerate endpoint reachable, CloudWatch metrics confirm traffic) | Emit verification results, cost summary, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Bucket reachability** — bucket exists (`head-bucket` does not
   return `404` or `403`).
2. **Not a directory bucket** — S3 Express One Zone directory buckets
   do NOT support Transfer Acceleration. Check bucket naming
   (`<name>--xaz-<az-id>`) and `get-bucket-location`.
3. **Region supports acceleration** — most AWS commercial regions
   support Transfer Acceleration. AWS GovCloud, China, and some
   opt-in regions may have limited support. Verify via
   `get-bucket-accelerate-configuration` (returns
   `Status: Suspended` if acceleration is not available in the
   region).
4. **Caller IAM permission** — the calling identity must have
   `s3:PutAccelerateConfiguration` on the bucket for enable/disable
   operations, and `s3:GetAccelerateConfiguration` for verification.
5. **Cost acknowledgment** — Transfer Acceleration charges
   $0.004-0.025/GB depending on the source edge location. Surface
   the estimated cost based on the planned transfer volume.
6. **No conflicting bucket policies** — bucket policies that deny
   `s3:PutAccelerateConfiguration` or restrict endpoint access must
   be resolved before enabling.
7. **In-flight multipart upload check (disable only)** — before
   disabling, verify no in-flight multipart uploads are using the
   accelerate endpoint via `list-multipart-uploads`.

**Cost/time baselines (2026):**

- Transfer Acceleration pricing by source edge location:
  - Asia Pacific (excluding Australia): $0.025/GB
  - South America: $0.025/GB
  - Australia / New Zealand: $0.025/GB
  - Europe: $0.004/GB
  - North America: $0.004/GB (if source is in NA)
  - Africa: $0.025/GB
  - Middle East: $0.025/GB
- Acceleration is billed on DATA IN (uploads to S3 via the
  accelerate endpoint). Downloads via accelerate are also billed.
- Direct S3 upload (no acceleration): free (standard S3 PUT request
  costs only: $0.005 per 1,000 PUT requests).
- Typical speed improvement: 2-10x for long-distance transfers
  (Asia to US, South America to EU). Minimal or no improvement for
  short-distance transfers (same continent).
- Multipart upload overhead: each part is a separate PUT request.
  10,000 parts at 8MB each = 10,000 PUT requests ($0.05 at
  $0.005/1,000 requests) + acceleration data-in fee.
- Direct Connect: flat port hourly rate ($0.30/hour for 1 Gbps)
  plus $0.02/GB data transfer out. Economical for sustained
  high-volume transfers (>50 TB/month from a fixed location).

## Mindset

**One-line takeaway:** Transfer Acceleration routes uploads through
the nearest CloudFront edge location over an optimized AWS backbone
path — it excels for long-distance, high-latency transfers but costs
$0.004-0.025/GB and is pointless for same-region traffic. Driven by
three S3 realities:

- **Acceleration is a routing optimization, not a bandwidth boost.**
  S3 Transfer Acceleration uses the CloudFront edge network to find
  the fastest path to the destination S3 bucket. The edge location
  receives the upload, then forwards it to S3 over the AWS backbone
  (optimized routing, larger TCP windows, fewer hops). For
  long-distance transfers (Asia to US, South America to EU), this
  can reduce transfer time by 2-10x. For same-region transfers
  (EU to EU, US to US), the improvement is negligible — and you pay
  the $/GB acceleration fee for nothing.

- **Cost scales with data volume, not speed.** You pay per GB
  transferred through the accelerate endpoint. A 1 TB upload from
  Asia to a US bucket costs $25.00 ($0.025/GB x 1,024 GB). A 100 TB
  migration costs $2,500. Always run the speed comparison tool first
  to confirm acceleration provides a meaningful speedup before
  committing to the cost. For sustained high-volume transfers from a
  fixed location, Direct Connect is usually cheaper.

- **Multipart upload is the performance multiplier.** Acceleration
  reduces per-connection latency. Multipart upload increases
  throughput by parallelizing across multiple connections. Together,
  they maximize transfer speed: each part is uploaded over an
  accelerated connection, and multiple parts run in parallel. Always
  use multipart upload for files > 100 MB when acceleration is
  enabled. The accelerate endpoint
  (`<bucket>.s3-accelerate.amazonaws.com`) accepts standard multipart
  upload API calls.

## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-multipart-uploads` paginates at 1,000/page —
drain `--page-size` / `--starting-token` to completion.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws s3api head-bucket --bucket <name>` — confirm bucket exists
   and is accessible (200 OK).
2. `aws s3api get-bucket-location --bucket <name>` — capture the
   bucket region. Verify it is a supported commercial region.
3. `aws s3api get-bucket-accelerate-configuration --bucket <name>`
   — capture `Status` (`Enabled`, `Suspended`, or null).
4. `aws s3api get-bucket-logging --bucket <name>` — verify logging
   is configured for audit trail (advisory).
5. `aws s3api list-multipart-uploads --bucket <name>` — capture
   in-flight multipart uploads (critical for disable-acceleration).
6. `aws cloudwatch get-metric-statistics --namespace AWS/S3
   --metric-name BytesUploaded --dimensions Name=BucketName,
   Value=<name> --start-time <24h-ago> --end-time <now>
   --period 3600 --statistics Sum` — capture recent upload volume
   for cost estimation.

**Malformed input:** if the input is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Bucket configuration
is not valid or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws s3api head-bucket --bucket <name>
--output json and re-plan.`

| Bucket attribute | Effect on operation |
|---|---|
| Directory bucket (`--xaz-` suffix) | BLOCKED — S3 Express One Zone does not support Transfer Acceleration. |
| Bucket in GovCloud / China region | BLOCKED — Transfer Acceleration not available in isolated regions. |
| `Status: Enabled` | Already accelerated. For enable: no-op or advisory. For disable: plan the disable. |
| `Status: Suspended` | Acceleration was enabled then suspended. Re-enable to resume. |
| In-flight multipart uploads (disable only) | BLOCKED — disabling acceleration while multipart uploads are in-flight via the accelerate endpoint will cause upload failures. |
| Bucket policy denies `s3:PutAccelerateConfiguration` | BLOCKED — update the bucket policy first. |
| Virtual-hosted-style incompatible | Advisory — the accelerate endpoint uses `<bucket>.s3-accelerate.amazonaws.com`. Ensure the client supports virtual-hosted-style addressing. |
| Bucket name with underscores | BLOCKED — underscores are not DNS-compatible; the accelerate endpoint requires DNS-compatible bucket names. |

## Process — operation planning (apply in order)

### Step 0: Expert heuristic — non-obvious S3 acceleration behaviors

These behaviors are easy to misjudge without operational experience.
Each changes a plan if ignored:

- **The accelerate endpoint is a different DNS name.** When
  acceleration is enabled, you MUST use
  `<bucket>.s3-accelerate.amazonaws.com` (or
  `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6).
  Using the standard endpoint (`<bucket>.s3.<region>.amazonaws.com`)
  bypasses acceleration entirely — you pay for the feature but get
  no benefit. The SDK auto-detects acceleration when configured with
  `use_accelerate_endpoint: true`.

- **Enabling acceleration does not change the standard endpoint.**
  The bucket remains accessible via the standard S3 endpoint after
  acceleration is enabled. Acceleration is an ADDITIONAL endpoint,
  not a replacement. Existing applications using the standard
  endpoint continue to work unchanged.

- **Directory buckets (S3 Express One Zone) do not support
  acceleration.** S3 Express One Zone (directory buckets with
  `--xaz-` suffix) have their own low-latency architecture and do
  not support Transfer Acceleration. `put-bucket-accelerate-
  configuration` returns an error for directory buckets.

- **Acceleration cost is per-GB data IN, not per-request.** You are
  charged for the data volume transferred through the accelerate
  endpoint, not the number of requests. A 1 GB file uploaded as 1
  part costs the same as a 1 GB file uploaded as 128 parts — the
  acceleration fee is for 1 GB either way. Request costs (PUT
  requests) are billed separately at standard S3 rates.

- **The speed comparison tool is non-destructive.** The S3 Transfer
  Acceleration speed comparison tool uploads and downloads small
  test files through both the accelerated and direct endpoints,
  measuring latency and throughput. It does not affect your data
  or bucket configuration. Always run it before enabling acceleration
  for production workloads.

- **Checksums protect against accelerated transfer corruption.**
  Accelerated uploads traverse the edge network and backbone. While
  TCP provides integrity per-hop, specifying a checksum
  (`x-amz-sdk-checksum-algorithm: CRC32C`) on the upload ensures
  end-to-end verification. S3 validates the checksum on the
  complete object and returns it in the response. For multipart
  uploads, each part has its own checksum; the complete-multipart-
  upload call aggregates them.

- **Disabling acceleration mid-multipart-upload causes failures.**
  If multipart uploads are in-flight via the accelerate endpoint and
  you disable acceleration, subsequent `upload-part` calls to the
  accelerate endpoint will fail. Always complete or abort in-flight
  multipart uploads before disabling acceleration.

- **Direct Connect and Transfer Acceleration serve different use
  cases.** Direct Connect is a dedicated network connection from
  your data center to AWS (fixed port cost + per-GB data transfer).
  Transfer Acceleration uses the public internet to reach the
  nearest edge, then the AWS backbone. Direct Connect is cheaper
  for sustained high-volume transfers from a fixed location
  (>50 TB/month). Transfer Acceleration is better for distributed
  uploaders (many locations uploading to one bucket) or one-time
  migrations.

- **Dual-stack (IPv6) accelerate endpoints are available.** Use
  `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6 support.
  This is transparent to the application — the endpoint resolves to
  both IPv4 and IPv6 addresses. Required for IPv6-only networks
  (some mobile carriers and enterprise networks).

- **Acceleration does not support Amazon S3 Object Lambda.** S3
  Object Lambda Access Points do not work with the accelerate
  endpoint. If your bucket has Object Lambda transformations, they
  are not applied to accelerated uploads.

- **KMS-encrypted buckets work with acceleration.** SSE-KMS
  encryption is transparent to Transfer Acceleration — the edge
  location receives the already-encrypted object and forwards it.
  No additional KMS configuration is needed. However, KMS API
  calls (GenerateDataKey) are NOT accelerated — they go directly
  to KMS in the bucket's region.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Bucket exists (`head-bucket` returns 200).
2. Bucket is accessible (caller has `s3:GetAccelerateConfiguration`).

**For enable-acceleration:**
3. Bucket is NOT a directory bucket (no `--xaz-` suffix, not S3
   Express One Zone).
4. Bucket region supports acceleration (commercial region, not
   GovCloud or China).
5. Calling identity has `s3:PutAccelerateConfiguration` on the bucket.
6. Bucket name is DNS-compatible (lowercase letters, numbers, hyphens;
   no underscores, no uppercase).
7. (Advisory) Cost acknowledgment: surface estimated $/GB based on
   source region.

**For disable-acceleration:**
3. No in-flight multipart uploads using the accelerate endpoint
   (`list-multipart-uploads` returns empty, or all uploads use the
   standard endpoint).
4. Calling identity has `s3:PutAccelerateConfiguration`.
5. (Advisory) Confirm no SDK clients are configured with
   `use_accelerate_endpoint: true` — they will fail after disable.

**For speed-comparison (read-only, non-destructive):**
3. Acceleration is enabled OR the operator plans to test before
   enabling. The speed comparison tool works on buckets with
   acceleration enabled.
4. Test files are small (< 1 MB) and do not affect production data.

**For plan-multipart-upload (read-only planning):**
3. Object size is known and > 100 MB (multipart is recommended for
   larger objects).
4. Acceleration is enabled on the target bucket (or planned to be
   enabled).
5. Checksum algorithm is specified (CRC32C recommended for
   performance, SHA-256 for compatibility).

**For compare-direct-connect (read-only analysis):**
3. Source location (data center or region) is known.
4. Transfer volume (GB/month) is estimated.
5. Direct Connect port speed (1 Gbps or 10 Gbps) is identified.

**For diagnose-transfer (read-only):**
3. Read `get-bucket-accelerate-configuration`, CloudWatch metrics,
   and the failure-mode table to identify why acceleration is slow
   or not working.

**Transfer failure-mode table (use during diagnose-transfer):**

| Symptom | Root cause | Fix |
|---|---|---|
| Accelerated upload is slower than direct | Source and bucket are in the same region (no benefit) or source is near the bucket region | Disable acceleration for same-region transfers; use direct endpoint |
| `put-bucket-accelerate-configuration` returns `UnsupportedArgument` | Bucket is a directory bucket (S3 Express One Zone) | Directory buckets do not support acceleration; use the Express One Zone endpoint directly |
| Accelerated upload returns `PermanentRedirect` | Using the wrong endpoint format; accelerate endpoint requires virtual-hosted-style | Use `<bucket>.s3-accelerate.amazonaws.com`; ensure SDK has `use_accelerate_endpoint: true` |
| `upload-part` to accelerate endpoint fails after disable | Acceleration was disabled while multipart upload was in-flight | Re-enable acceleration, complete or abort the multipart upload, then disable |
| Acceleration enabled but no speed improvement | Client is using the standard endpoint, not the accelerate endpoint | Update the SDK configuration: `use_accelerate_endpoint: true` or use `<bucket>.s3-accelerate.amazonaws.com` |
| Checksum mismatch on accelerated multipart upload | Parts uploaded out of order or part-size mismatch | Use consistent part size (except last part); upload all parts before calling complete-multipart-upload |
| `AccessDenied` on accelerate endpoint | Bucket policy restricts access to specific endpoints or VPC endpoints | Add the accelerate endpoint to the bucket policy's allowed sources |
| Cost higher than expected | Downloads are also billed via accelerate endpoint; large data OUT | Use accelerate for uploads only; serve downloads via CloudFront or standard endpoint |
| IPv6 connection fails on accelerate endpoint | Not using dualstack endpoint | Use `<bucket>.s3-accelerate.dualstack.amazonaws.com` for IPv6 |
| KMS throttling during accelerated multipart upload | Each part triggers a KMS GenerateDataKey call; many parallel parts overwhelm KMS | Request a KMS quota increase, or use a KMS key data key reuse period of 5+ minutes |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated.
- The expected cost (per-GB rate x estimated volume).
- The accelerate endpoint to use in the SDK/client configuration.
- The expected side-effects (accelerate endpoint becomes available,
  standard endpoint unchanged).
- The CONFIRM gate prompt.
- The verification step (`get-bucket-accelerate-configuration` +
  endpoint reachability test).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-bucket-accelerate-configuration`), emit:
  `CONFIRM: About to <enable/disable> Transfer Acceleration on bucket
  <name> (region <region>). <Cost/speed impact>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback:
  `aws s3api get-bucket-accelerate-configuration --bucket <name>
  --output json > /tmp/<name>-accel-pre-$(date +%s).json`.
- Execute the CLI. `put-bucket-accelerate-configuration` is
  synchronous — it returns once the configuration is applied.
  Propagation to the DNS (accelerate endpoint resolving) can take
  20-30 minutes for the first enable.
- For multipart uploads: execute the `create-multipart-upload` →
  `upload-part` (x N) → `complete-multipart-upload` sequence with
  the accelerate endpoint configured.

### Step 4: Post-verification — COMPLETED

After the CLI completes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `get-bucket-accelerate-configuration --bucket <name>` — confirm
   `Status: Enabled` (or `Suspended` for disable).
2. Endpoint reachability:
   `aws s3 ls s3://<name>/ --endpoint-url https://<name>.s3-accelerate.amazonaws.com`
   — confirm the accelerate endpoint resolves and responds.
3. CloudWatch `BytesUploaded` metric — confirm traffic is flowing
   through the accelerate endpoint (spike in BytesUploaded
   correlated with the upload time).
4. (For multipart uploads) Verify checksum: compare the object's
   `x-amz-checksum-crc32c` with the locally computed checksum.
5. Cost verification: confirm the CloudWatch BytesUploaded matches
   the expected volume and the estimated acceleration cost.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Output format (STRICT output contract — per operation)

```text
OPERATION: <enable-acceleration | disable-acceleration | speed-comparison | plan-multipart-upload | compare-direct-connect | diagnose-transfer>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket-name> (region <region>, account <account>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COST: <$X.XX per GB from <source-region> | $0.00 for direct>
NOTES: <speed comparison, multipart recommendation, monitoring>
```

### Worked example — enable-acceleration

```text
OPERATION: enable-acceleration
VERDICT: READY
TARGET: prod-data-lake (region us-east-1, account 111111111111)
PRE_CHECKS:
  - [PASS] Bucket exists (head-bucket: 200 OK)
  - [PASS] Not a directory bucket (standard bucket)
  - [PASS] Region us-east-1 supports acceleration
  - [PASS] Calling role has s3:PutAccelerateConfiguration
  - [PASS] Bucket name is DNS-compatible (lowercase, hyphens)
  - [INFO] Current Status: Suspended (not yet enabled)
  - [INFO] Estimated uploaders: Asia Pacific (Tokyo, Singapore,
    Sydney) and South America (Sao Paulo)
STEPS:
  1. CONFIRM: About to enable Transfer Acceleration on bucket
     prod-data-lake (us-east-1). Uploaders in Asia Pacific will
     pay $0.025/GB; uploaders in North America $0.004/GB; Europe
     $0.004/GB. The accelerate endpoint
     (prod-data-lake.s3-accelerate.amazonaws.com) will become
     available within 20-30 minutes. Proceed? (yes/no)
  2. aws s3api put-bucket-accelerate-configuration \
       --bucket prod-data-lake \
       --accelerate-configuration Status=Enabled
  3. Verify:
     aws s3api get-bucket-accelerate-configuration \
       --bucket prod-data-lake
POST_VERIFY:
  - (pending execution)
COST: $0.025/GB (Asia Pacific uploaders), $0.004/GB (EU/NA uploaders)
NOTES:
  - The accelerate endpoint DNS (prod-data-lake.s3-accelerate
    .amazonaws.com) may take 20-30 minutes to propagate after
    enabling. Test with a small upload before production use.
  - Configure SDK clients with use_accelerate_endpoint: true or use
    the endpoint URL directly.
  - Use multipart upload for files > 100 MB to maximize throughput
    with acceleration.
  - Run the speed comparison tool first for each uploader region to
    confirm acceleration provides a meaningful speedup.
```

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

## Anti-Patterns — NEVER (top mistakes)

- NEVER use the standard S3 endpoint after enabling acceleration.
  The accelerate endpoint (`<bucket>.s3-accelerate.amazonaws.com`)
  is the only way to route through the edge network. Using
  `<bucket>.s3.<region>.amazonaws.com` bypasses acceleration — you
  pay for the feature but get no speed benefit. Configure the SDK
  with `use_accelerate_endpoint: true`.

- NEVER disable acceleration while multipart uploads are in-flight
  via the accelerate endpoint. The in-flight `upload-part` calls
  will fail with `PermanentRedirect` or `NoSuchUpload`. Always
  check `list-multipart-uploads` and complete or abort all active
  uploads before disabling.

- NEVER enable acceleration for same-region transfers. If the
  uploader and the bucket are in the same region (e.g., EU to EU,
  US-East to US-West), the edge network adds latency and cost with
  no speed benefit. Transfer Acceleration is designed for
  long-distance, high-latency transfers. Run the speed comparison
  tool first.

- NEVER forget to specify checksums on accelerated multipart
  uploads. Accelerated uploads traverse the edge network and
  backbone — while TCP provides integrity per-hop, end-to-end
  checksum verification (CRC32C) ensures the object was not
  corrupted in transit. For multipart uploads, each part gets its
  own checksum; the final object checksum is aggregated.

- NEVER assume acceleration is cheaper than Direct Connect for
  sustained high-volume transfers. At 50 TB/month from Asia to US,
  acceleration costs $1,280/month ($0.025/GB). A 1 Gbps Direct
  Connect port costs ~$220/month + $1,024 (50 TB x $0.0204/GB) =
  ~$1,244/month. At 100+ TB/month, Direct Connect is significantly
  cheaper.

- NEVER use the accelerate endpoint for downloads unless you
  explicitly need the speed. Acceleration fees apply to both data IN
  and data OUT. For read-heavy workloads (many downloads), use
  CloudFront instead — it caches at the edge and reduces origin
  fetches.

- NEVER attempt to enable acceleration on a bucket with underscores
  in the name. The accelerate endpoint requires DNS-compatible
  bucket names (lowercase letters, numbers, hyphens only). Underscores
  cause DNS resolution failures. Rename the bucket or use a standard
  endpoint.

- NEVER assume `Status: Enabled` means the endpoint is immediately
  ready. DNS propagation for the accelerate endpoint can take 20-30
  minutes after the first enable. Test with a small upload before
  starting production transfers.

- NEVER skip the speed comparison tool for new acceleration use
  cases. The tool uploads and downloads small test files through
  both endpoints and reports the speed difference. If the speedup is
  less than 1.5x, acceleration is not worth the cost for that source
  region.

- NEVER use acceleration with S3 Object Lambda. Object Lambda Access
  Points do not work with the accelerate endpoint. If the bucket has
  Object Lambda transformations, uploads via the accelerate endpoint
  bypass the transformation.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any
  `put-bucket-accelerate-configuration` call, emit:
  `CONFIRM: About to <enable/disable> Transfer Acceleration on
  bucket <name> (region <region>). <Impact>. Proceed? (yes/no)`. Do
  NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before any acceleration change:
  `aws s3api get-bucket-accelerate-configuration --bucket <name>
  --output json > /tmp/<name>-accel-pre-$(date +%s).json`.

- **Verify no in-flight multipart uploads (for disable).**
  `list-multipart-uploads --bucket <name>` must return 0 active
  uploads using the accelerate endpoint before disabling.

- **Verify DNS compatibility.** The bucket name must be
  DNS-compatible for the accelerate endpoint to work. Check for
  underscores, uppercase letters, or consecutive dots.

- **Verify cost acceptance.** Surface the estimated acceleration
  cost (per-GB rate x estimated volume) before enabling. Track
  actual cost via CloudWatch BytesUploaded and Cost Explorer.

- **Prefer multipart upload for large objects.** When acceleration
  is enabled, always use multipart upload for files > 100 MB.
  Parallel parts over accelerated connections maximize throughput.
  Use CRC32C checksums for end-to-end integrity.

## Recent AWS features (2024-2026)

- **S3 Express One Zone (2024 GA):** Single-AZ, ultra-low-latency
  storage class with directory buckets. Does NOT support Transfer
  Acceleration. Designed for ML training data, analytics
  workloads, and local caching — not for long-distance transfers.

- **S3 checksums with multipart upload (2024-2025):** CRC32C
  checksum support for individual parts and aggregated object-level
  checksums on complete-multipart-upload. The `x-amz-checksum-crc32c`
  header is verified by S3 on upload completion. CRC32C is faster
  than CRC32 or SHA-256 for hardware-accelerated computation.

- **S3 multipart copy between accelerated buckets (2024-2025):**
  Server-side copy between S3 buckets using multipart upload
  (`create-multipart-upload` + `upload-part-copy`). When both
  buckets have acceleration enabled, the copy is routed through
  the edge network. Useful for cross-region data migration.

- **S3 Transfer Acceleration dual-stack IPv6 (2024):** The
  accelerate endpoint supports IPv6 via
  `<bucket>.s3-accelerate.dualstack.amazonaws.com`. Required for
  IPv6-only networks and some mobile carriers.

- **AWS Direct Connect + S3 integration (2024-2026):** Direct
  Connect now supports S3 VPC gateway endpoints over private VIFs.
  This provides a private, dedicated path to S3 without traversing
  the public internet. For sustained high-volume transfers from a
  fixed data center, Direct Connect is cheaper and more reliable
  than Transfer Acceleration.

- **S3 Batch Operations with acceleration (2025):** S3 Batch
  Operations now supports copy operations through the accelerate
  endpoint for cross-region batch transfers. Useful for large-scale
  data migration jobs.

- **CloudWatch S3 metrics enhancement (2025):** CloudWatch now
  provides per-endpoint S3 metrics (accelerate vs standard). The
  `BytesUploaded` metric can be filtered by endpoint type to
  monitor acceleration usage and cost.

## Domain

AWS CloudOps / S3 Transfer Acceleration, Multipart Upload Optimization & Cross-Region Transfer Strategy.

## AWS documentation

- **S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/
- **Transfer Acceleration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/transfer-acceleration.html
- **Transfer Acceleration speed comparison** — https://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html
- **Multipart upload** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
- **S3 checksums** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity.html
- **S3 Express One Zone** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-one-zone.html
- **S3 pricing** — https://aws.amazon.com/s3/pricing/
- **Direct Connect pricing** — https://aws.amazon.com/directconnect/pricing/
- **S3 CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
