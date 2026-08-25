---
name: s3-replication-operator
description: Operates S3 cross-region replication (CRR) and same-region replication (SRR) end-to-end — rule configuration (priority, filter prefix/tags, status), source/destination requirements (versioning on BOTH buckets, same or different region/account), IAM replication role (s3:ReplicateObject, s3:ReplicateDelete, s3:ObjectOwnerOverrideToBucketOwner, KMS decrypt/encrypt), Replication Time Control (RTC, 15 min SLA, CloudWatch PendingReplication metrics), batch replication of existing objects via S3 Batch Operations, delete-marker replication (optional, separate config), replica modification sync, cross-account destination bucket policy (s3:x-amz-source-account condition), and S3 Replication to multiple destinations. Runs deterministic pre-checks behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict. Use when configuring CRR/SRR rules, diagnosing replication not happening, batching existing objects, or wiring cross-account replication.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws s3api get-bucket-replication, put-bucket-replication, get-bucket-versioning, get-bucket-encryption, get-bucket-location, aws s3control create-job (Batch Operations), aws cloudwatch get-metric-statistics (RTC metrics), and aws kms describe-key / get-key-policy (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Configuring or modifying a replication rule (CRR or SRR), diagnosing objects not replicating, setting up batch replication for existing objects, wiring cross-account destination bucket policy, enabling Replication Time Control and reading its CloudWatch metrics, deciding whether delete-marker replication should be on, configuring replica modification sync, or designing S3 Replication to multiple destination buckets.
  activation_triggers: configure S3 replication, cross-region replication, CRR setup, same-region replication, SRR setup, objects not replicating, replication is broken, batch replicate existing objects, S3 Batch Operations replication, cross-account replication, destination bucket policy replication, Replication Time Control, RTC metrics, delete marker replication, replica modification sync, S3 multiple destinations, PendingReplication metric, versioning required for replication
  invocation_schema: 'Input: either (a) a source bucket configuration (get-bucket-replication, get-bucket-versioning, get-bucket-encryption, get-bucket-location) plus the intended operation (add-rule, update-rule, enable-rtc, batch-replicate, diagnose-not-replicating, configure-cross-account, enable-delete-marker-replication), OR (b) a source + destination bucket pair for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3 replication, cross-region replication, CRR, same-region replication, SRR, ReplicationTimeControl, RTC, replication rule, filter prefix, delete marker replication, replica modification sync, batch replication, S3 Batch Operations, cross-account replication, destination bucket policy, s3:ReplicateObject, s3:ReplicateDelete, KMS decrypt, PendingReplication, multiple destinations, versioning enabled, OwnershipControls
  tags: aws, s3, storage, replication, crr, srr, kms, cross-account, backup, dr, operate
---

# S3 Replication Operator

## What this skill does

Executes S3 replication operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (source AND
destination versioning, source bucket Region match against rule, IAM
replication role permission chain including KMS decrypt on source and
encrypt on destination, destination bucket policy for cross-account,
OwnershipControls for object ownership, delete-marker replication
config), executes the rule change behind a CONFIRM gate, and verifies
the result by tailing the S3 replication CloudWatch metrics
(`PendingReplication`, `OperationPendingReplicationCount`,
`BytesPendingReplication`) and confirming a sample object appears in the
destination. Every add-rule produces a rule-config expectation; every
diagnose-not-replicating surfaces the failure-mode table so the operator
knows where to look (rule status, versioning, IAM role, KMS key policy,
destination bucket policy).

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why replication is a four-link chain, the false-green-rule trap, the confirm gate | Understanding the safety model |
| **§ Pre-flight** | Source + destination metadata gate — versioning, encryption, location, ownership | Before executing any CLI |
| **§ Process** | Per-operation planning: add-rule, update-rule, enable-rtc, batch-replicate, diagnose, cross-account, delete-markers | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand objects or break replication silently | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, IAM role policy, KMS key policy, destination bucket policy | Defense-in-depth |
| **§ Expert heuristic** | Replication is async + eventually-consistent — never assume success from the API alone | Avoiding the false-green trap |

## STRICT output contract

EVERY response MUST end with a single fenced text block in this exact
shape (the operator's downstream tooling greps for it). No deviations:

```text
OPERATION: <add-rule | update-rule | enable-rtc | batch-replicate | diagnose-not-replicating | configure-cross-account | enable-delete-marker-replication>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-bucket> -> <destination-bucket> (rule id: <id-or-"new">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated, or "(none — pre-checks failed)">
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description> | (pending execution)
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

Rules of the contract:

- VERDICT is exactly one of `READY`, `BLOCKED`, `COMPLETED`. No other
  values. `READY` means pre-checks passed and a CONFIRM gate is
  pending; `BLOCKED` means at least one pre-check failed — do NOT
  emit STEPS that mutate state; `COMPLETED` means post-verification
  passed after execution.
- If PRE_CHECKS has any `[FAIL]`, VERDICT MUST be `BLOCKED` and STEPS
  MUST be `(none — pre-checks failed)`.
- If VERDICT is `READY`, STEPS[1] MUST be the CONFIRM prompt and
  STEPS[2] MUST be the actual CLI.
- If VERDICT is `COMPLETED`, POST_VERIFY MUST contain at least one
  `[PASS]` and no `[FAIL]`.
- Never wrap the block in JSON, never abbreviate the field names,
  never omit a section. If a section is empty, write `(none)`.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (source or destination versioning off, IAM replication role missing `s3:ReplicateObject`/`s3:ReplicateDelete`, KMS decrypt/encrypt gap, cross-account destination bucket policy denies source account role, source bucket not in the rule's Region, OwnershipControls mismatch, rule `Status: Disabled` with no filter match) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Rule change applied AND post-verification passed (sample object replicated, `PendingReplication` drained or stable, delete-marker test passed when configured) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Versioning on BOTH buckets.** Source AND destination must have
   `Status: Enabled`. Suspend is treated as disabled for replication
   purposes.
2. **Source bucket Region matches the rule's source.** A rule created on
   `bucket-A` in `us-east-1` cannot be applied to `bucket-B` in
   `eu-west-1`.
3. **Destination bucket exists and is in the expected Region/account.**
   For CRR the Region MUST differ from source; for SRR it MUST match.
4. **IAM replication role permission chain.** Role must have
   `s3:ReplicateObject`, `s3:ReplicateDelete`, and (cross-account)
   `s3:ObjectOwnerOverrideToBucketOwner` on the destination ARN; and
   `s3:GetObjectVersion`, `s3:GetObjectVersionAcl`, `s3:GetReplicationConfiguration` on the source ARN.
5. **KMS decrypt path on source.** For SSE-KMS source objects, the role
   needs `kms:Decrypt` on the source key ARN.
6. **KMS encrypt path on destination.** The role needs `kms:Encrypt` on
   the destination key ARN AND the destination key policy must grant
   the role.
7. **Destination bucket policy (cross-account).** Must allow the source
   account's replication role to `s3:ReplicateObject`,
   `s3:ReplicateDelete`, `s3:ObjectOwnerOverrideToBucketOwner`, AND the
   `s3:x-amz-source-account` condition key for the source account.
8. **OwnershipControls.** For cross-account, destination should have
   `ObjectOwnership: BucketOwnerPreferred` or `ObjectOwnerEnforced` so
   the destination account owns replicas (otherwise replicas are owned
   by the source account and are unreadable to the bucket owner).
9. **Rule status + filter.** Rule `Status` is `Enabled` and the filter
   (prefix and/or tags) actually matches the objects the operator
   expects to replicate.
10. **RTC validity (for enable-rtc).** RTC requires a replication rule
    that is `Enabled`; once RTC is on, the SLA is 15 minutes for
    99.99% of objects.

→ Cost/time baselines moved to [references/advanced-patterns.md](references/advanced-patterns.md).


## Mindset

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the four-link-chain mindset behind every verdict.


## Pre-flight: source + destination metadata gate

Run before classification. Misclassifying these produces wrong plans.

→ Pagination guidance and the 10-command live-account pre-flight listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md); the attribute table below is the gate itself.



→ Malformed-input error contract moved to [references/error-handling.md](references/error-handling.md).


| Bucket attribute | Effect on operation |
|---|---|
| Source `Status` absent (versioning off) | add-rule BLOCKED. Existing rules are silently inert. |
| Destination `Status: Suspended` | Replication halts. Either re-enable versioning or pick a new destination. |
| `LocationConstraint` returns null | Source is `us-east-1` (the legacy default). Do not assume `aws-global`. |
| Destination in same Region as source with CRR rule | Misclassified CRR. Use SRR (same `Region` in the rule) or pick a different-Region destination. |
| `ObjectOwnership: BucketOwnerEnforced` | ACLs are disabled; replicas are owned by destination account automatically. Preferred for cross-account. |
| `ObjectOwnership: ObjectWriter` (legacy) | Cross-account replicas are owned by source account; destination account cannot read them. Update to `BucketOwnerPreferred` minimum. |
| SSE-S3 (no KMS) source | KMS decrypt pre-check is skipped; SSE-KMS still requires it. |
| Rule `Status: Disabled` | Rule exists but is inert. Diagnose-not-replicating surfaces this immediately. |
| `DeleteMarkerReplication.Status: Disabled` | Delete markers are NOT replicated even though objects are. Update-rule if deletes must propagate. |
| `Filter.Prefix` empty AND no Tag filter | Rule applies to the entire bucket. Confirm intent before applying — replication cost scales with bytes. |
| Rule `Priority` collision (two rules, same prefix) | The higher Priority wins for overlapping objects. Verify intent. |
| `PendingReplication` non-zero and stable | Backlog not draining — investigate IAM, KMS, or destination policy. |
| `PendingReplication` non-zero and decreasing | Healthy backlog — RTC SLA still applies. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious S3 replication behaviors

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive (non-obvious replication behaviors).


### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Source bucket exists and is in the account/Region the operator
   expects.
2. Source bucket versioning `Status: Enabled`.
3. IAM role ARN in `ReplicationConfiguration.Role` exists and is
   assumable by the `s3.amazonaws.com` service principal.

**For add-rule (new `put-bucket-replication` with a new rule):**
4. Destination bucket exists in the expected Region.
5. Destination bucket versioning `Status: Enabled`.
6. Destination `ObjectOwnership` is `BucketOwnerEnforced` or
   `BucketOwnerPreferred` (cross-account only).
7. IAM role has `s3:GetReplicationConfiguration`,
   `s3:GetObjectVersion`, `s3:GetObjectVersionAcl` on source ARN.
8. IAM role has `s3:ReplicateObject`, `s3:ReplicateDelete` on
   destination ARN.
9. (Cross-account) IAM role has
   `s3:ObjectOwnerOverrideToBucketOwner` on destination ARN.
10. (SSE-KMS source) IAM role has `kms:Decrypt` on source key; source
    key policy grants the role.
11. (SSE-KMS destination) IAM role has `kms:Encrypt` on destination
    key; destination key policy grants the role.
12. (Cross-account) Destination bucket policy allows source account's
    role with `s3:x-amz-source-account` condition.
13. Existing `ReplicationConfiguration` rules preserved (full-replace
    API — capture pre-state).
14. New rule `Priority` does not collide with existing rule Priorities.
15. If enabling RTC: `ReplicationTime.Time.Minutes` is 15 and
    `Metrics.EventThreshold.Minutes` is 15.

**For update-rule (modify an existing rule's filter, status, or
destination):**
4. The rule `ID` exists in the current configuration.
5. New destination (if changing) passes the add-rule pre-checks.
6. Pre-state captured for rollback (the entire prior
   `ReplicationConfiguration`).

**For enable-rtc:**
4. At least one rule has `Status: Enabled`.
5. RTC not already enabled on the rule (idempotent check).

**For batch-replicate (existing objects via S3 Batch Operations):**
4. S3 Inventory configured on the source (provides the manifest).
5. The Batch Operations IAM role has `s3:GetObject`,
   `s3:ReplicateObject`, KMS decrypt on source key, KMS encrypt on
   destination key.
6. Manifest object exists and is recent (< 24 hours old).
7. No in-flight batch-replicate job covers the same prefix.

**For diagnose-not-replicating (read-only, no BLOCKED gate):**
4. Read the failure-mode table to identify the root cause.

**For configure-cross-account:**
4. Destination bucket policy exists or is being created.
5. Destination `ObjectOwnership` is `BucketOwnerEnforced` or
   `BucketOwnerPreferred`.
6. (SSE-KMS) Destination KMS key policy grants the source account's
   role.

**For enable-delete-marker-replication:**
4. Existing rule found by `ID` or filter.
5. Pre-state captured (rule is being replaced).

**Replication failure-mode table (use during diagnose-not-replicating):**

→ Failure-mode table moved to [references/error-handling.md](references/error-handling.md) — symptom → root cause → fix, 13 rows.


### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the source +
  destination configuration. For `put-bucket-replication` this is the
  merged JSON config (existing rules + new rule).
- The expected latency (small objects 5-15 seconds; RTC P99 15 minutes;
  batch 1-5 seconds per object).
- The expected side-effects (new objects matching the filter begin
  replicating immediately; existing objects remain UNLESS batch is
  run).
- The CONFIRM gate prompt.
- The monitoring step (CloudWatch metrics tail for RTC; S3 Server
  Access Logs for non-RTC).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`put-bucket-replication`, `delete-bucket-replication`,
  `put-bucket-ownership-controls`, `put-bucket-policy`,
  `s3control create-job`), emit:
  `CONFIRM: About to <operation> on source <source> / destination
  <destination> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws s3api get-bucket-replication
  --bucket <source> --output json > /tmp/<source>-repl-$(date +%s).json`.
- Execute the CLI. For `put-bucket-replication`, the API returns
  immediately; actual replication runs asynchronously.
- Tail the replication metrics (RTC only):
  `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name
  PendingReplication --dimensions ... --start-time <now-15m> --end-time
  <now> --period 60 --statistics Sum`.

### Step 4: Post-verification — COMPLETED

After the rule change, run post-verification. ALL checks must pass for
`COMPLETED`.

1. Put a test object in the source matching the rule's filter.
2. `aws s3api head-object --bucket <destination> --key <test-key>`
   returns 200 within 60 seconds (or 15 minutes for RTC).
3. Confirm version ID in destination matches the source version ID.
4. For RTC: confirm `PendingReplication` drained (or remained at zero
   if the test object was the only PUT).
5. For delete-marker replication: delete the test object in the source,
   confirm the delete marker appears in the destination.
6. For cross-account: confirm the destination account can read the
   replica (no AccessDenied).
7. For replica modification sync: update a tag on the source, confirm
   the tag change appears in the destination.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. Route the failure back to
diagnose-not-replicating.

## Output format (per operation)

See § STRICT output contract above. The block MUST appear exactly in
that shape.

### Worked example — add-rule (cross-region, SSE-KMS, RTC enabled)

```text
OPERATION: add-rule
VERDICT: READY
TARGET: prod-logs-source-us-east-1 -> prod-logs-dr-eu-west-1
        (rule id: new — "dr-crr-rtc")
PRE_CHECKS:
  - [PASS] Source bucket exists in us-east-1
  - [PASS] Source versioning Status: Enabled
  - [PASS] Destination bucket exists in eu-west-1
  - [PASS] Destination versioning Status: Enabled
  - [PASS] Destination ObjectOwnership: BucketOwnerEnforced
  - [PASS] IAM role arn:aws:iam::111111111111:role/s3-repl-role has
    s3:GetReplicationConfiguration + s3:GetObjectVersion on source
  - [PASS] IAM role has s3:ReplicateObject + s3:ReplicateDelete on
    arn:aws:s3:::prod-logs-dr-eu-west-1/*
  - [PASS] IAM role has kms:Decrypt on source key
    arn:aws:kms:us-east-1:111111111111:key/source-cmk
  - [PASS] IAM role has kms:Encrypt on destination key
    arn:aws:kms:eu-west-1:111111111111:key/dest-cmk
  - [PASS] Destination key policy grants role kms:Encrypt
  - [PASS] ReplicationTime.Time.Minutes: 15, Metrics.EventThreshold.Minutes: 15
  - [PASS] Existing rules (1) preserved in merged config
STEPS:
  1. CONFIRM: About to add replication rule "dr-crr-rtc" on
     prod-logs-source-us-east-1 (us-east-1) replicating to
     prod-logs-dr-eu-west-1 (eu-west-1) with RTC (15 min SLA). This
     applies to NEW objects only; existing objects require a Batch
     Operations job. Proceed? (yes/no)
  2. aws s3api put-bucket-replication --bucket prod-logs-source-us-east-1 \
       --replication-configuration file:///tmp/prod-logs-source-us-east-1-repl-merged.json
  3. aws cloudwatch get-metric-statistics --namespace AWS/S3 \
       --metric-name PendingReplication \
       --dimensions Name=SourceBucket,Value=prod-logs-source-us-east-1 \
       --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
       --period 60 --statistics Sum
POST_VERIFY: (pending execution)
NOTES:
  - This rule replicates only NEW objects matching prefix "logs/".
    Existing objects (e.g., 4.2 TB of historical logs) require a Batch
    Operations S3ReplicateObject job. Generate the manifest from S3
    Inventory (config id: prod-logs-inventory-daily) and create the
    job AFTER this rule is applied.
  - RTC SLA: 99.99% of objects replicate within 15 minutes. CloudWatch
    alarms on PendingReplication > 0 for > 15 minutes recommended.
  - Cross-account NOT detected — both buckets in account 111111111111.
    If destination moves to account 222222222222, also attach a
    destination bucket policy with s3:x-amz-source-account condition.
```

### Worked example — diagnose-not-replicating (BLOCKED with fix)

→ Secondary worked example moved to [references/worked-examples.md](references/worked-examples.md).


### Worked example — configure-cross-account (COMPLETED)

→ Secondary worked example moved to [references/worked-examples.md](references/worked-examples.md).


## Anti-Patterns — NEVER

- NEVER call `put-bucket-replication` without first reading the existing
  `ReplicationConfiguration`. The API is full-replacement; calling it
  with only the new rule wipes ALL existing rules on the bucket,
  silently halting other replication streams. Always merge, sort by
  Priority, and put the merged config.

- NEVER assume `Status: Enabled` on a replication rule means objects
  are replicating. The rule is a claim; the only proof is a `head-object`
  on the destination returning the same version ID. Always run a test
  PUT after creating or modifying a rule.

- NEVER assume existing objects replicate when a new rule is added.
  S3 replication only catches NEW PUTs. Existing objects require a
  Batch Operations `S3ReplicateObject` job. This is the single most
  common misclassification.

- NEVER assume delete markers replicate. `DeleteMarkerReplication.Status`
  defaults to `Disabled`. If the operator expects deletes to propagate,
  explicitly set it to `Enabled`.

- NEVER assume tag updates replicate. `SourceSelectionCriteria.ReplicaModifications.Status`
  must be `Enabled`; otherwise metadata edits on the source diverge
  silently from the replica.

- NEVER configure cross-account replication with only the IAM role
  policy. The destination bucket policy MUST grant the source account's
  role with the `s3:x-amz-source-account` condition. The role policy is
  necessary but not sufficient.

- NEVER leave destination `ObjectOwnership` at `ObjectWriter` (legacy
  ACL mode) for cross-account replication. Replicas end up owned by
  the source account; the destination account cannot read or delete
  them. Set `BucketOwnerEnforced` or `BucketOwnerPreferred` AND include
  `s3:ObjectOwnerOverrideToBucketOwner`.

- NEVER grant the replication role `kms:Encrypt` without also updating
  the destination KMS key policy to grant the role. IAM identity-based
  policy alone is not sufficient for cross-account KMS keys.

- NEVER suspend versioning on a source bucket with active replication
  rules. Replication halts immediately and the backlog may not resume
  on re-enable. Run a Batch Operations job to backfill after
  re-enabling.

- NEVER enable Object Lock on the source AFTER replication is already
  running without first enabling it on the destination. The destination
  rejects the locked object and replication fails silently.

- NEVER rely on CloudWatch `Replication` metrics without RTC enabled.
  The `PendingReplication`, `OperationPendingReplicationCount`, and
  `BytesPendingReplication` metrics are ONLY emitted when RTC is on.
  Without RTC, use S3 Server Access Logs.

- NEVER use overlapping filter prefixes without explicit `Priority`
  assignment. The lower-Priority rule is silently masked; objects under
  the overlap only replicate to the higher-Priority destination.

- NEVER assume `get-bucket-replication` returns rules in Priority order.
  S3 returns them in insertion order. Always sort by `Priority` before
  editing and re-putting.

- NEVER auto-execute a state-changing S3 replication CLI without the
  CONFIRM gate. Rule changes, ownership-control changes, and bucket
  policy changes can halt or misdirect existing replication streams.

- NEVER create a Batch Operations manifest by hand. Use S3 Inventory
  (daily CSV). Hand-built manifests miss deleted versions and
  overwrite existing replicas with stale data.

- NEVER replicate to a destination in the same Region as the source if
  the intent is disaster recovery. Same-Region replication is a backup
  pattern, not DR.

- NEVER trust `LocationConstraint: null` as an error. It means the
  bucket is in `us-east-1` (the legacy default Region where the field
  is omitted). Hard-coded Region assumptions produce wrong CRR vs SRR
  classifications.

## Pre-flight safety checks (run before any remediation CLI)

→ Pre-flight safety checklist moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).


## Expert heuristic: the false-green rule

Replication is async and eventually-consistent. The single highest-
leverage rule for operating it safely is:

> A replication rule with `Status: Enabled` is a CONFIGURATION claim,
> not a DELIVERY claim. The only proof of replication is a `head-object`
> on the destination returning the source's version ID, combined with
> `PendingReplication` draining to zero (RTC) or stable. Treat any
> dashboard that shows "rule Enabled" as a health signal worth less
> than a single end-to-end test PUT.

**Why this rule exists:** S3 evaluates replication rules asynchronously
after the initial PUT completes. Failures in the IAM role, KMS key
policy, destination bucket policy, or versioning state do NOT fail the
PUT — the source object is stored successfully, and the replication
failure is recorded only in S3 Server Access Logs (or CloudWatch if RTC
is on). Dashboards that surface "replication: Enabled" are reading the
rule status, not the delivery status.

→ Verification-technique table, three-bucket protocol, and silent-failure detection moved to [references/advanced-patterns.md](references/advanced-patterns.md).


## Recent AWS features (2024-2026)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (2024-2026).


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, mindset deep dive, cost/time baselines, false-green verification protocol, recent AWS features.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (diagnose-not-replicating BLOCKED, configure-cross-account COMPLETED).
- [references/error-handling.md](references/error-handling.md) — malformed-input contract and the replication failure-mode table.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pagination notes, 10-command live-account pre-flight, pre-remediation safety checks.
- [references/diagnostic-procedures.md](references/diagnostic-procedures.md) — pre-existing; per-failure-mode diagnostic procedures and failure-mode routing.
- [references/rule-config-templates.md](references/rule-config-templates.md) — pre-existing; full JSON rule templates, IAM role policies, Batch Operations manifests.

## Domain

AWS CloudOps / S3 Replication, Cross-Region DR, and Same-Region Backup.

## AWS documentation

- **S3 Replication Developer Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html
- **Replication configuration** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-add-config.html
- **Replication Time Control (RTC)** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-time-control.html
- **Cross-Region replication** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-crr.html
- **Same-Region replication** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-srr.html
- **Replicating existing objects with S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-batch-replication-batch.html
- **Cross-account replication** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-walkthrough-2.html
- **Replica modification sync** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-for-metadata-changes.html
- **Delete marker replication** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-delete-markers.html
- **S3 Replication to multiple destinations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication-mult-destinations.html
- **S3 Batch Operations** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops.html
- **S3 API Reference** — https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html
- **S3 CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/s3api/
