---
description: Operate S3 Glacier restore workflows — initiate restore (Expedited/Standard/Bulk), provision Expedited capacity, bulk restore via Batch Operations, restore in place vs copy-to-tier, status checking, lifecycle integration. Pre-checks, CONFIRM gate, post-verification.
nl_triggers:
  - "restore object from Glacier"
  - "S3 Glacier restore"
  - "expedited retrieval"
  - "standard retrieval"
  - "bulk retrieval"
  - "Deep Archive restore"
  - "Glacier Instant Retrieval"
  - "provisioned capacity"
  - "bulk restore via Batch Operations"
  - "manifest restore"
  - "restore drill"
  - "DR restore from Glacier"
  - "head-object Restore field"
  - "stalled restore job"
  - "lifecycle policy integration"
  - "copy to different storage class"
  - "promote Glacier object"
routes_to: s3-glacier-restore-operator
---

# /aws:operate-s3-glacier-restore

Activate the `s3-glacier-restore-operator` skill and plan/execute an
S3 Glacier restore operation with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a restore operation spec plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight object-state gate — short-circuit cases where the
   object is in Glacier Instant Retrieval (no restore needed),
   already restored (Restore field with expiry-date), or currently
   being restored (ongoing-request: true — do not re-issue).
2. Tier-vs-source-class compatibility check — Expedited only on
   Flexible Retrieval; Deep Archive only Standard (12hr) or Bulk
   (48hr); GIR is directly readable.
3. RTO reconciliation — the tier SLA must fit within the user's RTO
   budget. BLOCK when it does not.
4. Capacity check for Expedited — verify provisioned capacity
   exists before promising Expedited SLA (on-demand is best-effort).
5. Bulk-restore routing — for manifests of >1000 objects, route to
   S3 Batch Operations (create-job) instead of inline loops.
6. In-place vs copy-to-tier decision — restore-object with Days=N
   is a temporary lease; permanent promotion requires copy-object
   with StorageClass override or a lifecycle-policy update.
7. Lifecycle integration — warn when a lifecycle rule will re-archive
   promoted objects.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <restore-object | bulk-restore | check-status | diagnose | copy-to-tier>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket/key or job-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <restore progress, job status, expiry date>
NOTES: <lease caveat, tier rationale, lifecycle interaction, RTO reconciliation>
```

## When to invoke

Paste a restore operation spec and ask any of:

- "restore this object from Glacier"
- "expedited restore for audit"
- "bulk restore 10000 objects via Batch Operations"
- "DR drill from Glacier with RTO 5 min"
- "permanently promote this object out of Glacier"
- "check restore status for this key"
- "diagnose why my Batch Operations job is stuck"
- "provision Expedited capacity for the drill"

A bare bucket + key + "restore" also routes here via the
orchestrator.

## Inputs

- **Required:** bucket, key (or prefix, or manifest), source storage
  class (or confirm via head-object), tier (Expedited | Standard |
  Bulk), target (in-place | copy-to-bucket | copy-to-tier).
- **Optional:** days (lease window for in-place), RTO budget,
  manifest (for bulk restore), IAM role ARN (for Batch Operations),
  report bucket, version-id (for versioned objects), provisioned
  capacity check (bool).

## Outputs

- One VERDICT block per operation (READY, BLOCKED, or COMPLETED).
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration (per tier
  SLA), expected side-effects (temporary lease vs permanent copy),
  and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  restore expiry-date, the Batch Operations progress summary, and
  any follow-up re-run recommendations.
- For BLOCKED: the specific failure reason (wrong tier for source
  class, RTO exceeded, GIR not archived, capacity missing) and the
  remediation step.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for S3 Glacier storage operations).
- `/aws:audit-s3-bucket` for S3 bucket hardening (encryption,
  versioning, public-access block).
- `/aws:operate-s3-batch-operations` for non-restore Batch Operations
  (copy, replace-tag, invoke Lambda).
- `/aws:operate-backup-vault` for AWS Backup (vs S3 lifecycle) cold
  storage workflows.
