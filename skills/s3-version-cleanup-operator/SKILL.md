---
name: s3-version-cleanup-operator
description: >-
  Operates S3 version cleanup for cost optimization and compliance —
  NoncurrentVersionExpiration, NoncurrentVersionTransition,
  NewerNoncurrentVersions, AbortIncompleteMultipartUpload lifecycle
  rules, S3 Batch Operations for immediate version delete, Object
  Lock (Compliance vs Governance mode) and legal-hold handling,
  versioning-state pre-checks (Enabled vs Suspended), Storage Lens
  impact estimation, and post-apply verification. Runs deterministic
  pre-checks (versioning enabled, Object Lock mode and retention,
  legal holds, existing lifecycle rule conflicts, BucketKeyEnabled
  for cost), executes the operation behind a CONFIRM gate, and emits
  a verdict (READY | BLOCKED | COMPLETED) per bucket with the exact
  CLI/JSON sequence, estimated monthly savings, and verification
  commands. Use when auditing noncurrent version accumulation,
  configuring version cleanup lifecycle rules, planning immediate
  cleanup via Batch Operations, handling Object Lock retention, or
  estimating S3 version cleanup savings.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan classification.
  Live-account operations use aws s3api get-bucket-versioning,
  put-bucket-versioning, get-bucket-lifecycle-configuration,
  put-bucket-lifecycle-configuration, get-object-lock-configuration,
  get-object-legal-hold, list-object-versions, delete-objects, and
  aws s3control create-job (S3 Batch Operations) (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - S3
  - versioning
  - noncurrent versions
  - NoncurrentVersionExpiration
  - NoncurrentVersionTransition
  - NewerNoncurrentVersions
  - lifecycle rule
  - AbortIncompleteMultipartUpload
  - S3 Batch Operations
  - Object Lock
  - Compliance mode
  - Governance mode
  - legal hold
  - S3 Storage Lens
  - cost optimization
  - version cleanup
  - delete markers
  - BucketKeyEnabled
tags: [s3, storage, versioning, lifecycle, cost-optimization, object-lock, batch-operations]
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
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [s3, storage, versioning, lifecycle, cost-optimization, object-lock]
  dependencies: [aws-orchestrator]
  keywords:
    - S3
    - versioning
    - noncurrent versions
    - lifecycle rule
    - Object Lock
    - S3 Batch Operations
    - cost optimization
  when_to_use: >-
    Auditing S3 noncurrent version accumulation, configuring version
    cleanup lifecycle rules (NoncurrentVersionExpiration,
    NoncurrentVersionTransition, NewerNoncurrentVersions), planning
    immediate version cleanup via S3 Batch Operations, handling Object
    Lock retention before cleanup, estimating S3 version cleanup
    savings, or hardening S3 cost posture on versioned buckets.
  activation_triggers:
    - "clean up S3 versions"
    - "S3 noncurrent versions cost"
    - "configure S3 lifecycle NoncurrentVersionExpiration"
    - "S3 version cleanup"
    - "S3 Object Lock retention"
    - "S3 legal hold"
    - "S3 Batch Operations delete versions"
    - "S3 cost optimization versions"
    - "S3 Storage Lens noncurrent"
    - "abort multipart upload S3"
    - "S3 NewerNoncurrentVersions"
    - "versioned bucket cleanup"
    - "S3 lifecycle configuration"
  invocation_schema: >-
    Input: either (a) a bucket configuration with the intended
    operation (configure-lifecycle, batch-delete-versions, audit-
    versions, estimate-savings), OR (b) a bucket name + operation for
    live-account execution. Output: deterministic OPERATION/VERDICT/
    PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT
    is one of READY, BLOCKED, COMPLETED.
---

# S3 Version Cleanup Operator

## What this skill does

Executes S3 version cleanup operations correctly and safely — for
cost optimization and for compliance retention. Runs deterministic
pre-checks before any state-changing CLI (versioning state, Object
Lock mode + retention, legal holds, existing lifecycle conflicts),
executes the operation behind a CONFIRM gate, and verifies the
result. Every operation surfaces the estimated monthly savings, the
compliance implications, and the verification steps.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority order | Before any operation |
| **§ Mindset** | Why version cleanup is the #1 S3 cost lever, the 4 lifecycle rule types, Object Lock modes | Understanding the cost model |
| **§ Pre-flight** | Bucket metadata gate — versioning state, Object Lock, legal holds, existing lifecycle | Before executing any CLI |
| **§ Process** | Per-operation planning: lifecycle rules, batch-delete, impact estimation, audit | When choosing which operation to run |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, SAVINGS, VERIFICATION | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause data loss or compliance violation | Review before risky operations |
| **§ Pre-flight safety** | Additional checks before any remediation CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (versioning not enabled, Object Lock Compliance mode blocks deletion, legal hold active, lifecycle rule conflict, bucket in a different region/account than expected) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI/JSON sequence, wait for operator yes |
| `COMPLETED` | Operation finished and post-verification passed (lifecycle rule applied, Batch Operations job completed, noncurrent version count dropped) | Emit savings estimate, verification results |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Versioning state** — must be `Enabled` for cleanup to affect
   noncurrent versions. `Suspended` is a different state (new puts
   create a null-version-id object, old versions are preserved).
   `NeverEnabled` → no versions exist, nothing to clean.
2. **Object Lock** — if `Compliance` mode is active with retention,
   versions CANNOT be deleted or overwritten until retention expires
   (not even by root). `Governance` mode permits deletion with
   `s3:BypassGovernanceRetention` permission.
3. **Legal holds** — per-object `LegalHold: ON` prevents deletion
   regardless of lifecycle, Object Lock mode, or retention. Check
   via `get-object-legal-hold` for specific objects.
4. **Existing lifecycle rules** — `put-bucket-lifecycle-configuration`
  **REPLACES** the entire configuration, not merges. Read existing
   rules first and merge new rules; otherwise you silently delete
   existing transitions/expirations.
5. **MFA Delete** — if `MFADelete: Enabled` on the bucket, version
   deletion and lifecycle rule changes require MFA. Plan for the
   additional auth step.
6. **Bucket Key** — `BucketKeyEnabled: true` reduces KMS request cost
   on encrypted buckets (~99% reduction). Recommend enabling alongside
   lifecycle changes.

**Cost/savings baselines (2026 us-east-1):**

- Standard storage: ~$0.023/GB-month.
- Standard-IA: ~$0.0125/GB-month (50% cheaper, but 30-day minimum +
  retrieval fee).
- Glacier Instant Retrieval: ~$0.004/GB-month (~83% cheaper).
- Glacier Flexible Retrieval: ~$0.0036/GB-month (~84% cheaper).
- Glacier Deep Archive: ~$0.00099/GB-month (~96% cheaper).
- One-time delete via lifecycle or Batch Operations: free (no per-delete
  charge).
- S3 Batch Operations: ~$1.00 per million objects processed.

**Rule of thumb:** versioned buckets with frequent overwrites
accumulate noncurrent versions at the same rate as the overwrite
frequency × object size. A 1 GB log file overwritten hourly = 24
noncurrent versions/day × $0.023/GB ≈ $0.55/month — scales linearly
with overwrite count.

## Mindset

**One-line takeaway:** versioned buckets accumulate noncurrent versions
indefinitely at standard storage rates — version cleanup is the #1 S3
cost optimization after storage-class transitions. Driven by four
realities:

- **Every noncurrent version bills at full Standard rate by default.**
  Unlike S3 IA or Glacier, noncurrent versions are NOT automatically
  tiered. A 1 GB file overwritten 100 times is 100 GB of Standard
  storage — 100x the cost of the current version alone.
- **Object Lock Compliance mode is irrevocable.** If Compliance mode is
  active with retention until 2030, no one (including root, including
  AWS support) can delete those versions before 2030. This is the
  correct posture for ransomware-resilient backups — and a hard block
  for version cleanup.
- **`put-bucket-lifecycle-configuration` REPLACES, not merges.** Every
  operator who forgets this silently deletes the existing lifecycle
  rules — transitions, expirations, abort-multipart rules — and the
  bucket reverts to "no lifecycle" until the operator notices (usually
  via a cost spike months later).
- **Legal holds override everything.** A single `LegalHold: ON` on one
  object blocks its deletion regardless of Object Lock mode, retention,
  lifecycle rules, or root access. Legal holds are per-object; bulk
  cleanup requires checking each object (or using Batch Operations with
  a manifest).

## Pre-flight: bucket metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-object-versions` paginates at 1000 keys/page —
drain `--key-marker` and `--version-id-marker` to completion. Use S3
Storage Lens for account-wide noncurrent version metrics instead of
enumerating every bucket.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws s3api get-bucket-versioning --bucket <name>` — confirm
   `Status: Enabled`. Capture `MFADelete` (if enabled, plan for MFA).
2. `aws s3api get-bucket-lifecycle-configuration --bucket <name>` —
   capture existing rules. NEVER overwrite without first reading.
3. `aws s3api get-object-lock-configuration --bucket <name>` — capture
   `ObjectLockEnabled` and `Rule.DefaultRetention` (Mode, Days, Years).
4. `aws s3api get-public-access-block --bucket <name>` — context only.
5. `aws s3api get-bucket-encryption --bucket <name>` — capture
   `BucketKeyEnabled` (recommend enabling if false and SSE-KMS in use).
6. `aws s3api list-object-versions --bucket <name --max-keys 1000` —
   sample the noncurrent version count and average size for impact
   estimation.
7. `aws s3control get-storage-lens-configuration --config-id default`
   — capture account-level `NoncurrentVersionCount` and
   `NoncurrentVersionStorageBytes`.
8. For specific objects being cleaned: `aws s3api get-object-legal-hold
   --bucket <name> --key <key> --version-id <vid>` — verify no legal
   hold before batch-delete.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Bucket/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws s3api get-bucket-versioning
--bucket <name> --output json and re-plan.`

| Bucket attribute | Effect on operation |
|---|---|
| `Status: Enabled` (versioning) | Cleanup proceeds normally. Noncurrent versions are eligible for lifecycle rules. |
| `Status: Suspended` | New puts create a null-version-id object (replacing the prior null version, which becomes noncurrent). OLD versions from before suspension are still preserved. Lifecycle rules apply only to noncurrent versions created before suspension. Plan carefully — typically the operator should re-enable versioning before cleanup. |
| Versioning never enabled | No versions exist. Nothing to clean. Emit BLOCKED with "versioning never enabled — no noncurrent versions to clean up". |
| `MFADelete: Enabled` | Version deletion and lifecycle rule changes require MFA. Plan for additional auth step (MFA token in CLI call). |
| `ObjectLockEnabled: Enabled`, `DefaultRetention.Mode: COMPLIANCE` | Versions within the retention window CANNOT be deleted by anyone — BLOCKED for in-retention versions. Lifecycle rules still apply to versions PAST retention. |
| `ObjectLockEnabled: Enabled`, `DefaultRetention.Mode: GOVERNANCE` | Versions can be deleted with `s3:BypassGovernanceRetention` permission. Lifecycle rules apply normally; Governance mode provides a softer guardrail. |
| Object-level `LegalHold: ON` | That specific version cannot be deleted by anyone. Lifecycle rules skip it silently. Bulk cleanup must check each object. |
| Existing lifecycle rules referencing the same prefix | `put-bucket-lifecycle-configuration` REPLACES. Merge new rules into the existing config or you silently delete existing transitions. |
| `BucketKeyEnabled: false` with SSE-KMS | Each noncurrent version incurs a KMS `GenerateDataKey` charge on access. Recommend enabling Bucket Key alongside lifecycle changes. |
| Bucket in a different AWS account | Caller needs cross-account IAM permissions on both sides. Verify before planning. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious S3 versioning behaviors

These behaviors are easy to misjudge without operational S3
experience. Each changes a plan if ignored:

- **Noncurrent versions bill at Standard rate by default.** Unlike
  intelligent tiering or lifecycle transitions, noncurrent versions
  stay in Standard storage until you explicitly tier or expire them.
  This is why version cleanup is the #1 S3 cost optimization.

- **`put-bucket-lifecycle-configuration` REPLACES, not merges.** This
  is the single most common S3 lifecycle mistake. Read existing rules
  via `get-bucket-lifecycle-configuration` first, merge new rules into
  the JSON, then PUT the merged configuration. Otherwise you silently
  delete existing transitions/expirations.

- **`NewerNoncurrentVersions` keeps only N most recent noncurrent
  versions.** This is the recommended rule for cost optimization
  without losing recent history: keep 3 noncurrent versions, expire the
  rest. Combine with `NoncurrentVersionTransition` to move the kept
  versions to IA/Glacier for further savings.

- **`NoncurrentVersionExpiration` deletes permanently.** Once expired,
  noncurrent versions are gone — no recovery, no Glacier archive. Use
  `NoncurrentVersionTransition` first if you need a softer cleanup
  path. The default is "no expiration" (versions persist indefinitely).

- **`AbortIncompleteMultipartUpload` cleans up orphaned uploads.**
  Multipart uploads that never complete bill at Standard rate for the
  uploaded parts — indefinitely. A 7-day abort window is the standard
  recommendation. This is a separate rule type from
  NoncurrentVersionExpiration.

- **`NoncurrentDays` counts from when the version BECAME noncurrent.**
  Not from object creation. A version that became noncurrent yesterday
  has `NoncurrentDays: 1`, regardless of when the object was first
  created.

- **Lifecycle rules apply once per day, not in real time.** S3
  processes lifecycle rules asynchronously, typically within 24 hours
  of eligibility. A rule with `NoncurrentDays: 30` may take 30-31
  days plus up to 24 hours of processing lag before the version is
  actually transitioned or expired.

- **S3 Batch Operations for immediate cleanup.** For immediate version
  deletion (not via lifecycle), use `aws s3control create-job` with an
  S3 Inventory manifest of noncurrent versions and the
  `S3DeleteObjectVersion` operation. Cost: ~$1.00 per million objects
  processed.

- **Object Lock Compliance mode is irrevocable.** Versions in
  Compliance mode cannot be deleted by ANYONE (including root,
  including AWS support) until retention expires. Governance mode is
  the softer alternative — deletion requires
  `s3:BypassGovernanceRetention` permission, which can be granted and
  revoked. Choose Governance for "trust but verify" workflows;
  Compliance for "absolutely immutable" workloads.

- **Object Lock legal hold is per-object, not bucket-wide.** A
  `LegalHold: ON` on one object blocks its deletion regardless of
  lifecycle, Object Lock mode, or retention. Bulk cleanup must check
  each object (or use a manifest-based Batch Operations job that
  filters by legal-hold status).

- **Versioning `Suspended` is NOT the same as never enabled.** When
  versioning is suspended, new puts create a null-version-id object
  (replacing the prior null version, which becomes noncurrent).
  Versions from before suspension are still preserved. Lifecycle rules
  behave differently on suspended buckets — typically the operator
  should re-enable versioning before cleanup.

- **Delete markers are themselves versions.** Deleting a versioned
  object creates a new "delete marker" version (the object appears
  deleted) but does NOT remove prior versions. To actually delete
  data, you must delete the specific versions OR configure
  NoncurrentVersionExpiration. Cleaning up delete markers themselves
  is a separate operation.

- **S3 Storage Lens is the canonical impact estimator.** Use the
  `NoncurrentVersionCount` and `NoncurrentVersionStorageBytes`
  dimensions to estimate savings before applying rules.
  `BucketSizeBytes` by storage class shows where cost is concentrated.

- **Glacier Instant Retrieval vs Glacier Flexible Retrieval.** GIR
  (~$0.004/GB) is for data accessed once a quarter with ms latency;
  Flexible (~$0.0036/GB) is for data accessed once or twice a year
  with 1-5 minute restore. Choose based on access pattern, not just
  cost. For noncurrent versions, GIR is usually the right first
  transition.

- **Bucket Key reduces KMS cost ~99%.** On SSE-KMS buckets, every
  S3 request that accesses an object triggers a KMS API call. Bucket
  Key uses a transient data key cached at the bucket level, reducing
  KMS request charges. Always recommend enabling Bucket Key alongside
  lifecycle changes on encrypted buckets.

- **Cross-region replication preserves versions.** If the bucket has
  Cross-Region Replication (CRR) or Same-Region Replication (SRR),
  lifecycle rules apply independently on source and destination.
  Cleaning up source versions does NOT clean up replica versions —
  apply the same lifecycle rules to the destination bucket.

- **S3 Intelligent-Tiering has its own noncurrent version handling.**
  Intelligent-Tiering automatically moves noncurrent versions to the
  Archive Access and Deep Archive tiers after 90 days — no explicit
  lifecycle rule needed. This is an alternative to manual lifecycle
  rules for buckets where the access pattern is unknown.

- **`put-bucket-lifecycle-configuration` validates XML, not business
  logic.** The API rejects malformed XML but does not warn about rule
  conflicts (two rules matching the same prefix with different
  actions), impossible transitions (Standard → Glacier before 30 days
  of Standard-IA minimum), or missing dependencies. Verify the rules
  in the console or via `get-bucket-lifecycle-configuration` after
  PUT.

- **`Expiration` (current version) vs `NoncurrentVersionExpiration`
  (noncurrent versions).** They are different rule actions.
  `Expiration` deletes the current version (creating a delete marker
  on a versioned bucket); `NoncurrentVersionExpiration` deletes old
  versions. Conflating them causes the wrong cleanup.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
BLOCKED with the failed checks enumerated in PRE_CHECKS. Do NOT
execute the operation.

**For ALL operations:**
1. Caller has `s3:GetBucketVersioning`, `s3:GetLifecycleConfiguration`,
   `s3:PutLifecycleConfiguration` on the bucket ARN.
2. Bucket exists in the expected region and account.
3. Bucket name is correct (S3 bucket names are globally unique;
   verify the region matches the expectation).

**For configure-lifecycle (add/modify lifecycle rules):**
4. Versioning state is `Enabled` (or `Suspended` with explicit
   acknowledgment — see Step 0 for behavior differences).
5. Existing lifecycle rules captured via
   `get-bucket-lifecycle-configuration` — new rules must be MERGED
   into the existing config, not REPLACE it.
6. No conflicting rules (same prefix + overlapping actions with
   different NoncurrentDays values).
7. Object Lock configuration captured — Compliance-mode retention
   overrides NoncurrentVersionExpiration for in-retention versions.

**For batch-delete-versions (immediate cleanup via Batch Operations):**
4. Versioning state is `Enabled`.
5. S3 Inventory configured OR a manifest generated via
   `list-object-versions` (paginated). Batch Operations needs a
   manifest of object-key + version-id pairs.
6. No Object Lock Compliance-mode versions in the manifest (delete
   would fail per-object; the job continues but reports failures).
7. No legal-hold ON objects in the manifest (same per-object failure
   behavior).
8. IAM role for Batch Operations has `s3:DeleteObjectVersion` on the
   bucket AND `iam:PassRole` to assign the execution role.

**For estimate-savings (impact audit):**
4. S3 Storage Lens enabled at the account or bucket level.
5. Sample `list-object-versions` captured (1000 keys) to estimate
   average version count and size.

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI/JSON
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with the merged lifecycle JSON.
- The estimated monthly savings (computed from noncurrent version
  count × average size × storage rate).
- The expected timeline (lifecycle rules apply within 24 hours of
  eligibility; Batch Operations jobs run in minutes-to-hours).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI,
  emit: `CONFIRM: About to <operation> on bucket <name> in account
  <account> region <region>. This will <consequence>. Estimated
  monthly savings: $<amount>. Proceed? (yes/no)`. Do NOT execute
  until the operator confirms.
- Capture pre-state for audit:
  `aws s3api get-bucket-lifecycle-configuration --bucket <name>
  --output json > /tmp/<name>-lifecycle-pre-$(date +%s).json`.
- Execute the CLI. For `put-bucket-lifecycle-configuration`, PUT
  the merged JSON (NEVER the new rules alone). For Batch Operations,
  capture the JobId.
- Verify the operation:
  `get-bucket-lifecycle-configuration` shows the new rules;
  `describe-job` shows Batch Operations progress.

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `get-bucket-lifecycle-configuration --bucket <name>` — confirm
   the new rules are present AND existing rules are preserved (no
   silent deletion).
2. For Batch Operations: `aws s3control describe-job --account-id
   <acct> --job-id <id>` — confirm `Status: Complete`,
   `NumberOfTasksSucceeded` matches expected.
3. Wait 24-48 hours, then re-check Storage Lens
   `NoncurrentVersionCount` and `NoncurrentVersionStorageBytes` —
   they should drop.
4. Verify no compliance violations (Object Lock retention respected,
   no legal-hold objects deleted).
5. Verify the expected cost drop in AWS Cost Explorer (S3 service,
   filtered by bucket tag or usage type) — allow 1-3 days for billing
   lag.
6. For lifecycle rules: verify the rule prefix filter is correct
   (does not accidentally match unintended prefixes).
7. Document the savings in NOTES for the operator's reporting.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Output format (per operation)

```text
OPERATION: <configure-lifecycle | batch-delete-versions | estimate-savings | audit-versions>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ESTIMATED_SAVINGS: <$X/month (computed from N noncurrent versions × avg size × rate)>
NOTES: <compliance caveats, Object Lock implications, cleanup timeline>
```

### Worked example — configure lifecycle (3-rule cleanup)

```text
OPERATION: configure-lifecycle
VERDICT: READY
TARGET: s3://prod-logs-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] MFADelete: Disabled (no MFA required)
  - [PASS] ObjectLockEnabled: Disabled (no Compliance/Governance retention)
  - [PASS] Existing lifecycle rules captured (3 rules: current-version
    transition, current-version expiration on logs/ prefix, abort-
    multipart-upload 7d)
  - [PASS] New rules MERGED into existing config (not replacing)
  - [PASS] BucketKeyEnabled: true (no KMS optimization gap)
  - [PASS] Caller has s3:PutLifecycleConfiguration
STEPS:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on
     s3://prod-logs-bucket in account 111111111111 region us-east-1.
     This will ADD NoncurrentVersionExpiration (keep 3, expire rest
     after 90d) and NoncurrentVersionTransition (Standard-IA after 30d,
     Glacier Instant Retrieval after 90d) to the existing 3 rules.
     Existing rules preserved. Estimated monthly savings: $312/month
     (~13.5 TB noncurrent versions × $0.023/GB). Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket \
       --lifecycle-configuration file:///tmp/prod-logs-bucket-merged-lifecycle.json
  3. aws s3api get-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket --output json
POST_VERIFY:
  - (pending execution)
ESTIMATED_SAVINGS: $312/month (13.5 TB noncurrent × $0.023/GB-month;
  after transition to IA + GIR: $95/month; net savings $217/month)
NOTES:
  - Lifecycle rules apply within 24 hours of eligibility. Allow 24-48
    hours for the first noncurrent versions to transition/expire.
  - The 3-rule pattern (NewerNoncurrentVersions=3 + Transition to IA
    at 30d + Transition to GIR at 90d) preserves 3 recent versions,
    moves mid-aged versions to cheaper storage, and expires old ones.
  - The existing 3 rules are PRESERVED in the merged config —
    verified by reading the post-PUT lifecycle configuration.
  - S3 Storage Lens will show NoncurrentVersionCount and
    NoncurrentVersionStorageBytes dropping over 1-2 weeks.
  - For immediate cleanup of versions already older than 90d, use
    S3 Batch Operations (separate operation).
```

### Worked example — Object Lock BLOCKED

```text
OPERATION: batch-delete-versions
VERDICT: BLOCKED
TARGET: s3://compliance-archive-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] Manifest generated (10,000 noncurrent versions via
    list-object-versions pagination)
  - [FAIL] ObjectLockEnabled: Enabled, DefaultRetention: Mode=COMPLIANCE,
    Years=5. Versions within retention CANNOT be deleted by anyone
    (including root). Manifest contains 4,287 in-retention versions
    that the Batch Operations job cannot delete.
  - [SKIP] Legal hold check skipped (Object Lock Compliance already
    blocks deletion)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ESTIMATED_SAVINGS: $0 (Compliance retention overrides cleanup)
NOTES:
  - Compliance mode is irrevocable. No one can delete the in-retention
    versions until 2031-08-09.
  - Options:
    (a) Wait for retention to expire, then re-run Batch Operations.
    (b) Apply NoncurrentVersionTransition lifecycle rules — versions
        PAST retention will transition to IA/Glacier automatically.
        In-retention versions remain in Standard until retention
        expires, then transition.
    (c) For Governance-mode buckets (not this case), delete with
        s3:BypassGovernanceRetention permission.
  - Recommend: lifecycle NoncurrentVersionTransition (IA at 30d past
    retention, GIR at 90d past retention) as the only viable cleanup
    path for Compliance-mode buckets.
```

### Worked example — Batch Operations immediate cleanup

```text
OPERATION: batch-delete-versions
VERDICT: READY
TARGET: s3://staging-uploads-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] ObjectLockEnabled: Disabled
  - [PASS] Manifest generated: 2,500,000 noncurrent versions via
    S3 Inventory (2026-08-08 snapshot)
  - [PASS] No legal holds (sampled 1000 objects, all OFF)
  - [PASS] Caller has s3control:CreateJob + iam:PassRole
  - [PASS] Execution role has s3:DeleteObjectVersion on the bucket
STEPS:
  1. CONFIRM: About to create S3 Batch Operations job to delete
     2,500,000 noncurrent versions in s3://staging-uploads-bucket
     (account 111111111111, region us-east-1). Cost: ~$2.50 ($1.00
     per million objects). Estimated savings: $825/month (35 TB ×
     $0.023/GB). Proceed? (yes/no)
  2. aws s3control create-job \
       --account-id 111111111111 \
       --operation '{"S3DeleteObjectVersion": {}}' \
       --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "staging-uploads-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/staging-uploads-inventory/2026-08-08/manifest.json"}}' \
       --report "{\"Bucket\":\"arn:aws:s3:::batch-ops-reports\",\"Prefix\":\"staging-uploads-cleanup-2026-08-09/\",\"Format\":\"Report_CSV_20180820\",\"Enabled\":true,\"ReportScope\":\"AllTasks\"}" \
       --priority 50 \
       --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole \
       --client-request-token $(uuidgen)
  3. Poll: aws s3control describe-job --account-id 111111111111 \
       --job-id <returned-id>
     Wait for Status: Complete.
POST_VERIFY:
  - (pending execution)
ESTIMATED_SAVINGS: $825/month (35 TB × $0.023/GB-month)
NOTES:
  - Batch Operations runs in minutes-to-hours depending on object
    count. Monitor via describe-job.
  - The job reports per-object success/failure — review the report CSV
    in batch-ops-reports/staging-uploads-cleanup-2026-08-09/.
  - Object Lock Compliance-mode versions (if any) fail per-object; the
    job continues but reports failures.
  - Pair this immediate cleanup with a lifecycle rule to prevent
    future accumulation.
```

## Anti-Patterns — NEVER

- NEVER execute `put-bucket-lifecycle-configuration` without first
  reading the existing rules via `get-bucket-lifecycle-configuration`.
  The PUT REPLACES the entire configuration — silently deleting
  existing transitions and expirations is the #1 S3 lifecycle mistake.

- NEVER attempt to delete versions in an Object Lock Compliance-mode
  bucket within the retention window. NO ONE — including root,
  including AWS support — can delete them. Apply lifecycle
  transitions instead; versions past retention will transition.

- NEVER attempt to delete objects with `LegalHold: ON`. Legal hold
  overrides all lifecycle and Object Lock settings. Check via
  `get-object-legal-hold` before any bulk delete; the operation fails
  per-object.

- NEVER conflate `Expiration` (current version) with
  `NoncurrentVersionExpiration` (noncurrent versions). `Expiration`
  creates a delete marker on versioned buckets; it does NOT remove old
  versions. The wrong rule cleans up nothing.

- NEVER assume `NewerNoncurrentVersions` alone is sufficient. It keeps
  only the N most recent noncurrent versions but does NOT transition
  them to cheaper storage. Pair with
  `NoncurrentVersionTransition` for full savings.

- NEVER recommend Glacier Flexible Retrieval when the access pattern
  needs ms latency. GIR (~$0.004/GB) supports ms-latency GETs;
  Flexible (~$0.0036/GB) requires 1-5 minute restore. Choose by access
  pattern, not just cost.

- NEVER skip the `MFADelete` check. If MFADelete is enabled, version
  deletion and lifecycle rule changes require an MFA token in the CLI
  call — the operation fails without it.

- NEVER assume version cleanup is always safe for compliance. Financial
  / regulatory workloads may REQUIRE keeping all versions for N years
  (use Object Lock). Verify retention requirements before enabling
  expiration.

- NEVER recommend S3 Batch Operations without estimating the per-
  million-object cost (~$1.00/million). A 1-billion-object cleanup is
  $1,000 — sometimes more than the savings.

- NEVER assume `list-object-versions` is the right manifest source for
  Batch Operations on large buckets. Use S3 Inventory (daily or weekly
  CSV snapshots) for buckets with millions of versions — paginating
  `list-object-versions` is too slow and consumes API quota.

- NEVER forget to apply lifecycle rules to the REPLICA bucket. CRR/SRR
  replicates versions but lifecycle rules are independent per bucket.
  Cleaning the source does NOT clean the replica.

- NEVER assume lifecycle rules apply in real time. S3 processes rules
  asynchronously within 24 hours of eligibility. A rule with
  `NoncurrentDays: 30` may take 30-31 days plus up to 24 hours of
  processing lag.

- NEVER conflate versioning `Suspended` with never-enabled. Suspended
  buckets have versions from before suspension (still preserved) and
  null-version-id objects from after. Re-enable versioning before
  cleanup for predictable behavior.

- NEVER recommend disabling Bucket Key on an encrypted bucket. Bucket
  Key reduces KMS request charges ~99% with no security downside. If
  `BucketKeyEnabled: false`, recommend enabling as part of the same
  operation.

- NEVER execute `delete-objects` without specifying version IDs on a
  versioned bucket. Without version IDs, the call creates delete
  markers rather than deleting data — the underlying versions remain
  and continue to bill.

- NEVER skip the cross-account IAM check. S3 bucket policies and the
  caller's IAM policy BOTH must permit the operation. A bucket policy
  denying `s3:PutLifecycleConfiguration` blocks the operation even if
  IAM allows it.

- NEVER assume Intelligent-Tiering is free. Intelligent-Tiering charges
  a per-object monitoring fee (~$0.0025 per 1,000 objects/month for
  the Monitor/Auto-Tiering). For small objects (<128 KB), the
  monitoring fee can exceed the storage savings.

- NEVER auto-execute a state-changing S3 CLI without the CONFIRM gate.
  Lifecycle PUTs and Batch Operations jobs have side effects (silent
  deletion of existing rules, immediate version deletion). Always emit
  CONFIRM and wait.

- NEVER skip the post-PUT lifecycle verification. A malformed
  lifecycle JSON can be silently rejected or partially applied. Always
  re-read the lifecycle config and verify the new rules + preserved
  existing rules.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-lifecycle-configuration`, `delete-objects`,
  `aws s3control create-job`, `put-bucket-versioning`), emit:
  `CONFIRM: About to <operation> on bucket <name> in account <account>
  region <region>. This will <consequence>. Estimated monthly savings:
  $<amount>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture pre-state for rollback.** Before any lifecycle change:
  `aws s3api get-bucket-lifecycle-configuration --bucket <name>
  --output json > /tmp/<name>-lifecycle-pre-$(date +%s).json`.
  Lifecycle state is not versioned — a wrong PUT silently replaces.

- **Verify versioning BEFORE cleanup.** `Status: Enabled` is the
  expected state. `Suspended` and never-enabled have different
  cleanup semantics.

- **Verify Object Lock BEFORE any delete.** `ObjectLockEnabled:
  Enabled` with `DefaultRetention.Mode: COMPLIANCE` blocks in-retention
  deletion irrevocably. Governance mode allows bypass with
  `s3:BypassGovernanceRetention`.

- **Verify legal holds BEFORE Batch Operations.** Sample the manifest
  with `get-object-legal-hold` to ensure no `LegalHold: ON` objects
  are in scope.

- **Verify existing lifecycle rules BEFORE PUT.** Read via
  `get-bucket-lifecycle-configuration`. Merge new rules into the
  existing config; never PUT new rules alone.

- **Plan the cleanup timeline BEFORE promising savings.** Lifecycle
  rules apply within 24 hours of eligibility. For immediate cleanup,
  use Batch Operations (separate operation, separate cost).

- **Verify the rule prefix BEFORE PUT.** A rule with `prefix: ""`
  applies to ALL objects in the bucket. A rule with `prefix: logs/`
  applies only to objects under `logs/`. Verify the prefix matches
  intent — too narrow misses versions, too broad affects unintended
  objects.

## Recent AWS features (2024-2026)

- **S3 Intelligent-Tiering Archive Access default (2024-2025):** New
  buckets with Intelligent-Tiering now default to moving noncurrent
  versions to Archive Access after 90 days automatically. Operators
  should verify whether Intelligent-Tiering is in use before adding
  manual lifecycle rules — duplicate rules can conflict.

- **S3 Glacier Instant Retrieval lifecycle rule GA (2024):**
  NoncurrentVersionTransition to GIR is fully supported as a lifecycle
  target. GIR provides ms-latency GETs at ~$0.004/GB-month — the
  recommended first transition for noncurrent versions.

- **S3 Batch Operations expanded operations (2024-2025):** Batch
  Operations now supports `S3DeleteObjectVersion` natively (previously
  required a custom Lambda). Cost remains ~$1.00 per million objects.

- **S3 Object Lock Governance mode enhancements (2024):** Governance
  mode now logs bypass attempts to CloudTrail by default. Operators
  should verify CloudTrail S3 data event logging is enabled for audit.

- **S3 Storage Lens dashboard improvements (2024-2025):** Storage Lens
  now includes `NoncurrentVersionCount` and
  `NoncurrentVersionStorageBytes` as top-level dimensions. Operators
  should enable Storage Lens at the account level (free tier) before
  planning version cleanup.

- **Bucket Key default for new SSE-KMS buckets (2024-2025):** New
  SSE-KMS buckets default to `BucketKeyEnabled: true`. Older buckets
  may still have it disabled — verify and enable to reduce KMS
  request charges ~99%.

- **S3 Lifecycle rule priority warnings (2025):** The S3 console now
  warns about conflicting lifecycle rules (same prefix, overlapping
  NoncurrentDays). The CLI/API still does not warn — verify rules
  manually after PUT.

## Domain

AWS CloudOps / S3 Storage Cost Optimization & Compliance Retention.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **S3 Versioning** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- **S3 Lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-operations.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html
- **AWS CLI s3api reference** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
- **Bucket Key** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-key.html
