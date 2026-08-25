---
name: s3-version-cleanup-operator
description: Operates S3 version cleanup for cost optimization and compliance — NoncurrentVersionExpiration, NoncurrentVersionTransition, NewerNoncurrentVersions, AbortIncompleteMultipartUpload lifecycle rules, S3 Batch Operations for immediate version delete, Object Lock (Compliance vs Governance mode) and legal-hold handling, versioning-state pre-checks (Enabled vs Suspended), Storage Lens impact estimation, and post-apply verification. Runs deterministic pre-checks (versioning enabled, Object Lock mode and retention, legal holds, existing lifecycle rule conflicts, BucketKeyEnabled for cost), executes the operation behind a CONFIRM gate, and emits a verdict (READY | BLOCKED | COMPLETED) per bucket with the exact CLI/JSON sequence, estimated monthly savings, and verification commands. Use when auditing noncurrent version accumulation, configuring version cleanup lifecycle rules, planning immediate cleanup via Batch Operations, handling Object Lock retention, or estimating S3 version cleanup savings.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws s3api get-bucket-versioning, put-bucket-versioning, get-bucket-lifecycle-configuration, put-bucket-lifecycle-configuration, get-object-lock-configuration, get-object-legal-hold, list-object-versions, delete-objects, and aws s3control create-job (S3 Batch Operations) (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: s3, storage, versioning, lifecycle, cost-optimization, object-lock, batch-operations
  dependencies: aws-orchestrator
  keywords: S3, versioning, noncurrent versions, NoncurrentVersionExpiration, NoncurrentVersionTransition, NewerNoncurrentVersions, lifecycle rule, AbortIncompleteMultipartUpload, S3 Batch Operations, Object Lock, Compliance mode, Governance mode, legal hold, S3 Storage Lens, cost optimization, version cleanup, delete markers, BucketKeyEnabled
  when_to_use: Auditing S3 noncurrent version accumulation, configuring version cleanup lifecycle rules (NoncurrentVersionExpiration, NoncurrentVersionTransition, NewerNoncurrentVersions), planning immediate version cleanup via S3 Batch Operations, handling Object Lock retention before cleanup, estimating S3 version cleanup savings, or hardening S3 cost posture on versioned buckets.
  activation_triggers: clean up S3 versions, S3 noncurrent versions cost, configure S3 lifecycle NoncurrentVersionExpiration, S3 version cleanup, S3 Object Lock retention, S3 legal hold, S3 Batch Operations delete versions, S3 cost optimization versions, S3 Storage Lens noncurrent, abort multipart upload S3, S3 NewerNoncurrentVersions, versioned bucket cleanup, S3 lifecycle configuration
  invocation_schema: 'Input: either (a) a bucket configuration with the intended operation (configure-lifecycle, batch-delete-versions, audit- versions, estimate-savings), OR (b) a bucket name + operation for live-account execution. Output: deterministic OPERATION/VERDICT/ PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
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

These behaviors are easy to misjudge without operational S3 experience.
Each changes a plan if ignored. See `references/lifecycle-rule-patterns.md`
for full lifecycle JSON anatomy and the
NoncurrentVersionExpiration-vs-NewerNoncurrentVersions heuristic. Summary:

- **Noncurrent versions bill at Standard rate by default** — they are
  NOT auto-tiered; version cleanup is the #1 S3 cost optimization.
- **`put-bucket-lifecycle-configuration` REPLACES, not merges** — the
  single most common lifecycle mistake. Always read-merge-write.
- **`NoncurrentVersionExpiration` deletes permanently** — no recovery,
  no Glacier archive. Use `NoncurrentVersionTransition` first for a
  softer path. Default is "no expiration" (indefinite billing).
- **`NewerNoncurrentVersions` keeps only N recent noncurrent versions**
  — pair with `NoncurrentVersionTransition` for full savings. Combine
  with `NoncurrentVersionExpiration` for defense in depth (caps count
  AND age).
- **`AbortIncompleteMultipartUpload` cleans orphaned uploads** —
  orphans bill at Standard rate indefinitely; 7-day abort window is
  standard.
- **`NoncurrentDays` counts from when the version BECAME noncurrent**,
  not from object creation.
- **Lifecycle rules apply asynchronously within 24 hours** of
  eligibility, not in real time.
- **Batch Operations for immediate cleanup** — ~$1.00/million objects;
  see `references/lifecycle-rule-patterns.md` for cost-comparison table.
- **Object Lock Compliance mode is irrevocable** — no one (including
  root) can delete in-retention versions. Governance mode allows bypass
  with `s3:BypassGovernanceRetention`.
- **Legal hold is per-object, not bucket-wide** — bulk cleanup must
  check each object or use a manifest-based Batch Operations job.
- **Versioning `Suspended` ≠ never enabled** — suspended buckets have
  pre-suspension versions (preserved) and null-version-id objects;
  re-enable versioning before cleanup.
- **Delete markers are themselves versions** — deleting a versioned
  object creates a delete marker but does NOT remove prior versions.
- **Storage Lens is the canonical impact estimator** — use
  `NoncurrentVersionCount` and `NoncurrentVersionStorageBytes`.
- **GIR vs Glacier Flexible Retrieval** — GIR (~$0.004/GB, ms latency)
  for quarterly access; Flexible (~$0.0036/GB, 1-5 min restore) for
  annual. Choose by access pattern, not just cost.
- **Bucket Key reduces KMS cost ~99%** — always recommend enabling on
  SSE-KMS buckets alongside lifecycle changes.
- **CRR/SRR preserves versions independently** — apply lifecycle rules
  to BOTH source and replica; cleaning source does NOT clean replica.
- **Intelligent-Tiering auto-archives noncurrent versions at 90 days**
  — alternative to manual rules for unknown access patterns.
- **`put-bucket-lifecycle-configuration` validates XML, not business
  logic** — does not warn about rule conflicts or impossible
  transitions; verify via `get-bucket-lifecycle-configuration` after PUT.
- **`Expiration` (current) ≠ `NoncurrentVersionExpiration`** —
  `Expiration` creates a delete marker on versioned buckets and does
  NOT remove old versions.

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

### Worked examples (see references/worked-examples.md)

Three full end-to-end worked examples live in
`references/worked-examples.md`:

- **READY — configure lifecycle (3-rule cleanup).** Demonstrates
  NewerNoncurrentVersions=3 + NoncurrentVersionTransition to IA and
  GIR, merged into 3 existing rules. ~$312/month savings.
- **BLOCKED — Object Lock Compliance mode.** Shows the irrevocable
  retention block, enumerates the 4,287 in-retention versions, and
  recommends NoncurrentVersionTransition as the only viable path.
- **READY — Batch Operations immediate cleanup.** 2.5M noncurrent
  versions via S3 Inventory manifest; ~$2.50 Batch Operations cost;
  ~$825/month savings.

Each example demonstrates the exact PRE_CHECKS, STEPS with CONFIRM
gate, POST_VERIFY, and NOTES for the verdict shape.

## STRICT output contract

This contract is mandatory. The Output format template above is the
authoritative structure; the rules below disambiguate the failure
modes that score D8=13 on this skill. Violating any rule produces a
plan that is unsafe to execute.

### Required output structure

Every operation MUST emit this exact block, with all fields populated
(no empty fields, no omitted sections, no reordering):

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
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ESTIMATED_SAVINGS: <$X/month (computed from N versions × avg size × rate)>
NOTES: <compliance caveats, Object Lock implications, cleanup timeline>
```

Verdict-specific rules:
- `BLOCKED` → at least one PRE_CHECKS line shows `[FAIL]` with a
  concrete reason; STEPS is `(none — pre-checks failed)`; no
  state-changing CLI is emitted.
- `READY` → all PRE_CHECKS show `[PASS]`; STEPS begins with the
  CONFIRM gate prompt before any state-changing CLI; POST_VERIFY is
  `(pending execution)`; ESTIMATED_SAVINGS cites the storage math.
- `COMPLETED` → all POST_VERIFY show `[PASS]`; STEPS reflects what
  was actually executed; ESTIMATED_SAVINGS is the realised (not
  estimated) savings if measurable.

### FORBIDDEN output patterns

1. NEVER recommend NoncurrentVersionExpiration without checking Object
   Lock — Compliance mode makes versions immutable regardless of
   lifecycle rules. A READY plan that did not run
   `get-object-lock-configuration` and confirm the mode is invalid.
2. NEVER suggest put-bucket-lifecycle-configuration as a merge — it
   REPLACES the entire configuration. Always read-merge-write: call
   `get-bucket-lifecycle-configuration`, merge the new rules into the
   existing JSON, then PUT the merged payload. A STEPS entry that PUTs
   only the new rules is a data-loss bug.
3. NEVER conflate `Expiration` (current version) with
   `NoncurrentVersionExpiration` (noncurrent versions). `Expiration`
   creates a delete marker on versioned buckets; it does NOT remove
   old versions. A STEPS entry using the wrong action cleans up
   nothing.
4. NEVER emit `VERDICT: READY` without the CONFIRM gate as the first
   STEPS item. State-changing CLIs (lifecycle PUT, `delete-objects`,
   `create-job`) require explicit operator approval before execution;
   emitting the CLI without the CONFIRM prompt is a violation.
5. NEVER attempt to delete objects with `LegalHold: ON`. Legal hold
   overrides all lifecycle and Object Lock settings. A batch-delete
   plan that did not sample `get-object-legal-hold` is incomplete —
   per-object failures will occur silently mid-job.
6. NEVER output `VERDICT: BLOCKED` without enumerating each failed
   PRE_CHECK with a `[FAIL]` line and a reason. A bare "BLOCKED —
   pre-checks failed" with no itemised failures is not actionable.
7. NEVER assume lifecycle rules apply in real time. S3 processes
   rules asynchronously within 24 hours of eligibility. A COMPLETED
   verdict that claims immediate cost reduction without the 24-48h
   verification window is misleading.

### Perfect example output

```text
OPERATION: configure-lifecycle
VERDICT: READY
TARGET: s3://prod-logs-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] MFADelete: Disabled (no MFA required)
  - [PASS] ObjectLockEnabled: Disabled (no Compliance/Governance
    retention — NoncurrentVersionExpiration is safe)
  - [PASS] Existing lifecycle rules captured (3 rules: current-version
    transition, current-version expiration on logs/ prefix,
    abort-multipart-upload 7d) via get-bucket-lifecycle-configuration
  - [PASS] New rules MERGED into existing config (not replacing) —
    PUT payload contains all 5 rules
  - [PASS] BucketKeyEnabled: true (no KMS optimization gap)
  - [PASS] Caller has s3:PutLifecycleConfiguration
STEPS:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on
     s3://prod-logs-bucket in account 111111111111 region us-east-1.
     This will ADD NoncurrentVersionExpiration (NoncurrentDays: 90)
     and NoncurrentVersionTransition (STANDARD_IA at 30d, GIR at 90d)
     to the existing 3 rules. Existing rules preserved in the merged
     payload. Estimated monthly savings: $312/month. Proceed? (yes/no)
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
  - The existing 3 rules are PRESERVED in the merged config — verified
    by reading the post-PUT lifecycle configuration in Step 3.
  - For immediate cleanup of versions already older than 90d, use S3
    Batch Operations (separate operation).
```

## Anti-Patterns — NEVER (top 5)

1. **NEVER execute `put-bucket-lifecycle-configuration` without first
   reading existing rules.** The PUT REPLACES the entire configuration
   — silently deleting existing transitions and expirations is the #1
   S3 lifecycle mistake. Always read-merge-write.

2. **NEVER attempt to delete versions in an Object Lock Compliance-mode
   bucket within the retention window.** NO ONE — including root,
   including AWS support — can delete them. Apply lifecycle transitions
   instead; versions past retention will transition.

3. **NEVER attempt to delete objects with `LegalHold: ON` or conflate
   `Expiration` with `NoncurrentVersionExpiration`.** Legal hold
   overrides all settings (check via `get-object-legal-hold`). 
   `Expiration` creates a delete marker on versioned buckets; it does
   NOT remove old versions — use `NoncurrentVersionExpiration`.

4. **NEVER auto-execute a state-changing S3 CLI without the CONFIRM
   gate, and NEVER skip the post-PUT lifecycle verification.** Lifecycle
   PUTs and Batch Operations jobs have side effects; a malformed JSON
   can be silently rejected. Always emit CONFIRM, wait, then re-read.

5. **NEVER recommend S3 Batch Operations without estimating the
   per-million-object cost (~$1.00/million) and never use
   `list-object-versions` as the manifest source for large buckets.**
   Use S3 Inventory for buckets with millions of versions; paginating
   `list-object-versions` is too slow and consumes API quota.

Additional NEVER rules (MFADelete check, compliance retention
verification, GIR vs Flexible latency, CRR/SRR replica lifecycle,
Intelligent-Tiering monitoring fee, Bucket Key, `delete-objects` with
version IDs, cross-account IAM) appear in the FORBIDDEN output
patterns section above and in `references/lifecycle-rule-patterns.md`.

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

## Expert heuristic and Batch Operations cost (see references/lifecycle-rule-patterns.md)

The full NoncurrentVersionExpiration-vs-NewerNoncurrentVersions
heuristic (with defense-in-depth JSON example and common-mistake
analysis) and the S3 Batch Operations per-million-object cost
comparison table (with payback-period maths and decision rule) live
in `references/lifecycle-rule-patterns.md`.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **S3 Versioning** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html
- **S3 Lifecycle configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-operations.html
- **S3 Storage Lens** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage_lens.html
- **AWS CLI s3api reference** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
- **Bucket Key** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-key.html
