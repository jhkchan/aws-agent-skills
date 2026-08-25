---
name: s3-access-troubleshooter
description: 'Diagnoses AWS S3 access failures via a systematic six-symptom diagnostic decision tree covering 403 Access Denied on GetObject (object ARN vs bucket ARN, KMS key policy, BPA, Object Ownership), 403 on PutObject (SSE enforcement, Object Lock retention, bucket full, KMS GenerateDataKey), 403 on ListBucket (bucket ARN, prefix-scoped resources), cross-account failures (identity + bucket policy intersection, KMS in both accounts), presigned URL failures (expiry, SigV4 credential scope, region), and unexpected public access (BPA hierarchy, legacy ACL, Access Point policy). Maps each symptom to a specific policy layer (account BPA, bucket BPA, bucket policy, KMS key policy, Object Ownership, ACL, VPC endpoint policy, CloudFront OAC, Access Point policy) with the BPA hierarchy: account-level > bucket -level > ACL > bucket policy > IAM identity policy. Emits ROOT_CAUSE_FOUND with the specific policy layer and evidence, or NEED_MORE_INFO / ESCALATE. Use when an S3 API call returns 403, when cross-account S3 access.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied policy JSON. Live-account diagnosis uses aws s3api get-bucket-policy, get-public-access-block, get-bucket-ownership-controls, get-object-acl, get-bucket-acl, aws kms describe-key, aws iam simulate-principal-policy, aws cloudtrail lookup-events, and aws ec2 describe-vpc-endpoints (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing an S3 403 Access Denied on GetObject, PutObject, or ListBucket, debugging cross-account S3 access failures, investigating a presigned URL that returns AccessDenied, finding the cause of unexpected public S3 access, validating BPA hierarchy interaction (account-level vs bucket-level), or determining why a KMS-encrypted object cannot be read by an otherwise-authorized principal.
  activation_triggers: AccessDenied on s3:GetObject, 403 on S3 PutObject, ListBucket AccessDenied, cross-account S3 access, presigned URL 403, S3 unexpectedly public, KMS-encrypted object AccessDenied, BPA hierarchy, bucket policy Deny, Object Lock retention, CloudFront OAC origin, S3 Access Point policy
  invocation_schema: 'Input: either (a) a symptom description (the error string, the failing S3 API, the caller''s principal ARN, the bucket/key affected) plus any policy documents already gathered, OR (b) a live-account scenario where the agent must run diagnostic CLI commands to gather context. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈ { ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE } and ROOT_CAUSE names the specific policy layer and the specific statement or missing permission that produced the deny.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: S3, AccessDenied, 403, GetObject, PutObject, ListBucket, cross-account, KMS key policy, presigned URL, Block Public Access, BPA, Object Ownership, BucketOwnerEnforced, ACL, bucket policy, VPC endpoint policy, CloudFront OAC, S3 Access Point, Object Lock, SigV4, simulate-principal-policy, CloudTrail
  tags: s3, storage, troubleshoot, access-denied, bpa, kms, cross-account, presigned-url, object-ownership, acl, bucket-policy
---

# S3 Access Troubleshooter

## Activation

Activate this skill when the user reports an S3 access failure or asks
why a principal cannot perform an S3 operation. Trigger phrases:
"AccessDenied on s3:GetObject", "403 on S3 PutObject", "ListBucket
AccessDenied", "cross-account S3 access", "presigned URL 403", "S3
unexpectedly public", "KMS-encrypted object AccessDenied", "BPA hierarchy",
"bucket policy Deny", "Object Lock retention", "CloudFront OAC origin",
"S3 Access Point policy".

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Mindset** | The BPA hierarchy and the ARN-shape trap | Read first — sets the evaluation model |
| **§ Quick reference** | Symptom → likely layer map | Identify which symptom category you have |
| **§ Pre-flight** | Mandatory context gate (principal ARN, action, resource, CloudTrail event) | Before any policy reading |
| **§ Process** | Six-symptom diagnostic decision tree (GetObject, PutObject, ListBucket, cross-account, presigned URL, unexpected public) | Walk in order for every diagnosis |
| **§ Output format** | INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION template | Format the response |
| **§ Diagnostic commands** | Exact CLI commands for each layer (s3api, kms, iam, cloudtrail) | When you need to gather evidence |
| **§ Expert edge cases** | Non-obvious gotchas (CloudFront OAC, VPC endpoint policy, S3 Access Points, Object Lock, KMS SourceAccount chain) | When the standard tree doesn't find the cause |
| **§ Anti-Patterns** | NEVER list — common misdiagnoses | Review before concluding ROOT_CAUSE_FOUND |
| **§ Remediation** | Step-by-step fix procedures per root-cause category | After root cause is identified |
| **§ References** | Deeper docs on BPA hierarchy and KMS/S3 cross-account chain | When you need the full truth tables |

## Mindset

**One-line takeaway:** an S3 access decision is the intersection of up to
seven independent policy layers evaluated in a fixed precedence — **account
-level Block Public Access (BPA), bucket-level BPA, Object Ownership, ACL,
bucket policy, IAM identity policy, KMS key policy** (when SSE-KMS is
involved) — and 403 Access Denied is a symptom, not a cause. The cause is
the specific layer (or pair of layers for cross-account) that produced the
deny. Treat the symptom as the entry point to a deterministic walk.

The three facts in full (ARN shape determines which actions can match, account-level BPA overrides everything silently, KMS as a separate decision gate): [references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference — symptom to layer map

| Symptom | Likely layer(s) | First probe |
|---|---|---|
| `AccessDenied` on `s3:GetObject` | (1) Identity policy missing `s3:GetObject` on object ARN, (2) bucket policy `Deny`, (3) KMS key policy, (4) account/bucket BPA, (5) Object Ownership (`BucketOwnerEnforced` for cross-account write) | CloudTrail `errorMessage`; check identity policy for `GetObject` on `bucket/*` |
| `AccessDenied` on `s3:PutObject` | (1) Identity policy missing `s3:PutObject` on object ARN, (2) bucket policy `Deny` enforcing SSE, (3) missing `kms:GenerateDataKey`, (4) bucket full, (5) Object Lock retention | Check bucket policy Deny statements; check `kms:GenerateDataKey` |
| `AccessDenied` on `s3:ListBucket` | Identity policy missing `s3:ListBucket` on BUCKET ARN (not object ARN); conditional resources for prefix-scoped listing | Check identity policy uses `arn:aws:s3:::bucket` (no `/*`) |
| Cross-account S3 failure | Identity policy AND bucket policy must BOTH allow (intersection); KMS key policy must also grant both accounts | Check both sides explicitly |
| Presigned URL `403` | (1) Expired, (2) SigV4 credential scope / region mismatch, (3) presigned for a different identity than the caller, (4) bucket policy denies the calling principal, (5) bucket region not the presigned region | Decode the URL; verify `X-Amz-Date` vs `X-Amz-Expires`; verify bucket region |
| Unexpected public access | (1) Account-level BPA not enabled, (2) legacy ACL `AllUsers`/`AuthenticatedUsers`, (3) public bucket policy, (4) Access Point policy with `Principal: "*"`, (5) MRAP policy propagating public access | Check BPA at both account and bucket levels; enumerate ACLs and Access Points |

## Pre-flight: mandatory context gate (run before any policy reading)

Before any policy reading, capture these four values. Without them, the
decision tree cannot terminate.

| Field | Why required | Source |
|---|---|---|
| **Principal ARN** | Identity-based policy and KMS key policy evaluate against this; reveals assumed-role vs federated vs anonymous | `aws sts get-caller-identity`, or CloudTrail `userIdentity.arn` |
| **Action (exact)** | Policy `Action` patterns must match the service-prefixed name. S3 has both bucket-level and object-level actions — confusing them is the #1 misdiagnosis. | The error message includes the action verbatim |
| **Resource ARN (bucket + key)** | Bucket ARN (`arn:aws:s3:::bucket`) vs object ARN (`arn:aws:s3:::bucket/key`) determine which actions can match. KMS key ARN is separate. | The error message OR the presigned URL |
| **CloudTrail event** | The only authoritative source for "implicit vs explicit deny" and the only source for the KMS layer's denial signal. `errorMessage` sometimes disambiguates. | `aws cloudtrail lookup-events` filtered by EventName |

**ARN shape gate (apply before any policy walk):**

- Bucket-level actions (`s3:ListBucket`, `s3:ListBucketVersions`,
  `s3:DeleteBucket`, `s3:GetBucketLocation`, `s3:GetBucketTagging`,
  `s3:PutBucketTagging`, `s3:PutBucketPolicy`, `s3:PutBucketAcl`)
  require `arn:aws:s3:::bucket-name` (no `/*`).
- Object-level actions (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`,
  `s3:CopyObject`, `s3:GetObjectVersion`, `s3:AbortMultipartUpload`)
  require `arn:aws:s3:::bucket-name/*` or
  `arn:aws:s3:::bucket-name/specific/key`.
- S3 Access Point ARNs (`arn:aws:s3:<region>:<acct>:accesspoint/<name>`)
  or `arn:aws:s3:::accesspoint/<name>` are an alternative Resource format
  for both bucket-level and object-level actions addressed through the
  Access Point.

If the caller cannot supply the exact action or resource ARN, emit
`NEED_MORE_INFO` listing the missing field. Do not guess.

## Process — Diagnostic decision tree (apply in order, do NOT skip steps)

### Step 0: Identify the symptom category

Map the symptom to one of six categories. Each category has a different
first probe — choosing the wrong category wastes diagnostic time.

| Category | Signature | First probe |
|---|---|---|
| **A. GetObject AccessDenied** | `s3:GetObject` returns 403 on a specific object | Step 1 |
| **B. PutObject AccessDenied** | `s3:PutObject` returns 403 when uploading | Step 2 |
| **C. ListBucket AccessDenied** | `s3:ListBucket` returns 403 — listing fails | Step 3 |
| **D. Cross-account failure** | Caller principal ARN account ≠ bucket account | Step 4 |
| **E. Presigned URL failure** | A URL that "should work" returns 403 to anyone | Step 5 |
| **F. Unexpected public access** | A bucket "should be private" but is publicly readable | Step 6 |

If the symptom matches more than one category, pick the most specific
(cross-account > specific action > generic). Most cross-account failures
are ALSO GetObject or PutObject failures; the cross-account path surfaces
the intersection rule.

### Step 1: GetObject AccessDenied diagnostic path

Walk these in order; the first match is the root cause.
Per-branch probe and evidence detail for Step 1 items 1-7 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).

1. **Identity policy missing `s3:GetObject` on the OBJECT ARN.**
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, missing
     `s3:GetObject` on object ARN.

2. **Bucket policy explicit `Deny` on `s3:GetObject`.**
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy Deny, statement
     Sid + matched condition keys.

3. **KMS key policy does not grant `kms:Decrypt` to the caller.**
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy, missing
     `kms:Decrypt` grant.

4. **Block Public Access blocking an otherwise-valid public policy.**
   - **Output:** ROOT_CAUSE_FOUND, layer = BPA (account or bucket),
     specific settings blocking.

5. **Object Ownership = `BucketOwnerEnforced` blocking cross-account
   writers.**
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, ACLs disabled.

6. **VPC endpoint policy restricting S3 access.**
   - **Output:** ROOT_CAUSE_FOUND, layer = VPC endpoint policy.

7. **CloudFront OAC misconfigured (origin is S3).**
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy CloudFront
     principal (OAC vs OAI mismatch).

### Step 2: PutObject AccessDenied diagnostic path

Per-branch probe and evidence detail for Step 2 items 1-6 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).
1. **Identity policy missing `s3:PutObject` on the OBJECT ARN.**

2. **Bucket policy `Deny` enforcing SSE.**
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy SSE enforcement
     Deny.

3. **Missing `kms:GenerateDataKey`.**
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS, missing
     `kms:GenerateDataKey`.

4. **Bucket full (capacity exhausted).**

5. **Object Lock retention / legal hold.**
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Lock retention /
     legal hold, mode and retain-until date.

6. **Object Ownership = `BucketOwnerEnforced` (cross-account write
   without bucket-owner-full-control ACL).**
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, missing
     `x-amz-acl: bucket-owner-full-control`.

### Step 3: ListBucket AccessDenied diagnostic path

Per-branch probe and evidence detail for Step 3 items 1-4 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).
1. **Identity policy missing `s3:ListBucket` on the BUCKET ARN.**
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, ARN shape
     wrong (object ARN used instead of bucket ARN).

2. **Prefix-scoped listing denied (conditional resources).**

3. **Bucket policy Deny on `s3:ListBucket`.**

4. **KMS is NOT a factor for ListBucket.** ListBucket does not read

### Step 4: Cross-account S3 access diagnostic path

For cross-account calls (caller account ≠ bucket account), BOTH the
caller's identity-based policy AND the bucket's resource-based policy
must Allow the action. This is the intersection rule.

```
Same-account:   identity-based  ∪  bucket policy  (either Allows = grant)
Cross-account:  identity-based  ∩  bucket policy  (both must Allow)
```

Walk these in order:
Per-branch probe and evidence detail for Step 4 items 1-6 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).

1. **Verify identity policy (caller account) grants the action on the

2. **Verify bucket policy (bucket account) grants the action to the
   caller principal ARN.**
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy missing
     cross-account principal.

3. **KMS key policy in BOTH accounts (for SSE-KMS).**
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy missing
     cross-account grant.

4. **Account-level BPA in the bucket account.**
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA, ACL-based
     cross-account workflow broken.

5. **KMS `aws:SourceAccount` chain.**
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy
     `aws:SourceAccount` chain, source account is bucket's account not
     caller's.

6. **VPC endpoint policy (cross-VPC or cross-account via TGW).**

### Step 5: Presigned URL failure diagnostic path

A presigned URL embeds the signing credential, signature, expiry, and
region. Any mismatch produces 403.
Per-branch probe and evidence detail for Step 5 items 1-6 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).

1. **URL expired.**
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL expired.

2. **SigV4 credential scope / region mismatch.**
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL region
     mismatch.

3. **Presigned for a different identity than intended.**
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL signer
     permission revoked.

4. **Bucket policy denies the calling principal.**

5. **BPA blocking public presigned URL.**

6. **Signature version mismatch.**
   - **Output:** ROOT_CAUSE_FOUND, layer = signature version mismatch.

### Step 6: Unexpected public access diagnostic path

Use when a bucket "should be private" but is publicly readable.
Per-branch probe and evidence detail for Step 6 items 1-7 (moved verbatim): [references/diagnostic-commands.md](references/diagnostic-commands.md).

1. **Account-level BPA not enabled.**
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA disabled.
     Recommend enable at account level (covers all current + future
     buckets).

2. **Bucket-level BPA not enabled (and account-level is also off).**

3. **Legacy ACL `AllUsers` / `AuthenticatedUsers`.**

4. **Public bucket policy (`Principal: "*"`).**
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy wildcard Allow.

5. **Access Point policy with `Principal: "*"`.**
   - **Output:** ROOT_CAUSE_FOUND, layer = Access Point policy wildcard
     Allow.

6. **MRAP (Multi-Region Access Point) propagating public access.**

7. **S3 website hosting amplifying exposure.**

### Step 7: Map to root-cause catalog

These are the patterns that account for ~90% of S3 AccessDenied incidents:

| # | Root cause | Symptom | Fix pattern |
|---|---|---|---|
| 1 | Wrong ARN shape (bucket vs object) | GetObject/ListBucket AccessDenied; policy "looks right" | Add the second ARN shape (bucket ARN + object ARN wildcard) |
| 2 | KMS key policy missing cross-account caller | Cross-account GetObject AccessDenied on SSE-KMS object | Add `kms:Decrypt` grant to caller's role ARN in key policy |
| 3 | Bucket policy missing cross-account principal | Cross-account GetObject/PutObject AccessDenied | Add caller's role ARN to bucket policy `Principal.AWS` |
| 4 | BPA blocking public access (account or bucket level) | Public access unexpectedly denied (or unexpectedly blocked when intentional) | Enable/disable BPA at appropriate scope |
| 5 | Bucket policy Deny enforcing SSE | PutObject AccessDenied | Add SSE header to PutObject request |
| 6 | Object Lock retention / legal hold | PutObject/DeleteObject AccessDenied on existing key | Wait for retention to expire; release legal hold |
| 7 | Presigned URL expired or region-mismatched | Presigned URL 403 | Re-sign with correct region and shorter expiry |
| 8 | CloudFront OAC vs OAI mismatch | 403 from CloudFront origin | Update bucket policy principal to OAC format |
| 9 | VPC endpoint policy restricting access | AccessDenied from VPC-attached resource only | Update VPC endpoint policy or route around endpoint |
| 10 | Object Ownership = `BucketOwnerEnforced` cross-account write | PutObject AccessDenied from cross-account writer | Add `x-amz-acl: bucket-owner-full-control` to PutObject |

When the walk reaches a fix that matches the catalog, name the catalog
number in the output.

### Step 8: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a single policy layer and
  statement (or a specific missing permission) as the cause, and the fix
  is a known pattern from the catalog. Output REMEDIATION with the exact
  policy edit.
- **NEED_MORE_INFO.** The walk reached a layer the operator cannot
  supply (e.g., "the KMS key is in another account and I have no read
  access"). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a layer that requires action outside
  the operator's scope: account-level BPA owned by a central security
  team, a KMS key owned by another team, a VPC endpoint policy owned by
  the network team, a CloudFront distribution owned by the edge team.
  Output the escalation target and the specific request to make.

## Output format

```text
INCIDENT: <principal ARN> → <action> on <resource ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <layer name> — <statement Sid or missing permission> —
<implicit or explicit deny>
EVIDENCE:
  - <layer 1>: <Allowed | Denied | Not evaluated> — <evidence line>
  - <layer 2>: <Allowed | Denied | Not evaluated> — <evidence line>
  - ...
ROOT_CAUSE_CATALOG: #<N> (if matches catalog, else "novel")
REMEDIATION:
  1. <specific policy edit with statement Sid>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — cross-account KMS-encrypted S3 GetObject

```text
INCIDENT: arn:aws:sts::111111111111:assumed-role/AppLambda/... →
s3:GetObject on arn:aws:s3:::prod-data/report.csv
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: KMS key policy (resource-based on
arn:aws:kms:us-east-1:222222222222:key/abc123) — implicit deny — caller
role not granted kms:Decrypt. S3 layer allows (bucket policy includes
caller; identity policy has s3:GetObject), but the KMS Decrypt call made
by S3 on the caller's behalf is denied at the key policy.
EVIDENCE:
  - Identity-based policy (caller, account 111111111111): Allowed —
    s3:GetObject on arn:aws:s3:::prod-data/* AND kms:Decrypt on the key
    ARN (verified)
  - S3 bucket policy (account 222222222222): Allowed — Principal.AWS
    includes arn:aws:iam::111111111111:role/AppLambda, Action
    s3:GetObject, Resource arn:aws:s3:::prod-data/*
  - Account BPA (account 222222222222): not blocking (caller is
    authenticated IAM, not public)
  - Object Ownership: BucketOwnerEnforced (does not affect read)
  - KMS key policy (account 222222222222): DENIED — Principal.AWS lists
    only account-222222222222 roles; no cross-account grant for
    kms:Decrypt to arn:aws:iam::111111111111:role/AppLambda
ROOT_CAUSE_CATALOG: #2 (KMS key policy missing cross-account caller)
REMEDIATION:
  1. Add to the KMS key policy in account 222222222222:
     {
       "Sid": "AllowCrossAccountDecrypt",
       "Effect": "Allow",
       "Principal": { "AWS": "arn:aws:iam::111111111111:role/AppLambda" },
       "Action": "kms:Decrypt",
       "Resource": "*"
     }
  2. The caller's identity policy already has kms:Decrypt on the key ARN
     (verified), so the cross-account intersection at KMS is satisfied
     once the key policy is updated.
  3. Validate with:
     aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/AppLambda \
       --action-names kms:Decrypt \
       --resource-arns arn:aws:kms:us-east-1:222222222222:key/abc123
  4. Monitor CloudTrail for kms:Decrypt events in account 222222222222.
```

## Diagnostic command reference

Run these in order. Each command's output narrows the decision tree.

The 13 ordered diagnostic commands (caller identity, CloudTrail, bucket policy, BPA both scopes, ownership, ACLs, encryption, key policy, simulator, Object Lock, Access Points, VPC endpoint, CloudFront OAC): [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Expert edge cases

These patterns represent genuine, non-obvious S3 access failure causes
that a senior S3 engineer would catch but a generalist would miss.
All nine edge cases (`aws:SourceAccount` chain, VPC endpoint policy shadow, CloudFront OAC replaces OAI, AP bypasses bucket policy, Object Lock COMPLIANCE irreversibility, BucketOwnerEnforced cross-account write, presigned URL with session policy, directory buckets, MRAP policy propagation): [references/advanced-patterns.md](references/advanced-patterns.md).


## Anti-Patterns — NEVER

- NEVER assume `s3:GetObject` and `s3:ListBucket` use the same ARN shape.
  `GetObject` requires the object ARN (`bucket/*`); `ListBucket` requires
  the bucket ARN (`bucket`). This is the single most common S3
  misdiagnosis.

- NEVER assume S3 access is enough for SSE-KMS objects. The KMS key
  policy is a SEPARATE gate that can independently deny. Cross-account
  SSE-KMS GetObject requires allows at THREE layers: caller identity,
  bucket policy, key policy.

- NEVER assume AccessDenied means the identity policy is wrong. The deny
  could be in the bucket policy, BPA, KMS key policy, VPC endpoint
  policy, Object Lock retention, or Object Ownership. Walk every layer
  before concluding.

- NEVER recommend `Action: "s3:*"` on `Resource: "*"` to fix S3
  AccessDenied. This is the most damaging operator reflex. The correct
  fix is to identify the specific missing action on the specific ARN
  shape.

- NEVER assume a `private` ACL means the bucket is safe when BPA is off.
  The ACL and the bucket policy are independent — a public policy
  overrides a private ACL because AWS unions the two.

- NEVER recommend disabling BPA as a fix for AccessDenied. BPA is a
  security control. The fix is to identify the actual layer causing the
  deny (often KMS or bucket policy), not to remove the public-access
  guardrail.

- NEVER conflate same-account and cross-account evaluation. The
  intersection vs union rule is non-negotiable. Same-account: EITHER
  identity OR bucket policy. Cross-account: BOTH.

- NEVER trust a presigned URL's region by assumption. Decode the
  `X-Amz-Credential` scope and verify the region matches the bucket's
  region via `aws s3api get-bucket-location`.

- NEVER assume a bucket policy `Principal: "*"` works without
  restrictive conditions. Without BPA, this is a public read path. With
  BPA, the policy is restricted to in-account principals only (silently).

- NEVER overlook the VPC endpoint policy layer. It is independent of IAM
  and S3 policies. Bypass the endpoint to test.

- NEVER forget that S3 Access Points have their own policies. A
  restrictive bucket policy does NOT prevent access through a permissive
  AP. Always enumerate APs.

- NEVER assume Object Lock retention can be bypassed. `COMPLIANCE` mode
  cannot be bypassed by ANY principal — even root — until expiry.
  `GOVERNANCE` mode can be bypassed with
  `s3:BypassGovernanceRetention` permission.

- NEVER assume CloudFront OAI bucket policies work for OAC. OAC uses a
  different principal format. Migrate the bucket policy when migrating
  from OAI to OAC.

- NEVER overlook Object Ownership `BucketOwnerEnforced` for cross-account
  writes. ACLs are disabled at the API layer — cross-account writers
  MUST use `x-amz-acl: bucket-owner-full-control` AND the bucket policy
  must allow the cross-account principal.

- NEVER report ROOT_CAUSE_FOUND when the only evidence is the error
  string. The error string does not distinguish implicit from explicit
  deny, and does not name the layer. Require CloudTrail `errorMessage`
  or simulator output before declaring the root cause.

- NEVER recommend `AuthenticatedUsers` ACL grant as a workaround.
  `AuthenticatedUsers` means "any AWS account holder" — anyone can
  create a free-tier account. It is effectively public.

## Remediation guidance

Per-root-cause remediation procedures (ARN-shape errors, KMS key policy cross-account, cross-account principal, BPA blocking intended public access, SSE-enforcement Deny, Object Lock, presigned URLs, CloudFront OAC migration): [references/error-handling.md](references/error-handling.md).

## Recent AWS features (2024-2026)

Recent AWS features detail (S3 directory buckets, S3 Access Grants, S3 Tables, versioning default, OAC mandate, account-level BPA default, MRAP cross-region access logging): [references/advanced-patterns.md](references/advanced-patterns.md).

## References

- `references/bpa-hierarchy-and-truth-tables.md` — full BPA scope
  interaction truth table (account-level vs bucket-level, per-setting
  effective values), worked examples for each combination.
- `references/kms-and-s3-cross-account-chain.md` — exhaustive walkthrough
  of the S3 → KMS service-to-service chain, `aws:SourceAccount` /
  `aws:SourceArn` semantics, and cross-account write scenarios with
  `BucketOwnerEnforced`.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — the three Mindset facts in full, the nine expert edge cases, recent AWS features
- [Diagnostic commands](references/diagnostic-commands.md) — full per-branch detail for Steps 1-6 and the 13 ordered diagnostic commands
- [Error handling](references/error-handling.md) — per-root-cause remediation procedures
- [BPA hierarchy and truth tables](references/bpa-hierarchy-and-truth-tables.md) — account vs bucket BPA interaction
- [KMS and S3 cross-account chain](references/kms-and-s3-cross-account-chain.md) — the S3 → KMS chain and `aws:SourceAccount` semantics

## Domain

AWS CloudOps / S3 Storage Access Control Diagnostics.

## AWS documentation

- **Amazon S3 User Guide** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- **S3 Security Best Practices** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html
- **Block Public Access** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
- **S3 Object Ownership** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html
- **S3 Access Points** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-points.html
- **S3 Object Lock** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html
- **CloudFront OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **IAM policy simulator** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html
- **AWS KMS + S3** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html
