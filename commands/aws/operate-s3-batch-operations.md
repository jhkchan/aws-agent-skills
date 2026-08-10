---
description: Operate AWS S3 Batch Operations jobs — create copy/replace-tag/restore/replicate/invoke-Lambda/put-ACL/object-lock jobs, diagnose failed jobs, cancel runaway jobs, update priority and rate control — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "S3 Batch Operations"
  - "batch copy objects"
  - "bulk restore Glacier"
  - "bulk replace tags"
  - "batch invoke Lambda"
  - "bulk replication backfill"
  - "bulk KMS re-encrypt"
  - "bulk storage class transition"
  - "put object lock retention batch"
  - "batch operations manifest"
  - "S3 inventory manifest"
  - "CSV manifest"
  - "completion report"
  - "RequestsPerSecond batch"
  - "cancel batch job"
  - "update job priority"
  - "S3 Tables batch operations"
  - "billion objects batch"
  - "batch operations failed tasks"
  - "describe-job"
routes_to: s3-batch-operations-operator
---

# /aws:operate-s3-batch-operations

Activate the `s3-batch-operations-operator` skill and plan/execute an
S3 Batch Operations job with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads a job specification (operation type, manifest, report bucket,
role, rate control) plus the intended operation and applies the
priority-ordered pre-check sequence:

1. Pre-flight job spec gate — short-circuit malformed manifests,
   wrong-Region report buckets, missing operation-specific grants.
2. Pre-check gate — BLOCKED if any check fails (manifest unreadable,
   report bucket not writable, role missing operation-specific S3/KMS
   grants, Lambda resource policy missing
   `batchoperations.amazonaws.com`, KMS key policy denies role,
   rate-control invalid, manifest contains zero objects).
3. READY — emit the exact `create-job` CLI with all flags populated,
   the estimated ETA from rate control, the expected KMS / S3 request
   volume, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   poll `describe-job` until `Status: Complete`.
5. Post-verification — Status Complete, NumberOfTasksFailed within
   threshold, completion report readable, sample objects verified.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-job | diagnose-job | cancel-job | update-priority>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <manifest-bucket/path> (operation: <type>, role: <arn-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <rate-control, monitoring, caveats>
```

## When to invoke

Paste a job specification plus the intended operation, or just
describe the scenario and ask any of:

- "bulk copy objects from bucket A to bucket B"
- "restore these Glacier objects in bulk"
- "re-encrypt all objects with the new KMS key"
- "invoke this Lambda across a manifest of objects"
- "replace tags in bulk across a bucket"
- "set object lock retention in bulk"
- "diagnose a failed Batch Operations job"
- "cancel a runaway job"
- "backfill replication for existing objects"

A bare bucket + batch verb ("batch copy", "bulk restore", "batch
re-encrypt") also routes here via the orchestrator.

## Inputs

- Job specification: operation type, manifest format and location,
  report bucket, IAM role ARN, operation-specific parameters
  (destination bucket for copy, tag set for replace-tag, restore tier
  and days for Glacier, Lambda ARN for invoke, ACL or retention
  policy for put-acl / put-object-lock).
- Role configuration: trust policy, identity-based policies, KMS key
  policy grants.
- For Lambda operations: Lambda `get-function-configuration`,
  `get-policy`, `get-function-concurrency`.
- For diagnose / cancel: `describe-job` output.
- Rate control: `RequestsPerSecond`, `CompletionWindow`, `Priority`.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact `create-job` CLI, estimated ETA, estimated KMS
  / S3 request volume, expected cost, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  `NumberOfTasksSucceeded` / `NumberOfTasksFailed` counts, sample-
  object verification, monitoring recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., `lambda add-permission --principal
  batchoperations.amazonaws.com`, `kms put-key-policy`,
  `lambda put-function-concurrency`).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for S3 Batch Operations).
- `/aws:operate-s3-replication` for the replication-rule counterpart —
  configuring CRR/SRR rules (this skill handles the batch-backfill of
  existing objects).
- `/aws:audit-s3-public-access` for the audit-side counterpart —
  auditing bucket posture without changing state.
- `/aws:optimize-s3-lifecycle` for the optimize-side counterpart —
  planning storage-class transitions (this skill executes the bulk
  transition).
