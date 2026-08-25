---
name: s3-bucket-policy-deployer
description: 'Provisions S3 bucket policies with production defaults: policy structure (Principal, Action, Resource, Condition), common patterns (HTTPS-only via aws:SecureTransport Deny, cross-account with external ID, VPC-endpoint-only via aws:SourceVpce, CloudFront Origin Access Control, AWS service access), policy vs ACL (policy preferred — ACLs are legacy), 20 KB policy size limit, condition keys (aws:SourceIp, aws:SourceVpc, aws:SourceVpce, s3:x-amz-acl, aws:SecureTransport), S3 Access Points policy delegation, S3 Multi-Region Access Point (MRAP) policy. Emits a READY_TO_DEPLOY checklist with verification commands. Use when attaching a bucket policy, enforcing HTTPS-only, restricting to a VPC endpoint, granting CloudFront OAC, or delegating via Access Points. Triggers: S3 bucket policy, put-bucket-policy, aws:SecureTransport, cross-account S3, VPC endpoint only, S3 CloudFront OAC, S3 Access Points delegation, MRAP policy.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with s3api (put-bucket-policy, get-bucket-policy, delete-bucket-policy), s3control (put-access-point-policy, put-multi-region-access-point-policy), cloudfront (get-origin-access-control). Works with Terraform aws_s3_bucket_policy and CloudFormation AWS::S3::BucketPolicy.
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
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, s3, bucket-policy, cloudfront-oac, vpc-endpoint, cloudops, deploy, storage
  dependencies: aws-orchestrator
  keywords: aws, s3, bucket policy, aws:SecureTransport, cross-account, vpc endpoint, aws:SourceVpce, aws:SourceVpc, aws:SourceIp, cloudfront oac, origin access control, s3:x-amz-acl, access points delegation, mrap policy, policy size limit, cloudops, deploy
  when_to_use: 'Invoke when the user wants to attach or replace an S3 bucket policy: enforcing HTTPS-only access (aws:SecureTransport Deny), granting cross-account access with conditions, restricting to a VPC endpoint (aws:SourceVpce), configuring CloudFront Origin Access Control (OAC), granting AWS service access, delegating via S3 Access Points, or configuring a Multi-Region Access Point policy. Do NOT invoke for bucket-level hardening without a policy (use s3-secure-bucket-deployer), for access point creation (use s3-access-points-deployer), for S3 ACLs (legacy — policies are preferred), or for auditing existing policies (use s3-public-access-auditor).'
---

# S3 Bucket Policy Deployer

An AWS CloudOps agent skill that provisions S3 bucket policies with
correct security defaults. The skill walks the operator through
policy structure validation, common access patterns (HTTPS-only,
cross-account, VPC-endpoint-only, CloudFront-OAC, service-access),
condition key selection, the 20 KB policy size limit, Access Points
policy delegation, and MRAP policies. It captures each policy
decision, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

S3 bucket policy, put-bucket-policy, aws:SecureTransport, HTTPS-only
S3, cross-account S3 access, VPC endpoint only S3, aws:SourceVpce,
aws:SourceVpc, aws:SourceIp, s3:x-amz-acl, CloudFront OAC, Origin
Access Control, AWS service access, S3 Access Points delegation,
MRAP policy, Multi-Region Access Point policy, policy size limit,
20 KB bucket policy.

## STRICT output contract

When this skill is invoked with a bucket-policy provisioning
request (a bucket name, access pattern, or a partial policy), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`BUCKET_POLICY:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Policy structure | Principal, Action, Resource, Condition |
| Step 2 — HTTPS-only (aws:SecureTransport) | Enforce TLS |
| Step 3 — Cross-account access | Grant another account |
| Step 4 — VPC-endpoint-only (aws:SourceVpce) | Private network |
| Step 5 — CloudFront OAC | CDN origin |
| Step 6 — AWS service access | Lambda, KMS, logging |
| Step 7 — Policy vs ACL | Policy preferred |
| Step 8 — 20 KB size limit | Large policies |
| Step 9 — Access Points delegation | Per-team policies |
| Step 10 — MRAP policy | Multi-region |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/policy-patterns.md | Pattern deep dive |
| references/provisioning-cli-commands.md | Copy-pasteable CLI |

## Mindset

**One-line takeaway:** A bucket policy is a JSON access-control
document attached directly to an S3 bucket. It is evaluated
alongside the IAM policy of the caller — effective permission is
the intersection. Bucket policies are the primary mechanism for
cross-account access, network-source restrictions, and enforcing
TLS; ACLs are legacy and should not be used.

The three misconceptions in full (bucket policy vs IAM policy override, `Principal: *` + Condition scoping, ACLs vs policies): [references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

Bucket-policy configurations are NOT independent. Many silently
no-op without their prerequisite; others conflict with each other.
Use this graph to sequence provisioning and debug "why is my policy
not taking effect?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Bucket policy | bucket exists; policy is valid JSON < 20 KB | **policy > 20 KB is rejected by put-bucket-policy** with `MalformedPolicy` | access control |
| `Principal: *` + Condition | valid condition key | **`Principal: *` with `aws:SourceVpce` still allows any identity in the VPC** — not identity-scoped | network-source restriction |
| `aws:SecureTransport: false` Deny | n/a | **Deny without `Bool` operator using `StringNotEquals` silently matches wrong values** — use `Bool` | HTTPS enforcement |
| `aws:SourceVpce` condition | VPC endpoint exists | **wrong endpoint ID silently blocks ALL traffic** or allows ALL if negated incorrectly | VPC-only access |
| `aws:SourceVpc` condition | request comes through a VPC endpoint with private DNS | **requests NOT through a VPC endpoint do not have `aws:SourceVpc` set** — condition silently does not match | VPC-scoped access |
| `aws:SourceIp` condition | valid CIDR | **`aws:SourceIp` is NOT populated for requests through a NAT gateway in some configs** — use `aws:SourceVpc` or `aws:SourceVpce` for VPC traffic | IP-based restriction |
| CloudFront OAC | OAC config exists in CloudFront | **legacy OAI (Origin Access Identity) and OAC are different** — OAC policy with an OAI principal silently fails | CDN origin access |
| Block Public Access | n/a | **BPA `RestrictPublicBuckets` silently blocks public policies even if the policy allows them** — BPA is a guardrail above the policy | public-access guardrail |
| Access Points delegation | access points exist | **bucket policy is still evaluated cumulatively with AP policy** — a Deny in the bucket policy cannot be overridden by the AP policy | per-team scoping |
| MRAP policy | MRAP exists | **MRAP policy and bucket policy are separate documents** — MRAP policy does not replace bucket policy | multi-region access |

**The `aws:SecureTransport` and `aws:SourceVpce` rows are the ones
a baseline model misses.** Using `StringNotEquals` instead of `Bool`
for SecureTransport, and using `aws:SourceVpc` for non-endpoint
traffic, both produce policies that look correct but silently match
the wrong condition. The procedure below forces the correct
condition operator for each pattern.

**Cross-dependency gotchas:**
- A bucket policy with `Effect: Deny` CANNOT be overridden by any
  IAM Allow. Deny wins in all cases. This is why overly broad Deny
  statements are dangerous.
- `Principal: *` makes the policy public — it allows any AWS
  identity (including from other accounts) subject to conditions.
  Always pair with conditions for non-public buckets.
- Block Public Access (BPA) at the bucket or account level is a
  guardrail ABOVE the policy. If BPA `RestrictPublicBuckets` is on,
  a policy with `Principal: *` is silently blocked even if the
  policy explicitly allows it.

## Expert heuristic: the aws:SecureTransport condition operator

The aws:SecureTransport operator deep dive (correct `Bool` vs wrong `StringNotEquals`, why, complete HTTPS-only Deny, key implication): [references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: aws:SourceVpce vs aws:SourceVpc vs aws:SourceIp

The aws:SourceVpce vs aws:SourceVpc vs aws:SourceIp comparison table, the endpoint-only-population gotcha, the correct VPC-endpoint-only pattern, and the SourceIp-through-endpoint caveat: [references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: policy vs ACL — policy always preferred

The policy-vs-ACL comparison table and the `BucketOwnerEnforced` production default: [references/advanced-patterns.md](references/advanced-patterns.md).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | How to verify |
|---|---|
| Bucket exists | `aws s3api head-bucket --bucket <name>` |
| Account ID | `aws sts get-caller-identity --query Account` |
| Policy JSON valid | `python3 -m json.tool policy.json` |
| Policy size < 20 KB | `wc -c policy.json` |
| VPC endpoint ID (if using aws:SourceVpce) | `aws ec2 describe-vpc-endpoints --vpc-endpoint-ids <id>` |
| CloudFront OAC config (if using OAC) | `aws cloudfront get-origin-access-control --id <id>` |
| Block Public Access posture | `aws s3api get-public-access-block --bucket <name>` |
| Object ownership (BucketOwnerEnforced) | `aws s3api get-bucket-ownership-controls --bucket <name>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Policy structure (Principal, Action, Resource, Condition)

Every bucket policy is a JSON document with a `Version` and a
`Statement` array. Each statement has four core elements.

Canonical four-element policy JSON example: [references/policy-patterns.md](references/policy-patterns.md).

**Element rules:**
- **Version:** always `"2012-10-17"` (NOT `2008-10-17` — the older
  version lacks support for policy variables).
- **Effect:** `Allow` or `Deny`. Deny overrides any Allow.
- **Principal:** the identity being granted/denied access. Use a
  specific ARN for identity-scoped access. Use `"*"` for everyone
  (public) — always pair with a Condition.
- **Action:** S3 actions (`s3:GetObject`, `s3:PutObject`,
  `s3:ListBucket`, etc.). Use fully-qualified names.
- **Resource:** the bucket ARN (`arn:aws:s3:::my-bucket`) for
  bucket-level actions and object ARN (`arn:aws:s3:::my-bucket/*`)
  for object-level actions. List both for policies that cover both.
- **Condition:** optional. See the expert heuristics for
  `aws:SecureTransport`, `aws:SourceVpce`, `aws:SourceVpc`.

**Common mistake:** listing only the bucket ARN (`arn:aws:s3:::bucket`)
but omitting the object ARN (`arn:aws:s3:::bucket/*`). Bucket-level
actions (`s3:ListBucket`) use the bucket ARN; object-level actions
(`s3:GetObject`, `s3:PutObject`) use the object ARN. A policy with
only the bucket ARN will deny all object operations.

## Step 2 — HTTPS-only (aws:SecureTransport)

See the "Expert heuristic: the aws:SecureTransport condition
operator" section. The canonical HTTPS-only Deny — **always use
`Bool`, never `StringNotEquals`:**

```json
{
  "Sid": "DenyInsecureTransport",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": { "Bool": { "aws:SecureTransport": "false" } }
}
```

## Step 3 — Cross-account access

To grant another account access, use the foreign account's role ARN
as Principal. Both sides must allow (bucket policy AND the foreign
role's IAM policy).

```json
{
  "Sid": "AllowCrossAccountRead",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::998877665544:role/PartnerRole" },
  "Action": ["s3:GetObject", "s3:ListBucket"],
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/shared/*"],
  "Condition": { "StringEquals": { "aws:ExternalId": "unique-external-id" } }
}
```

**Key rules:** use `aws:ExternalId` for third-party access (prevents
confused-deputy). Scope `Resource` to specific prefixes when
possible. **Common mistake:** granting `:root` instead of a specific
role ARN — `:root` delegates to the ENTIRE foreign account.

## Step 4 — VPC-endpoint-only (aws:SourceVpce)

See the "Expert heuristic: aws:SourceVpce vs aws:SourceVpc vs
aws:SourceIp" section. The VPC-endpoint-only Deny:

```json
{
  "Sid": "DenyNotFromVpcEndpoint",
  "Effect": "Deny",
  "Principal": "*",
  "Action": "s3:*",
  "Resource": ["arn:aws:s3:::my-bucket", "arn:aws:s3:::my-bucket/*"],
  "Condition": { "StringNotEquals": { "aws:SourceVpce": "vpce-0abc123def456" } }
}
```

**Key rule:** this Deny blocks ALL traffic not from the specified
VPC endpoint. Verify the endpoint ID before applying — a wrong ID
blocks all access.

## Step 5 — CloudFront Origin Access Control (OAC)

CloudFront OAC is the successor to the legacy Origin Access
Identity (OAI). OAC supports SSE-KMS and all CloudFront features.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontServicePrincipalReadOnly",
      "Effect": "Allow",
      "Principal": { "Service": "cloudfront.amazonaws.com" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456"
        }
      }
    }
  ]
}
```

**Key rules:**
- Use `Principal: { "Service": "cloudfront.amazonaws.com" }` (not
  the OAI canonical user ID).
- The `AWS:SourceArn` condition restricts access to a specific
  CloudFront distribution. Without it, ANY CloudFront distribution
  in the account can access the bucket.
- OAC supports SSE-KMS (OAI did not).
- The OAC configuration must exist in CloudFront first
  (`create-origin-access-control`).

**Common mistake:** using the legacy OAI principal (canonical user
ID `c4c1ede66af53448b93e28bd014fbedd65`) instead of the OAC
service principal. OAI is legacy; always use OAC.

## Step 6 — AWS service access

To grant an AWS service (Lambda, KMS, Config, logging) access to a
bucket, use the service principal with a condition.

```json
{
  "Sid": "AllowLambdaLogging",
  "Effect": "Allow",
  "Principal": { "Service": "logging.amazonaws.com" },
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::my-bucket/logs/*",
  "Condition": {
    "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control" }
  }
}
```

**Key rule:** `s3:x-amz-acl: bucket-owner-full-control` ensures the
bucket owner (not the writing service) owns the objects — critical
for cross-account logging. Without it, the service account owns
the objects and the bucket account cannot read them.

## Step 7 — Policy vs ACL (policy preferred)

See the "Expert heuristic: policy vs ACL" section. Production
default: disable ACLs with `BucketOwnerEnforced` ownership:

Disable-ACLs CLI (`put-bucket-ownership-controls` with `BucketOwnerEnforced`): [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

This disables ACLs entirely — all access control flows through
bucket policies and IAM.

## Step 8 — 20 KB policy size limit

S3 bucket policies have a maximum size of 20 KB. Policies exceeding
this limit are rejected by `put-bucket-policy` with
`MalformedPolicy`.

**Mitigations for large policies:**

| Strategy | When to use |
|---|---|
| Use wildcard prefixes | When many prefixes share the same access pattern |
| Use S3 Access Points | When different teams need different policies on the same bucket |
| Use IAM policies instead | When the policy grants access to specific roles (not cross-account) |
| Reduce statement count | Merge similar statements with multi-action / multi-resource arrays |

Policy-size verification commands (`wc -c`, 20 KB limit): [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

**Common mistake:** adding a statement per team/department until
the policy exceeds 20 KB. Use Access Points (Step 9) to delegate
per-team policies instead of cramming everything into one bucket
policy.

## Step 9 — Access Points policy delegation

S3 Access Points allow attaching separate policies to named entry
points on a bucket. Each access point has its own policy, evaluated
alongside (not instead of) the bucket policy. Use Access Points to
avoid exceeding the 20 KB bucket-policy limit with per-team rules.

```bash
aws s3control put-access-point-policy \
  --account-id 123456789012 \
  --name team-a-ap \
  --policy file://ap-policy.json
```

The access point policy uses the access point ARN (not the bucket
ARN) as the resource:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::123456789012:role/TeamARole" },
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:us-east-1:123456789012:accesspoint/team-a-ap/team-a/*"
  }]
}
```

**Key rule:** the bucket policy is still evaluated. A Deny in the
bucket policy cannot be overridden by the AP policy. See
`s3-access-points-deployer` for the full access point procedure.

## Step 10 — MRAP policy

A Multi-Region Access Point (MRAP) has its own policy, separate
from the underlying bucket policies.

```bash
aws s3control put-multi-region-access-point-policy \
  --account-id 123456789012 \
  --details Name=my-mrap,Policy=file://mrap-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::123456789012:role/GlobalApp" },
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3::123456789012:accesspoint/my-mrap"
  }]
}
```

**Key rules:** MRAP ARN format differs — `arn:aws:s3::account:accesspoint/name`
(no region). MRAP policy does NOT replace bucket policies. MRAP
routes to nearest region; pre-existing objects NOT backfilled.

## Step 11 — Recent features

Recent AWS features detail (CloudFront OAC, BucketOwnerEnforced, Access Points delegation, MRAP policies, SourceVpc/SourceVpce, Batch Operations for ACL migration): [references/advanced-patterns.md](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER use `StringNotEquals` for `aws:SecureTransport`.** Use
   the `Bool` operator instead. `aws:SecureTransport` is a boolean
   key; `Bool` evaluates it canonically. `StringNotEquals` is
   fragile and can silently fail on edge-case clients. The
   correct pattern is `"Bool": { "aws:SecureTransport": "false" }`
   in a Deny statement.

2. **NEVER use S3 ACLs for access control.** ACLs are legacy,
   limited to 100 grants, cannot express conditions, and are
   ignored when Block Public Access is enabled. Always use bucket
   policies. Disable ACLs with `BucketOwnerEnforced` ownership.

3. **NEVER use `aws:SourceIp` for VPC-endpoint traffic.** The
   source IP becomes the endpoint's internal IP, not the client's.
   For VPC-based restrictions, use `aws:SourceVpce` (specific
   endpoint) or `aws:SourceVpc` (VPC-scoped). `aws:SourceIp` only
   works for direct internet requests.

4. **NEVER omit the object ARN (`arn:aws:s3:::bucket/*`) from the
   Resource list.** Bucket-level actions (`s3:ListBucket`) use the
   bucket ARN; object-level actions (`s3:GetObject`,
   `s3:PutObject`) use the object ARN. A policy with only the
   bucket ARN silently denies all object operations.

5. **NEVER use the legacy CloudFront OAI canonical user ID as the
   Principal.** OAI is legacy and does not support SSE-KMS. Always
   use OAC with `Principal: { "Service": "cloudfront.amazonaws.com" }`
   and `AWS:SourceArn` condition.

## Output format

```text
BUCKET_POLICY: <bucket-name> (<n> statements, <size> KB)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket exists: <name>
  [✓|✗] Policy version: 2012-10-17
  [✓|✗] Policy size: <n> KB (< 20 KB limit)
  [✓|✗] HTTPS-only (aws:SecureTransport Deny with Bool): present | not needed
  [✓|✗] Cross-account: <account-id> (<role-arn>, external-id: <id>)
  [✓|✗] VPC-endpoint-only (aws:SourceVpce): vpce-<id> | not needed
  [✓|✗] CloudFront OAC: distribution <arn> | not needed
  [✓|✗] Service access: <service> (s3:x-amz-acl: bucket-owner-full-control)
  [✓|✗] ACLs disabled: BucketOwnerEnforced
  [✓|✗] Block Public Access: all 4 settings True
  [✓|✗] Access Points delegation: <n> APs | none
  [✓|✗] MRAP policy: <mrap-name> | none
VERIFICATION_COMMANDS:
  aws s3api get-bucket-policy --bucket <name>
  aws s3api get-public-access-block --bucket <name>
  aws s3api get-bucket-ownership-controls --bucket <name>
```

### Worked example — HTTPS-only + cross-account + CloudFront OAC

```text
BUCKET_POLICY: prod-shared-data (3 statements, 1.8 KB)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket exists: prod-shared-data
  [✓] Policy version: 2012-10-17
  [✓] Policy size: 1.8 KB (< 20 KB limit)
  [✓] HTTPS-only (aws:SecureTransport Deny with Bool): present
  [✓] Cross-account: 998877665544 (arn:aws:iam::998877665544:role/PartnerRole, external-id: partner-ext-123)
  [✓] CloudFront OAC: distribution arn:aws:cloudfront::123456789012:distribution/E123ABCDEF456
  [✓] ACLs disabled: BucketOwnerEnforced
  [✓] Block Public Access: all 4 settings True
VERIFICATION_COMMANDS:
  aws s3api get-bucket-policy --bucket prod-shared-data
  aws s3api get-public-access-block --bucket prod-shared-data
  aws s3api get-bucket-ownership-controls --bucket prod-shared-data
  aws cloudfront get-origin-access-control --id E123ABCDEF456
```

## Error handling

All five failure scenarios (`MalformedPolicy`, applied-but-denied, SourceVpce not matching, CloudFront OAC 403, cross-account denied despite policy): [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — the three Mindset misconceptions, the aws:SecureTransport / SourceVpce-vs-SourceVpc-vs-SourceIp / policy-vs-ACL expert heuristics, recent AWS features
- [Error handling](references/error-handling.md) — put-bucket-policy failure scenarios and their diagnosis
- [Policy patterns](references/policy-patterns.md) — pattern comparison, per-pattern JSON, canonical policy-structure example
- [Provisioning CLI commands](references/provisioning-cli-commands.md) — full copy-pasteable CLI sequence, Terraform equivalent

## Domain

AWS CloudOps / S3 Bucket Policy Provisioning & Storage Access
Control Management.

## AWS documentation

- **Bucket policies** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html
- **Policy conditions** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html
- **aws:SecureTransport** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-securetransport
- **CloudFront OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **Object Ownership** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html
- **Access Points policies** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-points-policies.html
- **MRAP policies** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/MrapPolicy.html
- **Block Public Access** — https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html
