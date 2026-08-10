---
name: s3-access-troubleshooter
description: 'Diagnoses AWS S3 access failures via a systematic six-symptom diagnostic decision tree covering 403 Access Denied on GetObject (object ARN vs bucket ARN, KMS key policy, BPA, Object Ownership),
  403 on PutObject (SSE enforcement, Object Lock retention, bucket full, KMS GenerateDataKey), 403 on ListBucket (bucket ARN, prefix-scoped resources), cross-account failures (identity + bucket policy intersection,
  KMS in both accounts), presigned URL failures (expiry, SigV4 credential scope, region), and unexpected public access (BPA hierarchy, legacy ACL, Access Point policy). Maps each symptom to a specific policy
  layer (account BPA, bucket BPA, bucket policy, KMS key policy, Object Ownership, ACL, VPC endpoint policy, CloudFront OAC, Access Point policy) with the BPA hierarchy: account-level > bucket -level >
  ACL > bucket policy > IAM identity policy. Emits ROOT_CAUSE_FOUND with the specific policy layer and evidence, or NEED_MORE_INFO / ESCALATE. Use when an S3 API call returns 403, when cross-account S3
  access.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied policy JSON. Live-account diagnosis uses aws s3api get-bucket-policy,
  get-public-access-block, get-bucket-ownership-controls, get-object-acl, get-bucket-acl, aws kms describe-key, aws iam simulate-principal-policy, aws cloudtrail lookup-events, and aws ec2 describe-vpc-endpoints
  (AWS CLI v2, SSO or key-based credentials).
keywords:
- S3
- AccessDenied
- 403
- GetObject
- PutObject
- ListBucket
- cross-account
- KMS key policy
- presigned URL
- Block Public Access
- BPA
- Object Ownership
- BucketOwnerEnforced
- ACL
- bucket policy
- VPC endpoint policy
- CloudFront OAC
- S3 Access Point
- Object Lock
- SigV4
- simulate-principal-policy
- CloudTrail
tags:
- s3
- storage
- troubleshoot
- access-denied
- bpa
- kms
- cross-account
- presigned-url
- object-ownership
- acl
- bucket-policy
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing an S3 403 Access Denied on GetObject, PutObject, or ListBucket, debugging cross-account S3 access failures, investigating a presigned URL that returns AccessDenied, finding the
    cause of unexpected public S3 access, validating BPA hierarchy interaction (account-level vs bucket-level), or determining why a KMS-encrypted object cannot be read by an otherwise-authorized principal.
  activation_triggers:
  - AccessDenied on s3:GetObject
  - 403 on S3 PutObject
  - ListBucket AccessDenied
  - cross-account S3 access
  - presigned URL 403
  - S3 unexpectedly public
  - KMS-encrypted object AccessDenied
  - BPA hierarchy
  - bucket policy Deny
  - Object Lock retention
  - CloudFront OAC origin
  - S3 Access Point policy
  invocation_schema: 'Input: either (a) a symptom description (the error string, the failing S3 API, the caller''s principal ARN, the bucket/key affected) plus any policy documents already gathered, OR
    (b) a live-account scenario where the agent must run diagnostic CLI commands to gather context. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈
    { ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE } and ROOT_CAUSE names the specific policy layer and the specific statement or missing permission that produced the deny.'
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

Three facts make S3 troubleshooting different from generic "check your
policy":

- **ARN shape determines which actions can match.** The single most
  common S3 misdiagnosis is "the policy has `s3:GetObject` on the bucket
  ARN." For S3, bucket-level actions (`s3:ListBucket`,
  `s3:DeleteBucket`, `s3:GetBucketLocation`) require
  `arn:aws:s3:::bucket-name` (no `/*`). Object-level actions
  (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`) require
  `arn:aws:s3:::bucket-name/*` (with `/*`). Confusing the two produces
  AccessDenied on a policy that "looks right."

- **Account-level BPA overrides everything below it.** The BPA hierarchy
  in AWS's evaluation is `account-level BPA > bucket-level BPA > ACL >
  bucket policy > IAM identity policy`. Account-level BPA blocks public
  access even if the bucket policy explicitly allows `Principal: "*"` —
  and SILENTLY. There is no error; the request is denied as if no policy
  allowed it. Operators chasing a bucket-policy bug while account-level
  BPA is the cause waste hours.

- **KMS is a separate decision gate, not part of the bucket policy.** A
  bucket encrypted with a customer-managed KMS key has TWO independent
  access decisions: the S3 layer (bucket policy + identity policy) AND
  the KMS layer (key policy + identity policy's `kms:Decrypt` grant).
  Each gate can independently deny. The same principal may have S3
  access but no KMS access — the symptom is AccessDenied on GetObject,
  indistinguishable from a pure S3 deny without inspecting CloudTrail.

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

1. **Identity policy missing `s3:GetObject` on the OBJECT ARN.**
   - Check via `aws iam simulate-principal-policy --action-names
     s3:GetObject --resource-arns arn:aws:s3:::bucket/key`.
   - Most common cause. Verify the policy uses
     `arn:aws:s3:::bucket-name/*` (object ARN), not
     `arn:aws:s3:::bucket-name` (bucket ARN — wrong for GetObject).
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, missing
     `s3:GetObject` on object ARN.

2. **Bucket policy explicit `Deny` on `s3:GetObject`.**
   - Read bucket policy: `aws s3api get-bucket-policy --bucket <name>`.
   - Look for `Effect: Deny` with `Action: s3:GetObject` or
     `NotAction` including GetObject. Check the `Condition` — `aws:SecureTransport:
     false` (TLS enforcement), `aws:SourceIp` (IP allowlist),
     `aws:SourceVpce` (VPCe enforcement).
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy Deny, statement
     Sid + matched condition keys.

3. **KMS key policy does not grant `kms:Decrypt` to the caller.**
   - Determine the bucket's encryption:
     `aws s3api get-bucket-encryption --bucket <name>`. If SSE-KMS with a
     customer-managed key, KMS is a separate gate.
   - Read the key policy:
     `aws kms describe-key --key-id <key-id>` and
     `aws kms get-key-policy --key-id <key-id> --policy-name default`.
   - For same-account: the key policy MUST grant `kms:Decrypt` to the
     caller. For cross-account: see Step 4.
   - ALSO verify the identity policy has `kms:Decrypt` on the key ARN.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy, missing
     `kms:Decrypt` grant.

4. **Block Public Access blocking an otherwise-valid public policy.**
   - If the bucket policy or ACL grants public access AND BPA is enabled
     at the account or bucket level, S3 silently denies the public
     request. The error is `AccessDenied` with no hint about BPA.
   - Check both levels:
     `aws s3control get-public-access-block --account-id <acct>` and
     `aws s3api get-public-access-block --bucket <name>`.
   - All four settings must be False for public access to work:
     `BlockPublicAcls`, `IgnorePublicAcls`, `BlockPublicPolicy`,
     `RestrictPublicBuckets`. Account-level BPA overrides bucket-level.
   - **Output:** ROOT_CAUSE_FOUND, layer = BPA (account or bucket),
     specific settings blocking.

5. **Object Ownership = `BucketOwnerEnforced` blocking cross-account
   writers.**
   - If the caller is in a different account than the bucket owner AND
     the bucket's Object Ownership is `BucketOwnerEnforced`, ACLs are
     disabled. Cross-account writers cannot use ACL-based ownership
     transfer — they MUST include `x-amz-acl: bucket-owner-full-control`
     in the upload AND the bucket policy must Allow it.
   - `aws s3api get-bucket-ownership-controls --bucket <name>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, ACLs disabled.

6. **VPC endpoint policy restricting S3 access.**
   - If the caller is in a VPC with a VPC endpoint for S3 (Gateway or
     Interface), the endpoint's policy is an independent gate that can
     deny requests even when all IAM/S3 policies allow.
   - The CloudTrail event shows AccessDenied with no hint about the VPC
     endpoint. The diagnostic is to bypass the endpoint (route over
     internet or a different endpoint) and see if the call succeeds.
   - **Output:** ROOT_CAUSE_FOUND, layer = VPC endpoint policy.

7. **CloudFront OAC misconfigured (origin is S3).**
   - If the caller is reaching S3 through CloudFront, the S3 bucket
     policy MUST grant `s3:GetObject` to the CloudFront OAC principal
     (`service:cloudfront.amazonaws.com` with the OAC ID in
     `aws:SourceArn` condition). The legacy OAI uses a different
     principal format.
   - Read the bucket policy and verify the CloudFront principal.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy CloudFront
     principal (OAC vs OAI mismatch).

### Step 2: PutObject AccessDenied diagnostic path

1. **Identity policy missing `s3:PutObject` on the OBJECT ARN.**
   - Same shape as GetObject — verify object ARN (`bucket/*`).

2. **Bucket policy `Deny` enforcing SSE.**
   - Common pattern: bucket policy denies `s3:PutObject` when
     `s3:x-amz-server-side-encryption` is not `aws:kms` or `AES256`.
     Operators uploading without the SSE header get AccessDenied.
   - Read the bucket policy's Deny statements for
     `s3:x-amz-server-side-encryption` or
     `s3:x-amz-server-side-encryption-aws-kms-key-id`.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy SSE enforcement
     Deny.

3. **Missing `kms:GenerateDataKey`.**
   - SSE-KMS PutObject requires `kms:GenerateDataKey` on the key ARN in
     addition to `s3:PutObject` on the object. The KMS call is made by
     S3 on the caller's behalf.
   - Cross-account: BOTH the caller's identity policy AND the KMS key
     policy must allow. See Step 4.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS, missing
     `kms:GenerateDataKey`.

4. **Bucket full (capacity exhausted).**
   - Rare in standard buckets (no quota), but possible for S3 Directory
     Buckets (`/express-*`). The error message usually says "Bucket is
     full" but can appear as AccessDenied on misconfigured clients.
   - `aws s3 ls s3://<bucket> --recursive --human-readable --summarize`
     for size check.

5. **Object Lock retention / legal hold.**
   - An object under `ObjectLockRetention` (`COMPLIANCE` or `GOVERNANCE`)
     or `LegalHold` cannot be overwritten or deleted. `COMPLIANCE` mode
     cannot be bypassed even by root.
   - `aws s3api get-object-retention --bucket <b> --key <k>` and
     `aws s3api get-object-legal-hold --bucket <b> --key <k>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Lock retention /
     legal hold, mode and retain-until date.

6. **Object Ownership = `BucketOwnerEnforced` (cross-account write
   without bucket-owner-full-control ACL).**
   - Cross-account writers MUST include
     `x-amz-acl: bucket-owner-full-control` in the PutObject request.
     Without it, the upload may succeed but the object is owned by the
     writer's account — and `BucketOwnerEnforced` may reject the upload
     entirely if the bucket policy requires it.
   - **Output:** ROOT_CAUSE_FOUND, layer = Object Ownership /
     `BucketOwnerEnforced`, missing
     `x-amz-acl: bucket-owner-full-control`.

### Step 3: ListBucket AccessDenied diagnostic path

1. **Identity policy missing `s3:ListBucket` on the BUCKET ARN.**
   - The #1 cause. `s3:ListBucket` requires the bucket ARN
     (`arn:aws:s3:::bucket-name`), NOT the object ARN. Operators often
     write `s3:ListBucket` on `bucket/*` — that matches no resource.
   - **Output:** ROOT_CAUSE_FOUND, layer = identity-based, ARN shape
     wrong (object ARN used instead of bucket ARN).

2. **Prefix-scoped listing denied (conditional resources).**
   - For prefix-scoped ListBucket permission, the identity policy uses
     two Resource entries:
     ```json
     "Resource": [
       "arn:aws:s3:::bucket-name",
       "arn:aws:s3:::bucket-name/prefix/*"
     ]
     ```
   - The first grants ListBucket on the bucket ARN; the second grants
     GetObject on objects under `prefix/`. Listing outside the prefix
     fails with AccessDenied.
   - Verify both entries exist.

3. **Bucket policy Deny on `s3:ListBucket`.**
   - Same as GetObject Deny — read the policy, look for `Effect: Deny`
     with `Action: s3:ListBucket` or `NotAction`.

4. **KMS is NOT a factor for ListBucket.** ListBucket does not read
   object content — no KMS decrypt is invoked. KMS issues only affect
   object-level operations.

### Step 4: Cross-account S3 access diagnostic path

For cross-account calls (caller account ≠ bucket account), BOTH the
caller's identity-based policy AND the bucket's resource-based policy
must Allow the action. This is the intersection rule.

```
Same-account:   identity-based  ∪  bucket policy  (either Allows = grant)
Cross-account:  identity-based  ∩  bucket policy  (both must Allow)
```

Walk these in order:

1. **Verify identity policy (caller account) grants the action on the
   ARN.** Same ARN-shape rules as Steps 1-3 apply.

2. **Verify bucket policy (bucket account) grants the action to the
   caller principal ARN.**
   - Read: `aws s3api get-bucket-policy --bucket <name> --profile
     <bucket-acct>`.
   - The policy's `Principal.AWS` MUST include the caller's role ARN
     (`arn:aws:iam::<caller-acct>:role/<role>`). A `Principal: "*"` is
     not enough if BPA is enabled at either scope.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy missing
     cross-account principal.

3. **KMS key policy in BOTH accounts (for SSE-KMS).**
   - The KMS key is in the bucket's account. The key policy MUST grant
     `kms:Decrypt` (read) and `kms:GenerateDataKey` (write) to the
     caller's role ARN.
   - The caller's identity policy MUST ALSO grant `kms:Decrypt` /
     `kms:GenerateDataKey` on the key ARN. The intersection rule applies
     at KMS too.
   - `aws kms get-key-policy --key-id <key-id> --policy-name default
     --profile <bucket-acct>` — check for the caller's role ARN.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy missing
     cross-account grant.

4. **Account-level BPA in the bucket account.**
   - Account-level BPA blocks public access regardless of bucket policy.
     For cross-account non-public access, BPA's `RestrictPublicBuckets`
     can still block a `Principal: "*"` policy if the caller is not
     authenticated — but cross-account IAM role access is not "public"
     and is not blocked by BPA directly.
   - However, BPA blocks public ACLs that were the original cross-account
     mechanism pre-2022. If the workflow uses ACL-based ownership
     transfer and BPA is on, the ACL is silently ignored.
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA, ACL-based
     cross-account workflow broken.

5. **KMS `aws:SourceAccount` chain.**
   - When S3 reads an object on behalf of a caller, the KMS call is made
     BY S3. A KMS key policy that requires
     `aws:SourceAccount: "<bucket-acct>"` evaluates the S3 service call's
     source account — which is the BUCKET's account, not the caller's.
     Operators writing this condition expecting it to mean "the caller's
     account" produce silent denies.
   - **Output:** ROOT_CAUSE_FOUND, layer = KMS key policy
     `aws:SourceAccount` chain, source account is bucket's account not
     caller's.

6. **VPC endpoint policy (cross-VPC or cross-account via TGW).**
   - If the caller is in a different VPC reaching the bucket through a
     VPC endpoint, the endpoint policy may restrict the principals or
     buckets allowed. Cross-account traffic through a shared VPC endpoint
     inherits the endpoint policy.

### Step 5: Presigned URL failure diagnostic path

A presigned URL embeds the signing credential, signature, expiry, and
region. Any mismatch produces 403.

1. **URL expired.**
   - Decode the URL's `X-Amz-Date` (signing time) and `X-Amz-Expires`
     (validity seconds). The URL expires at `X-Amz-Date +
     X-Amz-Expires`.
   - Default max expiry: 7 days (604800 seconds) for IAM-user-signed
     URLs, 36 hours (129600) for STS-session-signed URLs, 1 hour for
     instance-role-signed URLs.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL expired.

2. **SigV4 credential scope / region mismatch.**
   - The URL's `X-Amz-Credential` includes `<key-id>/<date>/<region>/
     s3/aws4_request`. The region MUST match the bucket's region. A
     presigned URL for `us-east-1` used against a `us-west-2` bucket
     returns 403.
   - `aws s3api get-bucket-location --bucket <name>` to verify.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL region
     mismatch.

3. **Presigned for a different identity than intended.**
   - A presigned URL is bound to the signing principal's permissions at
     the time of signing. If the signer's permissions change (revoked,
     role deleted, policy tightened), the URL fails.
   - The signing principal's identity policy still applies — a presigned
     URL does NOT bypass IAM. Verify the signer has the action at
     signing time AND at request time.
   - **Output:** ROOT_CAUSE_FOUND, layer = presigned URL signer
     permission revoked.

4. **Bucket policy denies the calling principal.**
   - A presigned URL authenticates the request as the SIGNER, not as an
     anonymous principal. If the bucket policy explicitly denies the
     signer's ARN, the URL fails.
   - Read the bucket policy Deny statements.

5. **BPA blocking public presigned URL.**
   - A presigned URL is not "public" in the BPA sense — it is
     authenticated as the signer. BPA does NOT block presigned URLs
     unless `RestrictPublicBuckets` is True AND the bucket has a public
     policy. (Rare.)
   - However, if the bucket policy has `Principal: "*"` AND BPA is on,
     the policy is restricted to in-account principals only — a
     presigned URL signed by an out-of-account principal fails.

6. **Signature version mismatch.**
   - S3 presigned URLs use SigV4 (SigV2 is deprecated and rejected in
     modern regions). Verify the URL contains `X-Amz-Signature`
     (hex string), `X-Amz-SignedHeaders`, `X-Amz-Algorithm=AWS4-HMAC-SHA256`.
   - **Output:** ROOT_CAUSE_FOUND, layer = signature version mismatch.

### Step 6: Unexpected public access diagnostic path

Use when a bucket "should be private" but is publicly readable.

1. **Account-level BPA not enabled.**
   - The single most effective public-access block. If account-level BPA
     is off, bucket-level public access is allowed by any permissive
     bucket policy or ACL.
   - `aws s3control get-public-access-block --account-id <acct>`.
   - **Output:** ROOT_CAUSE_FOUND, layer = account-level BPA disabled.
     Recommend enable at account level (covers all current + future
     buckets).

2. **Bucket-level BPA not enabled (and account-level is also off).**
   - If account-level is off and bucket-level is off, the bucket inherits
     no BPA protection. Both scopes must be checked.

3. **Legacy ACL `AllUsers` / `AuthenticatedUsers`.**
   - `aws s3api get-bucket-acl --bucket <name>` and
     `aws s3api get-object-acl --bucket <name> --key <key>`.
   - `AllUsers` = `http://acs.amazonaws.com/groups/global/AllUsers`
     (anyone on the internet).
   - `AuthenticatedUsers` = anyone with an AWS account (free-tier
     signable — effectively public).
   - If Object Ownership is `BucketOwnerEnforced`, ACLs are disabled and
     any grant in the ACL output is a stale no-op.

4. **Public bucket policy (`Principal: "*"`).**
   - Read bucket policy. A statement with `Effect: Allow`,
     `Principal: "*"`, `Action: s3:GetObject` (or any read/write action),
     `Resource: arn:aws:s3:::bucket/*`, and no restrictive `Condition`
     is a public read path.
   - **Output:** ROOT_CAUSE_FOUND, layer = bucket policy wildcard Allow.

5. **Access Point policy with `Principal: "*"`.**
   - Each Access Point has its own policy. A restrictive bucket policy
     does NOT prevent access through a permissive Access Point.
   - Enumerate APs: `aws s3control list-access-points --account-id <acct>`
     (per region). For each AP, fetch its policy and audit.
   - **Output:** ROOT_CAUSE_FOUND, layer = Access Point policy wildcard
     Allow.

6. **MRAP (Multi-Region Access Point) propagating public access.**
   - A MRAP has a single global ARN. A public MRAP policy exposes all
     underlying regional buckets. Audit via
     `aws s3control get-multi-region-access-point-policy`.

7. **S3 website hosting amplifying exposure.**
   - A bucket configured for static website hosting requires public
     read. If the bucket is also website-enabled, it is indexed by
     search engines and discoverable via the
     `s3-website-<region>.amazonaws.com` endpoint.

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

```bash
# 1. Confirm the caller identity. Reveals assumed-role vs federated.
aws sts get-caller-identity --profile <profile>

# 2. Pull the CloudTrail event. errorMessage disambiguates implicit vs
#    explicit deny.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --profile <profile>

# 3. Read the bucket policy. Look for Allow matching the caller's ARN
#    AND Deny statements with matching conditions.
aws s3api get-bucket-policy --bucket <name> --profile <profile>

# 4. Read the bucket's BPA (both scopes).
aws s3control get-public-access-block --account-id <acct> --profile <profile>
aws s3api get-public-access-block --bucket <name> --profile <profile>

# 5. Read the bucket's Object Ownership setting.
aws s3api get-bucket-ownership-controls --bucket <name> --profile <profile>

# 6. Read the bucket ACL and the object ACL.
aws s3api get-bucket-acl --bucket <name> --profile <profile>
aws s3api get-object-acl --bucket <name> --key <key> --profile <profile>

# 7. Read the bucket's encryption configuration to identify the KMS key.
aws s3api get-bucket-encryption --bucket <name> --profile <profile>

# 8. For SSE-KMS buckets, read the key policy and check for the caller.
aws kms describe-key --key-id <key-id> --profile <profile>
aws kms get-key-policy --key-id <key-id> --policy-name default --profile <profile>

# 9. Simulate the caller's identity policy.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::<acct>:role/<role> \
  --action-names s3:GetObject kms:Decrypt \
  --resource-arns arn:aws:s3:::bucket/key arn:aws:kms:<region>:<acct>:key/<id> \
  --output json --profile <profile>

# 10. Check Object Lock retention on the specific key (PutObject /
     DeleteObject issues only).
aws s3api get-object-retention --bucket <name> --key <key> --profile <profile>
aws s3api get-object-legal-hold --bucket <name> --key <key> --profile <profile>

# 11. Enumerate S3 Access Points and read their policies.
for r in us-east-1 us-west-2 eu-west-1 ap-southeast-2; do
  aws s3control list-access-points --account-id <acct> --region "$r" --profile <profile>
done
aws s3control get-access-point-policy --account-id <acct> --name <ap> --profile <profile>

# 12. For VPC-attached callers, inspect the VPC endpoint policy.
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc> --profile <profile>

# 13. For CloudFront origins, verify the OAC vs OAI principal in the
#    bucket policy.
#    CloudFront OAC principal:
#      Principal.Service: cloudfront.amazonaws.com
#      Condition.StringEquals.aws:SourceArn: arn:aws:cloudfront::<acct>:distribution/<id>
```

## Expert edge cases

These patterns represent genuine, non-obvious S3 access failure causes
that a senior S3 engineer would catch but a generalist would miss.

### The `aws:SourceAccount` chain on S3 → KMS

When S3 reads an object encrypted with a KMS key on behalf of a caller,
the KMS `Decrypt` call is made BY S3 — not by the caller directly. A KMS
key policy that requires
`aws:SourceAccount: "<caller-acct>"` evaluates the S3 service call's
source account — which is the BUCKET's account, not the caller's.

Operators writing this condition expecting it to mean "the caller's
account" produce silent denies. Fix: scope on `aws:SourceArn` of the
bucket, OR list the bucket's account in `aws:SourceAccount`.

### VPC endpoint policy shadow

A VPC endpoint has its own policy independent of IAM. If a VPC endpoint
policy denies an action, the request fails even though every IAM policy
allows it. The CloudTrail event shows AccessDenied with no hint about
the VPC endpoint policy. The diagnostic is to bypass the endpoint (route
over the internet or a different endpoint) and see if the call succeeds.

VPC endpoint policies are the most overlooked layer because they live in
the VPC console, not IAM.

### CloudFront OAC replaces OAI

The legacy CloudFront Origin Access Identity (OAI) used a special IAM
principal (`arn:aws:iam::cloudfront:user/CloudFront Origin Access
Identity <id>`). The modern Origin Access Control (OAC) uses a service
principal (`service:cloudfront.amazonaws.com`) with the distribution ARN
in `aws:SourceArn` condition.

A bucket policy still using the OAI principal blocks OAC-authenticated
CloudFront requests. The error is 403 from CloudFront (origin denied).
Migrate the bucket policy to the OAC format when migrating from OAI.

### S3 Access Point bypasses bucket policy

Each Access Point has its own policy. Requests addressed through the AP
ARN are evaluated against the UNION of the bucket policy and the AP
policy. A restrictive bucket policy does NOT prevent access through a
permissive Access Point. Always enumerate APs and audit their policies
independently.

### Object Lock retention is irreversible for COMPLIANCE mode

An object under `COMPLIANCE` retention cannot be overwritten or deleted
by ANY principal — including root — until the retain-until date. The
error is 403 AccessDenied. `GOVERNANCE` mode can be bypassed by a
principal with `s3:BypassGovernanceRetention` permission (and root has
this by default). Verify the mode (`COMPLIANCE` vs `GOVERNANCE`) before
recommending a fix.

### Cross-account write to a `BucketOwnerEnforced` bucket

Object Ownership `BucketOwnerEnforced` (default for new buckets since
April 2022) disables ACLs entirely. Cross-account writers cannot use
ACL-based ownership transfer. They MUST include
`x-amz-acl: bucket-owner-full-control` in the PutObject request AND the
bucket policy must Allow the action for the cross-account principal.

This is the most common cause of "cross-account uploads were working
before but now fail" after a bucket ownership-controls migration.

### Presigned URL with a Session Policy

When a presigned URL is signed by an assumed-role session, the session
policy that was active at signing is enforced at request time. If the
session policy narrows the effective permissions (e.g., allows
`s3:GetObject` only on `personal-${aws:username}/*`), the presigned URL
fails for any key outside that pattern.

The session policy is NOT visible in the presigned URL — it must be
inferred from the `assumeRole` request parameters in CloudTrail.

### S3 directory buckets have different access semantics

S3 Directory Buckets (`<prefix>--x-s3` — used for S3 Express One Zone)
use Zonal Endpoints with different authentication. Standard S3 presigned
URLs do NOT work against directory buckets — they require
directory-bucket-specific signing. The error is 403 with no hint about
the bucket type. Verify the bucket type via
`aws s3api list-buckets --query 'Buckets[?Name==`<name>`].BucketType'`.

### Multi-Region Access Point (MRAP) policy propagation

A MRAP policy applies to requests through the MRAP ARN. Each underlying
regional bucket also has its own policy. The effective permission is the
union of MRAP policy + regional bucket policy. A permissive MRAP policy
exposes ALL regional buckets. Audit MRAP policy via
`aws s3control get-multi-region-access-point-policy`.

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

### For ARN-shape errors (GetObject on bucket ARN, ListBucket on object ARN)

1. Identify the action's required ARN shape:
   - Object-level actions → `arn:aws:s3:::bucket/*`
   - Bucket-level actions → `arn:aws:s3:::bucket`
2. Update the identity policy to include BOTH ARN shapes:
   ```json
   "Resource": [
     "arn:aws:s3:::bucket-name",
     "arn:aws:s3:::bucket-name/*"
   ]
   ```
3. Re-run `aws iam simulate-principal-policy` to confirm `allowed`.

### For KMS key policy cross-account denies

1. Identify the calling role ARN and the KMS key ARN.
2. Add a statement to the KEY policy granting `kms:Decrypt` (read) and/or
   `kms:GenerateDataKey` (write) to the caller's role ARN.
3. ALSO verify the caller's identity policy has the corresponding KMS
   action on the key ARN (cross-account intersection at KMS).
4. If the workflow uses grants, prefer `kms:CreateGrant` over editing the
   key policy for ephemeral access.

### For bucket policy missing cross-account principal

1. Add the caller's role ARN to the bucket policy's `Principal.AWS`:
   ```json
   {
     "Sid": "AllowCrossAccountRead",
     "Effect": "Allow",
     "Principal": { "AWS": "arn:aws:iam::<caller-acct>:role/<role>" },
     "Action": "s3:GetObject",
     "Resource": "arn:aws:s3:::bucket/*"
   }
   ```
2. Verify via simulator and via a real GetObject test.

### For BPA blocking intended public access

1. If the bucket is genuinely intended public (static website), the
   proper fix is CloudFront OAC in front of a private bucket — not
   disabling BPA. If a direct public bucket is required (rare, legacy),
   disable BPA at the bucket level (NOT account level) AND verify no
   SCP restricts BPA.
2. Account-level BPA should remain enabled in nearly all production
   accounts.

### For bucket policy SSE enforcement Deny

1. Update the PutObject request to include the required SSE header:
   ```
   aws s3api put-object --bucket <b> --key <k> --body <file> \
     --server-side-encryption aws:kms \
     --ssekms-key-id arn:aws:kms:<region>:<acct>:key/<id>
   ```

### For Object Lock retention / legal hold

1. `GOVERNANCE` mode: bypass with
   `s3:BypassGovernanceRetention` permission and a header
   `x-amz-bypass-governance-retention: TRUE` on the delete/overwrite.
2. `COMPLIANCE` mode: cannot be bypassed. Wait for the retain-until date
   or restore from a backup to a different key.

### For presigned URL failures

1. Re-sign with a fresh signing credential.
2. Verify the region matches the bucket via `aws s3api get-bucket-location`.
3. Verify the signer's identity policy allows the action at signing time.
4. Use short expirations (5-15 min) for interactive use; 7 days max for
   IAM-user-signed URLs.

### For CloudFront OAC migration

1. Update the bucket policy to use the OAC principal:
   ```json
   {
     "Sid": "AllowCloudFrontOAC",
     "Effect": "Allow",
     "Principal": { "Service": "cloudfront.amazonaws.com" },
     "Action": "s3:GetObject",
     "Resource": "arn:aws:s3:::bucket/*",
     "Condition": {
       "StringEquals": {
         "AWS:SourceArn": "arn:aws:cloudfront::<acct>:distribution/<dist-id>"
       }
     }
   }
   ```
2. Create the OAC in CloudFront console (replacing the legacy OAI).
3. Verify the CloudFront distribution can fetch objects.

## Recent AWS features (2024-2026)

- **S3 directory buckets (S3 Express One Zone) (2024-2025):** Single-AZ,
  single-digit-millisecond latency. Different authentication model —
  standard presigned URLs do NOT work. Zonal endpoint API only.
- **S3 Access Grants (2024):** Identity-based access management for S3
  data. Troubleshoot access via Access Grants instance + IAM role for
  Access Grants. Replaces some bucket-policy use cases.
- **S3 Tables (2024-2025):** Managed tabular storage (Apache Iceberg) in
  S3. Table bucket policies follow the same BPA and encryption model as
  standard buckets.
- **S3 Object Versioning default (2024-2025):** AWS is moving toward
  enabling Versioning by default on new buckets. Troubleshoot
  DeleteObject on versioned buckets separately (DeleteObject vs
  DeleteObjectVersion).
- **CloudFront OAC mandatory for new distributions (2024-2025):** New
  CloudFront distributions should use OAC. OAI is legacy. Bucket policies
  must use the OAC principal format.
- **BPA account-level default (2024-2025):** AWS is enabling account-level
  BPA by default on new accounts. Troubleshoot "public access was working
  before" by checking if account-level BPA was enabled by AWS during a
  recent account refresh.
- **Cross-Region Access Logging for DataSync / Multi-Region Access
  Points (2024-2025):** MRAP policies can now propagate access logs to
  multiple regions. Troubleshoot MRAP access by checking the policy at
  the MRAP ARN, not just the regional bucket.

## References

- `references/bpa-hierarchy-and-truth-tables.md` — full BPA scope
  interaction truth table (account-level vs bucket-level, per-setting
  effective values), worked examples for each combination.
- `references/kms-and-s3-cross-account-chain.md` — exhaustive walkthrough
  of the S3 → KMS service-to-service chain, `aws:SourceAccount` /
  `aws:SourceArn` semantics, and cross-account write scenarios with
  `BucketOwnerEnforced`.

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
