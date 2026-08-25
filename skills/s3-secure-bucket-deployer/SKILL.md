---
name: s3-secure-bucket-deployer
description: 'Provisions S3 buckets with production-grade security defaults: Block Public Access (account + bucket, all 4 settings), default encryption (SSE-S3 or SSE-KMS with customer key), versioning with optional MFA delete, Object Ownership = BucketOwnerEnforced (ACLs disabled), access logging + CloudTrail data events, HTTPS-only bucket policy, SSE-KMS upload enforcement, lifecycle rules for cost optimization, and cross-region / same-region replication. Emits a READY_TO_DEPLOY checklist with every configuration item verified against the bucket''s actual state, plus copy-pasteable provisioning and verification commands. Use when creating a new S3 bucket, hardening an existing bucket before production, validating that a bucket meets security baseline, or generating a Terraform / CloudFormation skeleton with correct defaults. Triggers: create S3 bucket, provision S3, secure bucket, S3 deployment, bucket encryption, SSE-KMS, BPA, lifecycle, replication, production bucket setup.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with s3api, s3control, kms, cloudtrail, and iam access. Works with Terraform aws_s3_bucket resources and CloudFormation AWS::S3::Bucket templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: deploy
  skill_class: capability
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, s3, cloudops, deploy, security, bpa, encryption, sse-kms, versioning, lifecycle, replication, bucket-policy
  dependencies: aws-orchestrator
  keywords: aws, s3, cloudops, deploy, provisioning, security, block-public-access, bpa, encryption, sse-kms, sse-s3, bucket-owner-enforced, versioning, mfa-delete, lifecycle, replication, crr, bucket-policy, secure-transport, access-logging
  when_to_use: Invoke when the user wants to create a new S3 bucket with security defaults, harden an existing bucket to production baseline, validate a bucket configuration before go-live, generate provisioning CLI commands or IaC templates for a secure bucket, or verify that a bucket's current configuration matches the security baseline. Do NOT invoke for auditing public-access exposure (use s3-public-access-auditor), or for non-S3 storage (EBS, EFS, FSx).
---

# S3 Secure Bucket Deployer

An AWS CloudOps agent skill that provisions S3 buckets with correct
security defaults. The skill walks the operator through a 10-step
provisioning procedure, explains why each default matters, and emits a
READY_TO_DEPLOY checklist verifying every configuration item against the
bucket's actual state.

## Quick reference: provisioning summary (10 steps at a glance)

Detailed reasoning for each step's ordering is in the "Reasoning
framework" and "S3 configuration dependency graph" sections below.
The concise checklist for quick orientation:

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Block Public Access (account + bucket) | Yes | data leak window |
| 2 | Default encryption (SSE-S3 or SSE-KMS) | Yes | unencrypted objects |
| 3 | Object Ownership = BucketOwnerEnforced | Yes* | ACL-based exposure |
| 4 | Versioning (+ optional MFA Delete) | Yes | no recovery from overwrite |
| 5 | Bucket policy (HTTPS + SSE enforcement) | Yes | insecure uploads |
| 6 | Access logging + CloudTrail data events | Yes | no audit trail |
| 7 | Lifecycle rules | Yes | cost bloat |
| 8 | Replication (optional CRR/SRR) | Yes | no DR |
| 9 | Verification (all configs confirmed) | — | silent failures |
| 10 | Emit READY_TO_DEPLOY checklist | — | — |

\* BucketOwnerEnforced is reversible but existing ACL-based access breaks
silently and immediately on enable — audit before flipping.

**Critical ordering constraints:** BPA before any object upload;
encryption before any object upload; versioning before lifecycle and
replication; replication last (depends on all prior steps). Full
rationale in the dependency graph below. Full bucket-policy JSON
templates live in `references/bucket-policy-examples.md` — only summary
tables are shown inline to keep the procedure scannable.

## Activation keywords

create S3 bucket, provision S3, secure bucket, S3 deployment, block public
access, BPA, SSE-KMS, SSE-S3, default encryption, BucketOwnerEnforced,
Object Ownership, S3 versioning, MFA delete, S3 lifecycle, storage class
transition, S3 replication, CRR, SRR, HTTPS-only bucket policy,
aws:SecureTransport, S3 access logging, CloudTrail data events, S3
security baseline, production bucket setup.

## Invocation contract (hard requirement)

When this skill is invoked with a bucket-provisioning request (bucket
name, workload type, region, or a partial existing configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in
§"Output format" using the literal all-caps labels `BUCKET:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Reasoning framework (why the provisioning order matters)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the reasoning framework behind the 10-step order.


## S3 configuration dependency graph (novel heuristic)

S3 configurations are NOT independent. Many silently no-op or silently
degrade if their dependencies are missing — the API returns success in
all three "silent" rows below, which makes them especially dangerous.
Use this graph both to sequence provisioning and to debug
"why doesn't this work?" when a config appears applied but has no effect.

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Account-level BPA | none | — | overrides all bucket-level BPA relaxations |
| Bucket-level BPA | bucket exists | — | public-ACL / public-policy prevention |
| Default encryption (SSE-S3) | bucket exists | — | write-time encryption only |
| Default encryption (SSE-KMS) | bucket exists; KMS key ARN valid; key policy grants S3 | objects written before setting stay unencrypted | per-object CloudTrail KMS audit |
| Object Ownership = BucketOwnerEnforced | bucket exists | pre-existing ACL-based access silently breaks | disables ALL ACLs |
| Versioning | bucket exists | — | lifecycle non-current rules; replication; MFA Delete |
| Bucket policy | bucket exists; BPA must allow attach (Deny policies always pass) | — | HTTPS + SSE enforcement |
| Access logging | log target bucket exists in SAME region | **log target missing `s3:PutObject` grant to `logging.s3.amazonaws.com` → no logs, no error** | audit trail |
| CloudTrail data events | trail exists | trail in wrong region → silently no events | API-level audit trail |
| Lifecycle rules | versioning enabled (for non-current rules); respects min storage duration per class | **`NoncurrentVersion*` rules silently no-op without versioning** | cost optimization |
| Replication | versioning on source AND destination; destination bucket exists; IAM role with `s3:ReplicateObject` + KMS decrypt | **objects written before the rule was added are NOT backfilled — partial replication, no signal** | cross-region / same-region copy |
| MFA Delete | versioning enabled; caller is the ROOT account (not IAM user/role) | MFADelete=Enabled silently ignored if caller is not root | ransomware / accidental-delete protection |

**The three silent-failure rows are the ones a baseline model misses.**
Lifecycle, access logging, and replication backfill all return HTTP 200
on apply — only post-config verification (Step 9) catches the gap. This
is why the procedure verifies every configuration item against the
bucket's actual state rather than trusting the API response.

→ Cross-dependency gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).


## Expert heuristic: BPA timing window

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the BPA race window, CloudFormation/Terraform ordering, and the account-level-BPA fix.


## Expert heuristic: SSE-KMS Bucket Keys cost model

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — the $1K vs $1M/year KMS cost model.


## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a specific
gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with S3 access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | BPA and encryption are region-scoped | `aws configure get region` |
| KMS key ARN (if SSE-KMS) | Custom encryption requires a CMK | `aws kms list-aliases --query 'Aliases[?AliasName==`alias/s3`\]'` |
| Logging bucket exists | S3 server access logs need a target | `aws s3api head-bucket --bucket <log-bucket>` |
| Replication role (if CRR/SRR) | Replication needs an IAM role | `aws iam get-role --role-name <replication-role>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Block Public Access (account + bucket)

Enable BPA at BOTH account and bucket level. Account-level BPA is the
authoritative prevention layer.

→ Command listing moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md); rationale and common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).




### Step 2 — Default encryption

Choose SSE-S3 (free, AWS-managed) or SSE-KMS (customer-controlled key).

→ Command listing moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md); rationale and common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).




### Step 3 — Object Ownership = BucketOwnerEnforced

Disables ALL ACLs — the bucket owner always owns every object.

```bash
aws s3api put-bucket-ownership-controls \
  --bucket <BUCKET> \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

→ Rationale and common mistakes moved to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).



### Step 4 — Versioning

Enable versioning to keep every historical version of every object.
This is the foundation for lifecycle rules on non-current versions
(Step 7), replication (Step 8), and ransomware-resistant recovery.
MFA Delete is optional but recommended for production buckets holding
irreplaceable data.

→ Command listing moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md); rationale and common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).




### Step 5 — Bucket policy (HTTPS-only + SSE enforcement)

Apply a deny-style policy that blocks two upload vectors at once:
insecure transport (HTTP) and unencrypted object uploads. The policy
is DENY-based with `Principal: "*"` — this is safe because BPA at the
account level prevents anyone from attaching a more permissive policy
later, and the conditions are client-side requirements, not identity
requirements.

**Summary of statements** (full JSON, SSE-S3 variant, log-delivery
grant, and cross-account templates live in
`references/bucket-policy-examples.md`):

| Sid | Effect | Condition | Purpose |
|---|---|---|---|
| `DenyInsecureTransport` | Deny `s3:*` | `aws:SecureTransport == false` | force HTTPS on both bucket and object ARNs |
| `DenyUnEncryptedObjectUploads` | Deny `s3:PutObject` | `s3:x-amz-server-side-encryption` NOT in `["AES256","aws:kms"]` | force SSE header on every upload |

```bash
# Apply from a policy file (recommended — avoids shell-escaping bugs)
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://policy.json
```

→ Common mistakes moved to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).



### Step 6 — Access logging

Enable S3 server access logs for the data bucket (every request is
logged with requester, source IP, action, response code, bytes) AND
CloudTrail data events for the API-level audit trail. The log target
bucket must exist in the SAME region and must grant
`logging.s3.amazonaws.com` write access via bucket policy (ACL grants
do not work with `BucketOwnerEnforced`).

→ Command listing moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md); common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).




### Step 7 — Lifecycle rules

Apply lifecycle rules to transition objects through cheaper storage
classes over time and to expire non-current versions and incomplete
multipart uploads. Rules require versioning (Step 4) for any
`NoncurrentVersion*` action — without it the rule applies as a silent
no-op. Mind the minimum-storage-duration constraints per class
(STANDARD_IA: 30d, GLACIER: 90d, DEEP_ARCHIVE: 180d) or you will pay
early-deletion fees.

→ Lifecycle JSON template moved to [references/encryption-and-lifecycle-guide.md](references/encryption-and-lifecycle-guide.md); common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).


**Storage class guidance**:
- **Intelligent-Tiering**: unknown access patterns (auto-moves between tiers)
- **STANDARD_IA**: infrequent access (>30 days, >128KB objects)
- **GLACIER_IR**: quarterly access (90+ days)
- **GLACIER**: archival, minutes-to-hours retrieval (90+ days)
- **DEEP_ARCHIVE**: long-term retention, 12h retrieval (180+ days)



### Step 8 — Replication (optional, if CRR/SRR required)

Prerequisites: versioning enabled (Step 4), destination bucket with its
own security baseline, IAM role with replication permissions.

→ Command listing moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md); common mistakes to [references/advanced-patterns.md](references/advanced-patterns.md); failure triage to [references/error-handling.md](references/error-handling.md).




### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

→ Verification command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).


### Step 10 — Emit checklist

The agent outputs the READY_TO_DEPLOY checklist (see Output format below).

## NEVER do these things

These anti-patterns cause silent failures, exposure windows, or
compliance violations. Each one has been observed in production
incidents — the "why it's wrong" line is the post-mortem finding, not
hypothetical. Treat each as a hard rule.

1. **NEVER enable only bucket-level BPA without account-level BPA.**
   Why it's wrong: account-level BPA is authoritative — a future admin
   who relaxes account-level BPA immediately re-exposes every bucket
   that lacks its own bucket-level setting. Set both for defense-in-
   depth; the cost is one extra CLI call.

2. **NEVER upload objects before configuring default encryption.**
   Why it's wrong: bucket-level default encryption applies at write
   time only. Pre-existing objects stay unencrypted and remediation
   requires S3 Batch Operations Copy (slow, costly, and logged as a
   security incident in audits). Configure encryption BEFORE the first
   PutObject, ideally in the same CloudFormation / Terraform run as
   the bucket create.

3. **NEVER set `BucketOwnerEnforced` without auditing existing ACLs.**
   Why it's wrong: this setting disables ALL ACLs immediately and
   silently. Any cross-account writer relying on ACL-granted object
   ownership loses their workflow on the next PutObject — there is no
   deprecation window, no CloudTrail event beyond the ownership-change
   API call. Inventory `s3:GetObjectAcl` across all writers first;
   migrate those grants to the bucket policy before flipping.

4. **NEVER configure `NoncurrentVersion*` lifecycle rules without
   confirming versioning is `Enabled`.**
   Why it's wrong: the API accepts the rule and returns HTTP 200, but
   the rule is a silent no-op without versioning. You discover the
   miss weeks later via Storage Lens showing unbounded growth in old
   versions. Always check `get-bucket-versioning` immediately before
   `put-bucket-lifecycle-configuration`.

5. **NEVER configure replication if versioning is not enabled on BOTH
   source and destination buckets.**
   Why it's wrong: versioning on the source is required for the API
   call to succeed, but versioning on the DESTINATION is required for
   replicas to actually land. Worse, objects written to the source
   BEFORE the replication rule was added are NEVER backfilled — you
   get partial replication with no error signal. Run
   `ExistingObjectReplication: Enabled` (v2 config) or a Batch
   Operations Copy job to catch up.

6. **NEVER use SSE-KMS without `BucketKeyEnabled: true` on
   high-throughput buckets.**
   Why it's wrong: without Bucket Keys every PutObject triggers
   `kms:GenerateDataKey` ($0.03 / 10k calls + 50-100ms latency). At
   1M writes/day that is ~$1,095/year in KMS fees alone, and you risk
   hitting the KMS region throttle (5,500-10,000 req/s default),
   which surfaces as `ThrottlingException` on S3 writes. Bucket Keys
   cut KMS calls by ~99% with no security downside.

7. **NEVER attach a bucket policy with `Principal: "*"` and
   `Effect: "Allow"`, even briefly "to test".**
   Why it's wrong: a 30-second window with a public-allow policy is
   enough for internet scanners (GrayhatWarfare, Censys, Shodan) to
   enumerate the bucket and download objects. Use BPA + signed URLs +
   CloudFront Origin Access Control for any "public-ish" workload.
   Deny-style policies with `Principal: "*"` (used in Step 5) are safe
   because the condition gates the call; Allow-style is not.

8. **NEVER use the AWS-managed `aws/s3` KMS key for compliance
   workloads (HIPAA / PCI-DSS / SOC2 / FedRAMP).**
   Why it's wrong: you cannot customize the `aws/s3` key policy, so
   you lose the second access gate (`kms:Decrypt`) that makes SSE-KMS
   valuable for compliance. A principal with `s3:GetObject` can read
   any object encrypted with the managed key. Always provision a
   customer-managed CMK with an explicit key policy that grants
   `kms:Decrypt` only to authorized principals.

9. **NEVER delete the last KMS key referenced by a bucket's default
   encryption or bucket policy without draining the bucket first.**
   Why it's wrong: every GET / HEAD on an encrypted object fails with
   `AccessDenied` the moment the key enters `PendingDeletion` state.
   There is no recovery once the key's waiting period elapses — the
   data is cryptographically lost. Always disable encryption on the
   bucket, run a Batch Operations Copy to re-encrypt with a new key,
   verify, THEN schedule the old key for deletion.

## Output format

→ Compact template moved to [references/worked-examples.md](references/worked-examples.md); the STRICT output contract below is authoritative.


## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
BUCKET: <bucket-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Block Public Access (account-level): all 4 settings True
  [✓|✗] Block Public Access (bucket-level): all 4 settings True
  [✓|✗] Default encryption: SSE-S3 | SSE-KMS (<key-arn>)
  [✓|✗] Object Ownership: BucketOwnerEnforced
  [✓|✗] Versioning: Enabled (MFA Delete: Enabled|Disabled)
  [✓|✗] Bucket policy: HTTPS-enforce + SSE-enforce
  [✓|✗] Access logging: Enabled (target: <log-bucket>)
  [✓|✗] CloudTrail data events: Enabled
  [✓|✗] Lifecycle rules: <rule-summary> | None (optional)
  [✓|✗] Replication: CRR→<dest> | SRR→<dest> | None
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 10
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[OPTIONAL]` (not needed for this workload). Omitting a row
   implies it was not evaluated.

2. **NEVER mark an item `[✓]` without a corresponding verification
   command in `VERIFICATION_COMMANDS`.** If the checklist says
   `[✓] Access logging: Enabled`, the VERIFICATION_COMMANDS block MUST
   include the `aws s3api get-bucket-logging --bucket <BUCKET>` command
   that confirms it. A `[✓]` with no verification command is an
   unverified claim.

3. **NEVER mark Block Public Access as `[✓]` without confirming BOTH
   account-level AND bucket-level (all 4 settings each).** The
   checklist has two separate BPA rows for this reason. Marking only
   one `[✓]` and omitting the other is a non-compliant output.

4. **NEVER mark Access logging as `[✓]` without verifying the log
   target bucket's policy grants `logging.s3.amazonaws.com`
   `s3:PutObject`.** With `BucketOwnerEnforced` on the log target, ACL
   grants silently fail — S3 returns HTTP 200 but delivers zero logs.
   The REASON for `[✓]` must cite the policy grant, not just "logging
   enabled."

5. **NEVER mark Lifecycle rules as `[✓]` if versioning is `[✗]`.**
   `NoncurrentVersion*` lifecycle rules silently no-op without
   versioning — the API returns success but no objects transition. If
   versioning is `[✗]`, lifecycle MUST also be `[✗]` with a note
   citing the dependency.

6. **NEVER mark Replication as `[✓]` without confirming versioning on
   BOTH source AND destination buckets.** Replication requires
   versioning on both sides. Additionally, the replication IAM role
   must exist with `s3:ReplicateObject` + KMS decrypt permissions.

7. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] KMS key ARN not provided — operator must supply CMK ARN for
   SSE-KMS`. A bare `[✗]` with no explanation is non-compliant.

8. **NEVER mark Default encryption as `[✓] SSE-KMS` without
   `BucketKeyEnabled: true` on high-throughput buckets.** Without
   Bucket Keys, every PutObject triggers a `kms:GenerateDataKey` call
   ($0.03/10k + latency). The checklist MUST note Bucket Key status
   when SSE-KMS is selected.

### Perfect example output — READY_TO_DEPLOY

Every field below is complete and verifiable. Copy this shape exactly.

```text
BUCKET: prod-order-data
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Block Public Access (account-level): all 4 settings True
  [✓] Block Public Access (bucket-level): all 4 settings True
  [✓] Default encryption: SSE-KMS (alias/prod-s3-key, BucketKeyEnabled: true)
  [✓] Object Ownership: BucketOwnerEnforced
  [✓] Versioning: Enabled (MFA Delete: Disabled)
  [✓] Bucket policy: HTTPS-enforce (DenyInsecureTransport) + SSE-enforce (DenyUnEncryptedObjectUploads)
  [✓] Access logging: Enabled (target: s3-access-logs-prod, policy grants logging.s3.amazonaws.com)
  [✓] CloudTrail data events: Enabled (trail: management-events, ReadWriteType: All)
  [✓] Lifecycle rules: Standard→IA(30d)→GLACIER(90d), NoncurrentExpiration(90d), AbortMultipart(7d)
  [✓] Replication: CRR→prod-order-data-dr (us-west-2, versioning confirmed on destination)
VERIFICATION_COMMANDS:
  aws s3control get-public-access-block --account-id 111111111111
  aws s3api get-public-access-block --bucket prod-order-data
  aws s3api get-bucket-encryption --bucket prod-order-data
  aws s3api get-bucket-ownership-controls --bucket prod-order-data
  aws s3api get-bucket-versioning --bucket prod-order-data
  aws s3api get-bucket-policy --bucket prod-order-data
  aws s3api get-bucket-logging --bucket prod-order-data
  aws cloudtrail get-event-selectors --trail-name management-events
  aws s3api get-bucket-lifecycle-configuration --bucket prod-order-data
  aws s3api get-bucket-replication --bucket prod-order-data
```

### Perfect example output — PREREQUISITES_MISSING

→ Secondary worked example moved to [references/worked-examples.md](references/worked-examples.md).


**Self-check before emit:**
- [ ] All 10 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] BPA shows two separate rows (account + bucket)?
- [ ] No `[✓]` on Lifecycle if Versioning is `[✗]`?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features.


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — reasoning framework, dependency gotchas, BPA timing window, Bucket Keys cost model, per-step rationale, recent AWS features.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (PREREQUISITES_MISSING) and the compact output template.
- [references/error-handling.md](references/error-handling.md) — per-step failure triage (Steps 1-8).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 9 verification commands.
- [references/bucket-policy-examples.md](references/bucket-policy-examples.md) — pre-existing; full bucket-policy JSON templates.
- [references/encryption-and-lifecycle-guide.md](references/encryption-and-lifecycle-guide.md) — pre-existing; SSE decision matrix, Bucket Keys internals, lifecycle reference; extended with the Step 7 lifecycle template.
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — pre-existing; full 10-step CLI walkthrough; extended with command listings moved from SKILL.md.
