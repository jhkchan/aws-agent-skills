---
name: s3-secure-bucket-deployer
description: 'Provisions S3 buckets with production-grade security defaults: Block Public Access (account + bucket, all 4 settings), default encryption (SSE-S3 or SSE-KMS with customer key), versioning
  with optional MFA delete, Object Ownership = BucketOwnerEnforced (ACLs disabled), access logging + CloudTrail data events, HTTPS-only bucket policy, SSE-KMS upload enforcement, lifecycle rules for cost
  optimization, and cross-region / same-region replication. Emits a READY_TO_DEPLOY checklist with every configuration item verified against the bucket''s actual state, plus copy-pasteable provisioning
  and verification commands. Use when creating a new S3 bucket, hardening an existing bucket before production, validating that a bucket meets security baseline, or generating a Terraform / CloudFormation
  skeleton with correct defaults. Triggers: create S3 bucket, provision S3, secure bucket, S3 deployment, bucket encryption, SSE-KMS, BPA, lifecycle, replication, production bucket setup.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with s3api, s3control, kms, cloudtrail, and iam access. Works with Terraform
  aws_s3_bucket resources and CloudFormation AWS::S3::Bucket templates.'
keywords:
- aws
- s3
- cloudops
- deploy
- provisioning
- security
- block-public-access
- bpa
- encryption
- sse-kms
- sse-s3
- bucket-owner-enforced
- versioning
- mfa-delete
- lifecycle
- replication
- crr
- bucket-policy
- secure-transport
- access-logging
tags:
- aws
- s3
- cloudops
- deploy
- security
- bpa
- encryption
- sse-kms
- versioning
- lifecycle
- replication
- bucket-policy
dependencies:
- aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: deploy
  skill_class: capability
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags:
  - aws
  - s3
  - cloudops
  - deploy
  - security
  - bpa
  - encryption
  - sse-kms
  - versioning
  - lifecycle
  - replication
  - bucket-policy
  dependencies:
  - aws-orchestrator
  keywords:
  - create s3 bucket
  - provision s3
  - secure bucket
  - block public access
  - sse-kms
  - bucket owner enforced
  - s3 versioning
  - mfa delete
  - s3 lifecycle
  - s3 replication
  - https-only policy
  - s3 access logging
  when_to_use: Invoke when the user wants to create a new S3 bucket with security defaults, harden an existing bucket to production baseline, validate a bucket configuration before go-live, generate provisioning
    CLI commands or IaC templates for a secure bucket, or verify that a bucket's current configuration matches the security baseline. Do NOT invoke for auditing public-access exposure (use s3-public-access-auditor),
    or for non-S3 storage (EBS, EFS, FSx).
---

# S3 Secure Bucket Deployer

An AWS CloudOps agent skill that provisions S3 buckets with correct
security defaults. The skill walks the operator through a 10-step
provisioning procedure, explains why each default matters, and emits a
READY_TO_DEPLOY checklist verifying every configuration item against the
bucket's actual state.

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

### Step 5.1 — Bucket policy (legacy full-JSON reference)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::<BUCKET>",
        "arn:aws:s3:::<BUCKET>/*"
      ],
      "Condition": {
        "Bool": { "aws:SecureTransport": "false" }
      }
    },
    {
      "Sid": "DenyUnEncryptedObjectUploads",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::<BUCKET>/*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": ["AES256", "aws:kms"]
        }
      }
    }
  ]
}
```

```bash
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://policy.json
```

### Step 6 — Access logging

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

### Step 7 — Lifecycle rules

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