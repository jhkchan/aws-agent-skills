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

S3 configuration items have **dependency and timing semantics** that make
the provisioning order non-trivial. Applying configurations in the wrong
order creates windows of exposure or silently fails:

1. **Block Public Access FIRST** — BPA is the foundation. It prevents
   accidental public exposure during the rest of the setup. If you
   create a bucket, upload objects, and THEN enable BPA, there is a
   window where a misconfigured ACL or policy (or a race with a
   concurrent policy attach) exposes data. Enabling BPA at creation
   time closes this window before any data lands.

2. **Default encryption BEFORE any object upload** — server-side
   encryption is applied at write time. Objects written before default
   encryption is configured are NOT retroactively encrypted by the
   bucket-level setting. You would need S3 Batch Operations to encrypt
   existing objects after the fact.

3. **Object Ownership = BucketOwnerEnforced BEFORE granting cross-account
   write access** — this setting disables ALL ACLs on the bucket. If a
   cross-account writer has been using ACLs to share objects, setting
   BucketOwnerEnforced silently breaks that workflow. Set it early so
   all access flows through bucket policies from the start.

4. **Versioning BEFORE lifecycle rules and replication** — both lifecycle
   rules for non-current versions and S3 replication REQUIRE versioning
   to be enabled. Configuring either without versioning is a silent
   no-op (lifecycle) or an API error (replication).

5. **Bucket policy AFTER BPA** — the bucket policy enforces HTTPS-only
   and SSE-KMS on uploads. It is the enforcement layer; BPA is the
   prevention layer. Both are needed for defense-in-depth.

6. **Access logging EARLY** — logging captures all access events. The
   sooner it is enabled, the more audit trail you have. Log delivery
   requires a log-delivery ACL or bucket policy grant on the target
   logging bucket — set this up before the data bucket receives
   production traffic.

7. **Lifecycle AFTER versioning** — lifecycle rules that transition or
   expire non-current versions require versioning. Rules also have
   minimum-storage-duration constraints (STANDARD_IA: 30 days, GLACIER:
   90 days via STANDARD_IA transition). Configure lifecycle after
   versioning is confirmed enabled.

8. **Replication LAST** — replication requires versioning, a destination
   bucket with its OWN security baseline, and an IAM role with
   `s3:ReplicateObject` + KMS decrypt permissions. It is the most
   complex configuration and depends on all prior steps being correct.

The order matters because each layer DEPENDS ON or is STRENGTHENED BY
the prior layer. The provisioning procedure below follows this order.

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

**Cross-dependency gotchas** (not visible in the table):
- Setting `BucketOwnerEnforced` on the LOG TARGET silently breaks log
  delivery if the log-delivery ACL was the only grant — must switch to
  a bucket policy grant (see `references/bucket-policy-examples.md`).
- Enabling SSE-KMS on a bucket with cross-account readers requires the
  KMS key policy to grant them `kms:Decrypt`; the bucket policy alone
  is not enough.
- Removing the last KMS key referenced by a bucket policy is
  irreversible — encrypted objects become cryptographically unreadable.

## Expert heuristic: BPA timing window

The most dangerous period in an S3 bucket's lifecycle is the gap between
bucket creation and BPA enablement. This is when most real-world data
leaks occur — not from persistent misconfiguration, but from a race
condition during initial setup.

**The window:**

```text
T0: Bucket created (no public-access protection yet)
T1: Default encryption set
T2: Bucket policy attached
T3: BPA enabled at bucket level

Gap: T0 → T3 — bucket exists with NO public-access protection
```

**Why this matters in practice:**
- Internet scanners (GrayhatWarfare, Censys, Shodan) enumerate new S3
  buckets within **2-5 minutes** of creation. If any object is uploaded
  during T0 to T3, it is discoverable.
- A concurrent process (CI/CD pipeline, Lambda function) may upload
  objects to the bucket before BPA is enabled, creating a window even
  when the provisioning script is sequential.
- A bucket policy with `Principal: "*"` attached BEFORE BPA is enabled
  creates a public-access window even if the policy is later corrected.

**CloudFormation race condition:** when using CloudFormation, BPA is
applied as a SEPARATE resource (`AWS::S3::BucketPublicAccessBlock`) that
is created AFTER the `AWS::S3::Bucket` resource reaches
`CREATE_COMPLETE`. There is a real window where the bucket exists but
BPA is not yet enforced. To eliminate it:

```yaml
BucketPublicAccessBlock:
  Type: AWS::S3::BucketPublicAccessBlock
  Properties:
    Bucket: !Ref MyBucket
    BlockPublicAcls: true
    IgnorePublicAcls: true
    BlockPublicPolicy: true
    RestrictPublicBuckets: true

BucketPolicy:
  Type: AWS::S3::BucketPolicy
  Properties:
    Bucket: !Ref MyBucket
    PolicyDocument: ...
  DependsOn: BucketPublicAccessBlock   # enforce order
```

**Terraform:** use `aws_s3_bucket_public_access_block` as a separate
resource and add `depends_on = [aws_s3_bucket_public_access_block.my]`
on any resource that uploads objects.

**Account-level BPA is the real fix:** if account-level BPA is enabled
BEFORE any bucket is created in the account, the window is zero — all
new buckets inherit the account-level setting at creation time. Make
account-level BPA a one-time account bootstrap step, not a per-bucket
step. This eliminates the race entirely.

## Expert heuristic: SSE-KMS Bucket Keys cost model

When using SSE-KMS with cross-account or high-throughput access, Bucket
Keys are not a "nice to have" — they are the difference between a $1K/year
and a $1M/year KMS bill.

**Without Bucket Keys:**

```text
Every GET  → 1x kms:Decrypt call         ($0.03 / 10k)
Every PUT  → 1x kms:GenerateDataKey call ($0.03 / 10k)
Every HEAD → 1x kms:Decrypt call (if SSE-KMS object)

At 10M GETs/day without Bucket Keys:
  KMS cost = 10,000,000 / 10,000 * $0.03 = $3,000/day = $1,095,000/year
```

**With Bucket Keys enabled:**

```text
S3 negotiates ONE data key per bucket (time-limited, reused ~3 min).
KMS calls drop by ~99% — only 1x kms:GenerateDataKey every ~3 min.

At 10M GETs/day with Bucket Keys:
  KMS calls = ~480/day (1 every 3 min)
  KMS cost  = 480 / 10,000 * $0.03 = $0.0014/day = ~$0.52/year
```

The 99% reduction is real and documented. The nuance a baseline model
misses is the **cross-account amplification**: when a bucket is accessed
by principals in OTHER AWS accounts (cross-account replication, shared
data lake, analytics pipeline), each cross-account access without Bucket
Keys requires a KMS call in the KEY-OWNING account. This means:

1. The KMS quota (5,500-10,000 req/s region default) is shared across ALL
   cross-account readers — a single hot bucket can throttle KMS for the
   entire account.
2. The KMS cost is billed to the key owner, not the accessor. A data lake
   bucket accessed by 50 downstream accounts generates 50x the KMS calls
   with no way to charge back.

**Enable Bucket Keys on:**
- Any SSE-KMS bucket with more than 1,000 reads/day
- ANY bucket with cross-account access (no exceptions)
- Replication source and destination buckets (replication doubles KMS calls)

**Do NOT enable Bucket Keys on:**
- Buckets where you need per-request KMS audit in CloudTrail (Bucket Keys
  reduce the audit granularity to per-bucket, not per-request).
- Buckets with per-object KMS keys (different CMK per object) — Bucket
  Keys require a bucket-level default key.

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

```bash
# Account-level (do once per account)
aws s3control put-public-access-block \
  --account-id <ACCOUNT_ID> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Bucket-level (do per bucket)
aws s3api put-public-access-block \
  --bucket <BUCKET> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**Why all 4 settings**: Each blocks a different vector — `BlockPublicAcls`
prevents PUT with public ACL, `IgnorePublicAcls` ignores existing public
ACLs, `BlockPublicPolicy` prevents attaching a public bucket policy,
`RestrictPublicBuckets` restricts access to public buckets to only known
principals. All 4 together = full BPA.

**Common mistake**: Enabling only bucket-level BPA without account-level.
Account-level BPA overrides any bucket-level relaxation. Always set both.

**If it fails**: `AccessDenied` means the caller lacks
`s3:PutBucketPublicAccessBlock` (bucket-level) or
`s3:PutAccountPublicAccessBlock` (account-level) — these are separate
IAM permissions and both must be in the caller's policy. `NoSuchBucket`
on the bucket-level call means the bucket does not exist yet; create
it first (and apply bucket-level BPA in the same CloudFormation stack
or Terraform run as the create, so the public-exposure window is zero).

### Step 2 — Default encryption

Choose SSE-S3 (free, AWS-managed) or SSE-KMS (customer-controlled key).

```bash
# SSE-S3 (recommended default — zero cost, zero key management)
aws s3api put-bucket-encryption \
  --bucket <BUCKET> \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# SSE-KMS (when compliance requires customer-managed keys)
aws s3api put-bucket-encryption \
  --bucket <BUCKET> \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:<region>:<account>:key/<key-id>"}}]}'
```

**Why before upload**: Encryption applies at write time. Objects written
before this setting are NOT retroactively encrypted.

**KMS cost warning**: SSE-KMS incurs $0.03 per 10,000 requests. For
high-throughput buckets (logs, CDN), SSE-S3 is the better default. Use
SSE-KMS only when compliance or audit requirements mandate it.

**Common mistake**: Forgetting to set `BucketKeyEnabled: true` on
SSE-KMS buckets. Without Bucket Keys, every PutObject triggers a
`kms:GenerateDataKey` call ($0.03/10k + ~50-100ms latency) and you
risk hitting KMS throttle limits (5,500-10,000 req/s region default)
on high-throughput workloads.

**If it fails**: `KMSNotFoundException` or `AccessDenied` on the
SSE-KMS call almost always means ONE of: (a) the KMS key ARN region
or account ID is wrong, (b) the key is in `PendingDeletion` state,
(c) the key policy does not grant the S3 service principal
`kms:Encrypt` + `kms:GenerateDataKey` — verify with
`aws kms describe-key --key-id <ARN>` and inspect the policy with
`aws kms get-key-policy`. `MalformedJSON` usually means shell escaping
ate the inner double-quotes — wrap the JSON in single quotes.

### Step 3 — Object Ownership = BucketOwnerEnforced

Disables ALL ACLs — the bucket owner always owns every object.

```bash
aws s3api put-bucket-ownership-controls \
  --bucket <BUCKET> \
  --ownership-controls Rules=[{ObjectOwnership=BucketOwnerEnforced}]
```

**Why**: ACLs are a legacy access-control mechanism that's easy to
misconfigure. BucketOwnerEnforced eliminates ACL-based exposure vectors.
Cross-account access must flow through bucket policies (more auditable).

**Common mistake**: Flipping BucketOwnerEnforced on a bucket that has
existing cross-account writers using ACL-granted object ownership. The
switch is immediate and silent — those writers' next PutObject will
succeed but lose their per-object ownership, breaking any downstream
ACL-based read workflow. Audit `s3:GetObjectAcl` across writers first;
migrate grants to the bucket policy before flipping.

**If it fails**: `AccessDenied` means the caller lacks
`s3:PutBucketOwnershipControls` (separate from `s3:PutBucketPolicy`).
`OwnershipControlsNotFoundError` is benign on a brand-new bucket —
re-issue the call once.

### Step 4 — Versioning

Enable versioning to keep every historical version of every object.
This is the foundation for lifecycle rules on non-current versions
(Step 7), replication (Step 8), and ransomware-resistant recovery.
MFA Delete is optional but recommended for production buckets holding
irreplaceable data.

```bash
aws s3api put-bucket-versioning \
  --bucket <BUCKET> \
  --versioning-configuration Status=Enabled

# Optional: MFA delete (requires a hardware/virtual MFA device)
aws s3api put-bucket-versioning \
  --bucket <BUCKET> \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "<device-arn> <code>"
```

**Why**: Versioning protects against accidental deletion and overwrites.
Required for lifecycle rules on non-current versions and for replication.

**Common mistake**: Setting `MFADelete=Enabled` from an IAM user or
role. MFA Delete can ONLY be configured by the root account credentials
— an IAM principal issuing the call gets a silent success with no MFA
enforcement. Verify the actual MFADelete state with
`aws s3api get-bucket-versioning --bucket <BUCKET>` after the call.

**If it fails**: `AccessDenied` on the MFA Delete call almost always
means the caller is an IAM principal rather than root — re-run with
root account credentials (and rotate them after). `InvalidArgument` on
the `--mfa` flag means the device ARN or code is wrong, or the device
is not yet attached to the root account.

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

**Common mistake**: Using `Principal: "*"` with `Effect: "Allow"`.
The deny-style policies above are safe with `*` because the condition
gates the call. An ALLOW with `Principal: "*"` is genuine public access
and will be blocked by BPA — but if BPA is ever relaxed, the bucket
becomes public. Always use deny-style for enforcement policies.

**If it fails**: `AccessDenied` usually means BPA's
`BlockPublicPolicy=true` is blocking a policy containing `Principal: "*"`
with `Allow` (our deny policies should pass). `MalformedPolicy` means
JSON syntax error — validate with `python -m json.tool policy.json` or
`jq . policy.json`. `NoSuchBucket` means the bucket doesn't exist yet.

### Step 6 — Access logging

Enable S3 server access logs for the data bucket (every request is
logged with requester, source IP, action, response code, bytes) AND
CloudTrail data events for the API-level audit trail. The log target
bucket must exist in the SAME region and must grant
`logging.s3.amazonaws.com` write access via bucket policy (ACL grants
do not work with `BucketOwnerEnforced`).

```bash
aws s3api put-bucket-logging \
  --bucket <BUCKET> \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "<LOG-BUCKET>",
      "TargetPrefix": "s3/<BUCKET>/"
    }
  }'
```

For CloudTrail data events (API-level audit trail):

```bash
aws cloudtrail put-event-selectors \
  --trail-name <TRAIL> \
  --event-selectors '[{"ReadWriteType":"All","IncludeManagementEvents":true,
    "DataResources":[{"Type":"AWS::S3::Object",
    "Values":["arn:aws:s3:::<BUCKET>/"]}]}]'
```

**Common mistake**: Setting the log target to a bucket with
`BucketOwnerEnforced` enabled but granting log delivery via the legacy
`log-delivery` ACL. BucketOwnerEnforced disables ALL ACLs, so S3 log
delivery silently stops with no error. Grant `s3:PutObject` to
`logging.s3.amazonaws.com` via a bucket policy on the log target —
see `references/bucket-policy-examples.md` "Log-delivery grant".

**If it fails**: `put-bucket-logging` returns 200 even when the log
target is misconfigured — the only signal is that no logs appear after
1+ hours. Diagnostic order: (1) `aws s3api get-bucket-logging --bucket
<LOG-BUCKET>` to confirm S3 log delivery is the configured target;
(2) verify log target exists in the SAME region as the source bucket
(cross-region log delivery is unsupported for S3 server access logs);
(3) check the log target's bucket policy for the
`logging.s3.amazonaws.com` grant. CloudTrail `TrailNotFoundException`
means the trail name is wrong or the trail is in a different region.

### Step 7 — Lifecycle rules

Apply lifecycle rules to transition objects through cheaper storage
classes over time and to expire non-current versions and incomplete
multipart uploads. Rules require versioning (Step 4) for any
`NoncurrentVersion*` action — without it the rule applies as a silent
no-op. Mind the minimum-storage-duration constraints per class
(STANDARD_IA: 30d, GLACIER: 90d, DEEP_ARCHIVE: 180d) or you will pay
early-deletion fees.

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket <BUCKET> \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "transition-to-ia",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Transitions": [{ "Days": 30, "StorageClass": "STANDARD_IA" }],
        "NoncurrentVersionTransitions": [{ "NoncurrentDays": 30, "StorageClass": "STANDARD_IA" }],
        "NoncurrentVersionExpiration": { "NoncurrentDays": 90 },
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }'
```

**Storage class guidance**:
- **Intelligent-Tiering**: unknown access patterns (auto-moves between tiers)
- **STANDARD_IA**: infrequent access (>30 days, >128KB objects)
- **GLACIER_IR**: quarterly access (90+ days)
- **GLACIER**: archival, minutes-to-hours retrieval (90+ days)
- **DEEP_ARCHIVE**: long-term retention, 12h retrieval (180+ days)

**Common mistake**: Writing `NoncurrentVersion*` rules before checking
that versioning is enabled. Without versioning the rule applies
silently as a no-op — the API returns success, no objects transition,
and you only discover the cost leak weeks later via Storage Lens. Also:
transitioning objects smaller than 128 KB to STANDARD_IA / ONEZONE_IA /
GLACIER_IR costs MORE than leaving them in STANDARD due to the
minimum-size fee — use `ObjectSizeGreaterThan: 131072` in the filter.

**If it fails**: `MalformedXML` almost always means the `Filter` element
is missing — every modern rule requires `"Filter": {"Prefix": ""}` even
when matching all objects. If rules apply but objects do not transition,
verify (a) versioning is `Enabled`, (b) the object has been in its
current storage class for at least the minimum duration (30 / 60 / 90 /
180 days), and (c) for `NoncurrentVersion*` rules, the object has at
least one non-current version (a bucket with no overwrites has none).

### Step 8 — Replication (optional, if CRR/SRR required)

Prerequisites: versioning enabled (Step 4), destination bucket with its
own security baseline, IAM role with replication permissions.

```bash
aws s3api put-bucket-replication \
  --bucket <BUCKET> \
  --replication-configuration '{
    "Role": "arn:aws:iam::<ACCOUNT>:role/<REPLICATION-ROLE>",
    "Rules": [{
      "Status": "Enabled",
      "Priority": 1,
      "Filter": {},
      "Destination": { "Bucket": "arn:aws:s3:::<DEST-BUCKET>" }
    }]
  }'
```

**Common mistake**: Forgetting that replication does NOT backfill
objects written before the rule was added. Only new PutObject calls
after the rule is active are replicated. For pre-existing objects, run
an S3 Batch Operations Copy job or restart replication with
`ExistingObjectReplication: Enabled` (v2 config only).

**If it fails**: `InvalidRequest` typically means versioning is not
enabled on the SOURCE or the DESTINATION bucket (both are required).
`AccessDenied` on the role assume means the trust policy doesn't list
`s3.amazonaws.com` as principal, or the role doesn't exist in this
account. If the call succeeds but replicas do not appear, check the
replication role's permissions: it needs `s3:ReplicateObject` AND
`s3:GetObjectVersionForReplication` on source + `kms:Decrypt` on the
source KMS key + `kms:Encrypt` / `kms:GenerateDataKey` on the
destination KMS key. Use S3 replication metrics (`S3:ReplicationLatency`,
`S3:BytesPendingReplication`) to detect silent stalls.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
# BPA verification
aws s3api get-public-access-block --bucket <BUCKET>
# Expected: all 4 True

# Encryption verification
aws s3api get-bucket-encryption --bucket <BUCKET>
# Expected: SSEAlgorithm = AES256 or aws:kms

# Ownership verification
aws s3api get-bucket-ownership-controls --bucket <BUCKET>
# Expected: ObjectOwnership = BucketOwnerEnforced

# Versioning verification
aws s3api get-bucket-versioning --bucket <BUCKET>
# Expected: Status = Enabled

# Policy verification
aws s3api get-bucket-policy --bucket <BUCKET>

# Lifecycle verification
aws s3api get-bucket-lifecycle-configuration --bucket <BUCKET>
```

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

```
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
  <copy-pasteable verification commands>
```

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

```text
BUCKET: prod-order-data
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Block Public Access (account-level): all 4 settings True
  [✓] Block Public Access (bucket-level): all 4 settings True
  [✗] Default encryption: SSE-KMS selected but KMS key ARN not provided — operator must supply CMK ARN
  [✓] Object Ownership: BucketOwnerEnforced
  [✓] Versioning: Enabled (MFA Delete: Disabled)
  [✓] Bucket policy: HTTPS-enforce + SSE-enforce
  [✗] Access logging: log target bucket s3-access-logs-prod does not exist — create target bucket first
  [✗] CloudTrail data events: trail management-events not found — verify trail name and region
  [OPTIONAL] Lifecycle rules: None (not requested for this workload)
  [✗] Replication: replication IAM role not provided — create role with s3:ReplicateObject + kms:Decrypt
VERIFICATION_COMMANDS:
  aws kms list-aliases --query 'Aliases[?AliasName==`alias/prod-s3-key`]'
  aws s3api head-bucket --bucket s3-access-logs-prod
  aws cloudtrail describe-trails --query 'trailList[?Name==`management-events`]'
  aws iam get-role --role-name s3-replication-role
```

**Self-check before emit:**
- [ ] All 10 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] BPA shows two separate rows (account + bucket)?
- [ ] No `[✓]` on Lifecycle if Versioning is `[✗]`?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **S3 Express One Zone (directory buckets)**: Single-AZ, lowest latency
  for ML/AI and analytics. $0.16/GB. Use for hot data requiring <10ms
  latency. Does NOT support all lifecycle/replication features.
- **S3 Tables**: Managed Apache Iceberg tables stored in S3. Requires
  different provisioning (catalog database + table bucket).
- **S3 Object Versioning + BPA interaction**: As of 2024, BPA at account
  level overrides bucket-level BPA relaxations for ALL versions.
- **Intelligent-Tiering Archive configurations**: Can now specify Instant
  Access vs Deep Archive access tiers within Intelligent-Tiering.
- **S3 Storage Lens**: Organization-level dashboard for storage
  visibility. Enable to get metrics on noncurrent bytes, storage class
  distribution, and object age — critical for lifecycle planning.