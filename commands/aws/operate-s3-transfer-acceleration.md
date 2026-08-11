---
description: Operate S3 Transfer Acceleration — enable/disable acceleration per bucket (put-bucket-accelerate-configuration), cost analysis by source region ($0.004-0.025/GB), speed comparison tool (accelerate vs direct endpoint), multipart upload with acceleration and CRC32C checksum verification, S3 multipart copy between accelerated buckets, Direct Connect vs Transfer Acceleration comparison, and post-verify with CloudWatch BytesUploaded.
nl_triggers:
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
routes_to: s3-transfer-acceleration-operator
---

# /aws:operate-s3-transfer-acceleration

Activate the `s3-transfer-acceleration-operator` skill and plan/execute
an S3 Transfer Acceleration operation with deterministic pre-checks,
CONFIRM gate, and post-verification.

## What it does

Reads a bucket configuration plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight bucket metadata gate — bucket exists, not a directory
   bucket (S3 Express One Zone), region supports acceleration,
   bucket name DNS-compatible.
2. Pre-check gate — BLOCKED if any check fails (directory bucket,
   region not supported, caller lacks
   `s3:PutAccelerateConfiguration`, in-flight multipart uploads for
   disable, bucket policy conflict).
3. READY — emit the exact CLI sequence with all flags populated, cost
   analysis ($0.004-0.025/GB by source region), speed comparison
   recommendation, multipart upload plan with CRC32C checksums, and
   the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state for rollback,
   execute `put-bucket-accelerate-configuration`, verify endpoint
   reachability.
5. Post-verification — `get-bucket-accelerate-configuration` matches
   intent, accelerate endpoint reachable, CloudWatch BytesUploaded
   confirms traffic, checksum verified; COMPLETED only if ALL
   post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <enable-acceleration | disable-acceleration | speed-comparison | plan-multipart-upload | compare-direct-connect | diagnose-transfer>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket-name> (region <region>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COST: <$X.XX per GB from <source-region> | $0.00 for direct>
NOTES: <speed comparison, multipart recommendation, monitoring>
```

## When to invoke

Paste a bucket configuration plus the intended operation, or just
describe the scenario and ask any of:

- "enable transfer acceleration on prod-data-lake"
- "how much will acceleration cost for a 50 TB upload from Tokyo?"
- "compare acceleration vs Direct Connect for our migration"
- "plan a multipart upload with acceleration and checksums"
- "disable acceleration on this bucket"
- "why are accelerated uploads slower than expected?"

A bare bucket name + any acceleration verb ("enable acceleration on
prod-data-lake", "speed test this bucket") also routes here via the
orchestrator.

## Inputs

- Bucket configuration (`head-bucket`,
  `get-bucket-accelerate-configuration`, `get-bucket-location`,
  `list-multipart-uploads` JSON).
- The intended operation: `enable-acceleration`,
  `disable-acceleration`, `speed-comparison`, `plan-multipart-upload`,
  `compare-direct-connect`, `diagnose-transfer`.
- For multipart upload: object size, part count, checksum algorithm
  (CRC32C recommended).
- For Direct Connect comparison: source location, monthly volume,
  available port speed.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, accelerate endpoint URL,
  estimated cost by source region, multipart upload plan, and the
  CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  observed acceleration status, endpoint reachability, CloudWatch
  BytesUploaded, and checksum verification result.
- For BLOCKED: the specific failure reason (directory bucket, region
  not supported, IAM permission missing, in-flight multipart uploads)
  and the alternative path.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for S3 Transfer Acceleration).
- `/aws:deploy-s3-bucket` for provisioning S3 buckets with versioning,
  lifecycle, encryption, and bucket policies.
- `/aws:optimize-s3-cost` for S3 Storage Class analysis, lifecycle
  rules, and S3 Intelligent-Tiering optimization.
