---
name: cloudfront-origin-access-control-deployer
description: 'Provisions Amazon CloudFront Origin Access Control (OAC) with production defaults: OAC creation (create-origin-access-control), S3 origin configuration (s3:GetObject via OAC), bucket policy update (cloudfront.amazonaws.com principal with StringEquals AWS:SourceArn condition), signing behavior (sigv4 vs always), Origin Access Identity (OAI) vs OAC migration with no downtime, multi-distribution to single bucket, SSE-KMS with OAC (sigv4 signing required, KMS key policy), origin type (S3 vs S3 bucket with Website Endpoint), CloudFront distribution configuration with OriginAccessControlId, and region restrictions. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a CloudFront OAC, securing an S3 origin behind CloudFront, migrating from OAI to OAC, configuring SSE-KMS with CloudFront, or serving an S3 bucket from multiple. Triggers: create cloudfront oac, origin access control, cloudfront s3 origin, oai to oac migration, cloudfront sse-kms, cloudfront bucket policy, s3 origin oac.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudfront and s3 access. Works with Terraform aws_cloudfront_origin_access_control / aws_cloudfront_distribution / aws_s3_bucket_policy resources and CloudFormation AWS::CloudFront::OriginAccessControl templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudfront, oac, cloudops, deploy, networking, provisioning, s3, sse-kms, cdn, origin-access-control
  dependencies: aws-orchestrator
  keywords: aws, cloudfront, origin access control, oac, s3 origin, cloudops, deploy, provisioning, oai, origin access identity, sse-kms, bucket policy, sigv4, multi-distribution, cdn
  when_to_use: Invoke when the user wants to create a CloudFront Origin Access Control (OAC) for an S3 origin, secure an S3 bucket behind CloudFront, migrate from OAI to OAC, configure SSE-KMS with a CloudFront distribution, serve an S3 bucket from multiple distributions, or understand OAC signing behavior. Do NOT invoke for CloudFront custom origins (ALB, EC2, on-premises — OAC is S3-only), Lambda@Edge, or CloudFront Functions.
---

# CloudFront Origin Access Control Deployer

An AWS CloudOps agent skill that provisions Amazon CloudFront
Origin Access Control (OAC) with correct defaults. The skill walks
the operator through OAC creation, S3 origin configuration, bucket
policy updates (cloudfront.amazonaws.com principal with SourceArn
condition), signing behavior selection (sigv4 for SSE-KMS), OAI-to-
OAC migration with no downtime, multi-distribution to single bucket
patterns, SSE-KMS key policy requirements, and the critical origin
type distinction (S3 vs S3 bucket with Website Endpoint), captures
all configuration decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create CloudFront OAC, origin access control, CloudFront S3 origin,
OAI to OAC migration, CloudFront SSE-KMS, CloudFront bucket policy,
S3 origin OAC, CloudFront multi-distribution.

## STRICT output contract

When this skill is invoked with a CloudFront-OAC-provisioning
request (create an OAC, secure an S3 origin behind CloudFront,
migrate from OAI to OAC, configure SSE-KMS with CloudFront, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `CLOUDFRONT_OAC:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — OAC vs OAI | Why OAC replaces OAI |
| Step 2 — Create the OAC | OAC creation |
| Step 3 — S3 bucket policy update | Granting CloudFront access |
| Step 4 — CloudFront distribution with OAC origin | Distribution config |
| Step 5 — Signing behavior (sigv4 vs always) | Signing protocol |
| Step 6 — SSE-KMS with OAC | KMS-encrypted buckets |
| Step 7 — Multi-distribution to single bucket | Shared bucket pattern |
| Step 8 — OAI to OAC migration (no downtime) | Migration |
| Step 9 — Origin type: S3 vs Website Endpoint | Origin type constraint |
| Step 10 — Region restrictions | Region scoping |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/oac-and-bucket-policy.md | OAC + bucket policy detail |
| references/oai-migration-and-sse-kms.md | Migration + KMS detail |

## Mindset

**One-line takeaway:** CloudFront Origin Access Control (OAC) is the
successor to Origin Access Identity (OAI). OAC is attached to a
CloudFront distribution's S3 origin and signs requests to the S3
bucket so that only CloudFront can read the objects. The S3 bucket
policy MUST grant `cloudfront.amazonaws.com` the `s3:GetObject`
permission with a condition matching the distribution ARN. OAC
supports SSE-KMS and POST requests; OAI does not. OAC ONLY works
with the S3 origin type — NOT with S3 buckets configured for static
website hosting (Website Endpoint).

Three misconceptions dominate CloudFront OAC misdesign at
provisioning time:

- **"Creating the OAC is enough to secure the bucket."** It is not.
  The OAC must be referenced by the distribution's S3 origin
  (OriginAccessControlId), AND the S3 bucket policy must grant
  `cloudfront.amazonaws.com` the `s3:GetObject` permission with a
  `StringEquals` condition on `AWS:SourceArn` (the distribution ARN).
  Without the bucket policy update, CloudFront gets 403 Forbidden
  from S3. This is the #1 cause of "my CloudFront returns AccessDenied"
  tickets.

- **"OAI and OAC are interchangeable."** They are NOT. OAC is the
  recommended approach for all new distributions. OAI does not support
  SSE-KMS-encrypted buckets or HTTP POST/PUT requests (OAI only signs
  GET/HEAD). OAC supports both. AWS recommends migrating from OAI to
  OAC; the migration can be done with zero downtime by adding the OAC
  alongside the existing OAI, updating the distribution, then removing
  the OAI.

- **"OAC works with any S3 bucket configuration."** It does NOT. OAC
  ONLY works with the S3 origin type (`my-bucket.s3.<region>.amazonaws.com`).
  If the bucket is configured for static website hosting
  (`my-bucket.s3-website-<region>.amazonaws.com`), OAC is NOT
  supported — the Website Endpoint does not accept the SigV4-signed
  requests that OAC produces.

## Configuration dependency graph (novel heuristic)

CloudFront OAC configurations are NOT independent. The OAC must be
created before the distribution references it. The bucket policy
must grant the distribution ARN. SSE-KMS requires both sigv4 signing
and KMS key policy updates. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| OAC (create-origin-access-control) | None — standalone resource | exists but does nothing until referenced by a distribution origin | the signing identity |
| Distribution S3 origin (OriginAccessControlId) | OAC exists; S3 bucket exists | if OriginAccessControlId is not set, OAC is not used (s3:GetObject 403 if bucket is private) | CloudFront signs requests via OAC |
| S3 bucket policy (cloudfront.amazonaws.com) | Distribution exists (for ARN); bucket exists | if policy references wrong distribution ARN or omits the condition, CloudFront gets 403 from S3 | S3 serves objects to CloudFront |
| Signing behavior (sigv4 / always-sign) | OAC created with SigningBehavior | sigv4 is REQUIRED for SSE-KMS; no-override does NOT work with KMS | access to SSE-KMS objects |
| SSE-KMS key policy | KMS key exists; OAC uses sigv4 | MUST allow cloudfront.amazonaws.com kms:Decrypt; without it, 403 from KMS via S3 | CloudFront reads KMS-encrypted objects |
| Origin type (S3 vs Website Endpoint) | Bucket exists; website config determined | OAC ONLY supports S3 origin type; Website Endpoint silently bypasses OAC signing | correct OAC behavior |

**The bucket-policy row is the one a baseline model misses.** Creating
the OAC and referencing it in the distribution is necessary but NOT
sufficient. The S3 bucket policy must explicitly grant
`cloudfront.amazonaws.com` the `s3:GetObject` permission with a
condition matching the distribution ARN.

**Cross-dependency gotchas:**
- The bucket policy condition uses `AWS:SourceArn` (distribution ARN),
  NOT `AWS:SourceAccount`. Using SourceAccount is broader and less
  secure — it grants ALL distributions in the account access.
- For SSE-KMS buckets, BOTH the S3 bucket policy AND the KMS key
  policy must be updated. Missing either results in 403.
- The OAC signing behavior `always-sign` (sigv4) is REQUIRED for
  SSE-KMS buckets. `no-override` lets the client control signing and
  does NOT work with SSE-KMS.
- For multi-distribution to single bucket, the bucket policy condition
  must list ALL distribution ARNs.

## Expert heuristic: OAC replaces OAI

Expert heuristic — OAC replaces OAI (decision tree, SSE-KMS and POST/PUT support, global-resource note) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when deciding OAC vs OAI.

## Expert heuristic: bucket policy uses cloudfront.amazonaws.com

Expert heuristic — bucket policy principal (cloudfront.amazonaws.com with AWS:SourceArn, full JSON) moved verbatim to [references/oac-and-bucket-policy.md](references/oac-and-bucket-policy.md).
Load it when writing the bucket policy.

## Expert heuristic: sigv4 signing for SSE-KMS origins

Expert heuristic — sigv4 signing for SSE-KMS origins (always-sign vs no-override vs never-sign) moved verbatim to [references/oai-migration-and-sse-kms.md](references/oai-migration-and-sse-kms.md).
Load it when choosing SigningBehavior.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket exists | OAC serves objects from an S3 bucket | `aws s3api head-bucket --bucket <name>` |
| S3 bucket NOT configured for website hosting | OAC only supports S3 origin type, not Website Endpoint | `aws s3api get-bucket-website --bucket <name>` (NoSuchWebsiteConfiguration expected) |
| CloudFront distribution exists (or will be created) | OAC must be referenced by a distribution origin | `aws cloudfront list-distributions` |
| AWS account ID known | Distribution ARN requires account ID for bucket policy | `aws sts get-caller-identity` |
| SSE-KMS key identified (if SSE-KMS) | KMS key policy must grant cloudfront kms:Decrypt | `aws s3api get-bucket-encryption --bucket <name>` |
| IAM permission for cloudfront + s3 + kms | Creating OAC, updating distribution, policies | Verify cloudfront:*, s3:PutBucketPolicy, kms:PutKeyPolicy |
| Region of S3 bucket known | DomainName must include region for non-us-east-1 buckets | `aws s3api get-bucket-location --bucket <name>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — OAC vs OAI

OAC (Origin Access Control) is the successor to OAI (Origin Access
Identity). Both secure an S3 origin behind CloudFront, but OAC
supports features that OAI does not.

| Feature | OAI (legacy) | OAC (recommended) |
|---|---|---|
| SSE-KMS support | NOT supported | Supported (with sigv4 signing) |
| POST/PUT requests | NOT supported (GET/HEAD only) | Supported (all methods) |
| Bucket policy principal | Canonical user ID of the OAI | `cloudfront.amazonaws.com` service principal |
| Bucket policy condition | None (OAI reference is implicit) | `AWS:SourceArn` = distribution ARN |
| Recommended for new distributions | No | Yes |
| Migration path | Migrate to OAC | N/A |

**Always use OAC for new distributions.** Plan migration from OAI to
OAC for existing distributions (see Step 8).

## Step 2 — Create the OAC

Create the OAC using `create-origin-access-control`. The OAC is a
standalone resource later referenced by the distribution's S3 origin.

```bash
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{
      "Name": "oac-my-bucket",
      "Description": "OAC for my-bucket S3 origin",
      "SigningProtocol": "sigv4",
      "SigningBehavior": "always-sign",
      "OriginAccessControlOriginType": "s3"
    }' \
  --query 'OriginAccessControl.Id' --output text)

echo "OAC ID: $OAC_ID"
```

**Key fields:**
- `SigningProtocol`: always `sigv4` (the only supported value).
- `SigningBehavior`: `always-sign` (recommended, required for SSE-KMS),
  `never-sign` (public buckets), or `no-override` (client-controlled).
- `OriginAccessControlOriginType`: always `s3` (OAC does not work with
  custom origins).

## Step 3 — S3 bucket policy update

The S3 bucket policy MUST grant `cloudfront.amazonaws.com` the
`s3:GetObject` permission with a condition matching the distribution
ARN. This is the critical step a baseline model often misses.

```bash
aws s3api put-bucket-policy --bucket my-bucket --policy '{
  "Version": "2012-10-17",
  "Statement": {
    "Sid": "AllowCloudFrontServicePrincipalReadOnly",
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::my-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE"
      }
    }
  }
}'
```

**Critical:**
- The principal is `cloudfront.amazonaws.com` (service principal), NOT
  the OAC ID or ARN.
- The `AWS:SourceArn` condition MUST match the distribution ARN
  exactly. This restricts access to the specific distribution.
- The bucket must NOT be public. Remove any `Principal: "*"` grants —
  OAC replaces public access.

Step 3 multi-distribution AWS:SourceArn list JSON moved verbatim to [references/oac-and-bucket-policy.md](references/oac-and-bucket-policy.md).
Load it when several distributions share a bucket.

## Step 4 — CloudFront distribution with OAC origin

The distribution's S3 origin must reference the OAC ID via
`OriginAccessControlId`.

**Update an existing distribution to add OAC:**

```bash
# 1. Get current config and ETag
ETAG=$(aws cloudfront get-distribution-config \
  --id EDFDVBD6EXAMPLE \
  --query 'ETag' --output text)

# 2. Set Origins.Items[0].OriginAccessControlId = OAC_ID in the config
#    Leave S3OriginConfig.OriginAccessIdentity empty (OAC replaces OAI)
aws cloudfront update-distribution \
  --id EDFDVBD6EXAMPLE \
  --if-match "$ETAG" \
  --distribution-config file://updated-config.json
```

**Key origin config fields:**
- `DomainName`: S3 regional endpoint
  (`my-bucket.s3.<region>.amazonaws.com`).
- `OriginAccessControlId`: the OAC ID from Step 2.
- `S3OriginConfig.OriginAccessIdentity`: empty when using OAC.

**Common mistake:** including both `OriginAccessControlId` (OAC) and a
non-empty `S3OriginConfig.OriginAccessIdentity` (OAI) on the same
origin. OAC takes precedence, but clean this up during migration.

## Step 5 — Signing behavior (sigv4 vs always)

The OAC `SigningBehavior` determines when CloudFront signs origin
requests.

| SigningBehavior | When to use | SSE-KMS support |
|---|---|---|
| `always-sign` | All new OAC configurations; SSE-KMS; POST/PUT | Yes (REQUIRED) |
| `never-sign` | Public S3 buckets (rare — defeats OAC purpose) | No |
| `no-override` | Client-controlled signing (viewer has Authorization header) | No (unreliable) |

**For SSE-KMS-encrypted buckets, ALWAYS use `always-sign`.** Without
sigv4-signed requests, S3 cannot authorize KMS decryption.

```text
SSE-KMS bucket signing flow:
  Viewer → CloudFront → S3 (SSE-KMS bucket)
    CloudFront signs with sigv4 (always-sign)
    → S3 calls KMS: does cloudfront.amazonaws.com have kms:Decrypt?
    → Yes (key policy): object decrypted, served to viewer
    → No (missing key policy): 403 Forbidden from KMS via S3
```

## Step 6 — SSE-KMS with OAC

For SSE-KMS-encrypted S3 buckets, OAC with `always-sign` is required,
AND the KMS key policy must grant `cloudfront.amazonaws.com` the
`kms:Decrypt` permission.

Step 6 SSE-KMS verification commands and KMS key policy CLI moved verbatim to [references/oai-migration-and-sse-kms.md](references/oai-migration-and-sse-kms.md).
Load it when the bucket is SSE-KMS encrypted.

## Step 7 — Multi-distribution to single bucket

Step 7 multi-distribution bucket policy (multi-ARN SourceArn list, AWS:SourceAccount alternative) moved verbatim to [references/oac-and-bucket-policy.md](references/oac-and-bucket-policy.md).
Load it when sharing one bucket across distributions.

## Step 8 — OAI to OAC migration (no downtime)

Step 8 zero-downtime OAI-to-OAC migration flow (dual-grant bucket policy, distribution cutover, OAI cleanup) moved verbatim to [references/oai-migration-and-sse-kms.md](references/oai-migration-and-sse-kms.md).
Load it when migrating a legacy OAI distribution.

## Step 9 — Origin type: S3 vs S3 bucket with Website Endpoint

OAC ONLY works with the S3 origin type. It does NOT work with S3
buckets configured for static website hosting (Website Endpoint).

```text
Origin type decision:
  ├── S3 bucket WITHOUT website hosting → S3 origin type
  │     DomainName: my-bucket.s3.us-east-1.amazonaws.com
  │     OAC: SUPPORTED ✓
  ├── S3 bucket WITH website hosting → S3 Website Endpoint origin
  │     DomainName: my-bucket.s3-website-us-east-1.amazonaws.com
  │     OAC: NOT SUPPORTED ✗ (Website Endpoint does not process SigV4)
  └── Custom origin (ALB, EC2, on-prem) → Custom origin type
        OAC: NOT SUPPORTED ✗ (OAC is S3-only)
```

**Verify the bucket is NOT configured for website hosting:**

```bash
aws s3api get-bucket-website --bucket my-bucket
# Expected error: NoSuchWebsiteConfiguration (good — OAC will work)
# If a config IS returned, OAC will NOT work — remove it:
# aws s3api delete-bucket-website --bucket my-bucket
```

**Common mistake:** using the Website Endpoint DomainName with an OAC.
The distribution accepts the configuration, but OAC signing does not
work — CloudFront receives 403 because the Website Endpoint does not
process SigV4 signatures like the S3 REST API.

## Step 10 — Region restrictions

OAC is a global CloudFront resource. The S3 bucket can be in any
region, but the origin DomainName must include the region for non-
us-east-1 buckets.

```text
S3 origin DomainName by region:
  ├── us-east-1 → my-bucket.s3.amazonaws.com (or s3.us-east-1.amazonaws.com)
  ├── us-west-2 → my-bucket.s3.us-west-2.amazonaws.com (MUST include region)
  ├── eu-west-1 → my-bucket.s3.eu-west-1.amazonaws.com (MUST include region)
  └── ap-southeast-2 → my-bucket.s3.ap-southeast-2.amazonaws.com
```

**For region-restricted content**, use CloudFront geo restriction
(distribution-level, not OAC):

```bash
# Set GeoRestriction in the distribution config
# GeoRestriction: { RestrictionType: "whitelist", Locations: ["US","CA","GB"] }
```

## Step 11 — Recent features

Step 11 recent features (OAC GA, Terraform support, continuous deployment, SSE-KMS clarification, VPC origins) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing or migrating.

## NEVER do these things

1. **NEVER create an OAC without updating the S3 bucket policy.** The
   policy MUST grant `cloudfront.amazonaws.com` `s3:GetObject` with
   `AWS:SourceArn` matching the distribution ARN. Without it, 403.

2. **NEVER use the OAC ID as the principal in the bucket policy.** The
   principal is always `cloudfront.amazonaws.com`. S3 bucket policies
   do not understand OAC IDs.

3. **NEVER use OAC with an S3 Website Endpoint origin.** OAC ONLY
   supports the S3 origin type. Website Endpoints do not process
   SigV4-signed requests correctly.

4. **NEVER use `never-sign` or `no-override` with SSE-KMS-encrypted
   buckets.** SSE-KMS requires `always-sign` (sigv4). Without sigv4,
   S3 cannot authorize KMS decryption — CloudFront gets 403.

5. **NEVER forget the KMS key policy for SSE-KMS buckets.** Both the
   S3 bucket policy (s3:GetObject) AND the KMS key policy
   (kms:Decrypt) must grant `cloudfront.amazonaws.com` access.

6. **NEVER use `AWS:SourceAccount` when `AWS:SourceArn` is feasible.**
   SourceAccount grants ALL distributions in the account access.
   SourceArn restricts to a specific distribution.

7. **NEVER omit the region from the S3 origin DomainName for non-
   us-east-1 buckets.** Must be `my-bucket.s3.<region>.amazonaws.com`.

8. **NEVER leave the bucket public when using OAC.** Remove any
   `Principal: "*"` grants. The bucket should only be accessible via
   CloudFront.

9. **NEVER delete an OAI during migration before verifying the OAC
   works.** Keep both active, verify traffic, then remove the OAI.
   Deleting too early causes downtime.

10. **NEVER assume OAC works with custom origins.** OAC is S3-only.
    For ALB/EC2/on-prem, use signed URLs, signed cookies, or other
    access control.

## Output format

```text
CLOUDFRONT_OAC: <distribution-id> → <bucket-name> (<oac-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] S3 bucket: <bucket-name> (region: <region>)
  [✓|✗] Origin type: S3 (not Website Endpoint) | FAIL (Website Endpoint — OAC not supported)
  [✓|✗] OAC created: <oac-id> (SigningBehavior: always-sign | never-sign | no-override)
  [✓|✗] Distribution origin: <distribution-id> → OriginAccessControlId=<oac-id>
  [✓|✗] S3 bucket policy: cloudfront.amazonaws.com s3:GetObject with AWS:SourceArn=<distribution-arn>
  [✓|✗] SSE-KMS: enabled (KMS key policy grants cloudfront.amazonaws.com kms:Decrypt) | disabled
  [✓|✗] Multi-distribution: <count> distributions in bucket policy SourceArn list | single distribution
  [✓|✗] OAI migration: OAI removed (OAC is sole access control) | N/A (new distribution)
  [✓|✗] Bucket public access: blocked (OAC only) | WARNING (bucket is public)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudfront get-origin-access-control --id <oac-id>
  aws cloudfront get-distribution-config --id <distribution-id>
  aws s3api get-bucket-policy --bucket <bucket-name>
```

### Worked example — S3 origin with OAC and SSE-KMS

```text
CLOUDFRONT_OAC: EDFDVBD6EXAMPLE → my-secure-bucket (E2QWRUOACID123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] S3 bucket: my-secure-bucket (region: us-east-1)
  [✓] Origin type: S3 (not Website Endpoint)
  [✓] OAC created: E2QWRUOACID123 (SigningBehavior: always-sign)
  [✓] Distribution origin: EDFDVBD6EXAMPLE → OriginAccessControlId=E2QWRUOACID123
  [✓] S3 bucket policy: cloudfront.amazonaws.com s3:GetObject with AWS:SourceArn=arn:aws:cloudfront::111122223333:distribution/EDFDVBD6EXAMPLE
  [✓] SSE-KMS: enabled (KMS key policy grants cloudfront.amazonaws.com kms:Decrypt)
  [✓] Multi-distribution: single distribution
  [✓] OAI migration: N/A (new distribution)
  [✓] Bucket public access: blocked (OAC only)
  [✓] Tags: Environment=production, OriginType=s3
VERIFICATION_COMMANDS:
  aws cloudfront get-origin-access-control --id E2QWRUOACID123
  aws cloudfront get-distribution-config --id EDFDVBD6EXAMPLE
  aws s3api get-bucket-policy --bucket my-secure-bucket
```

## Error handling

Error handling deep dives (S3 403, KMS 403, OAC not signing, migration downtime, multi-distribution 403) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load it when the distribution returns 403.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — OAC-replaces-OAI heuristic and recent features moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — 403/migration failure deep dives moved from SKILL.md
- [references/oac-and-bucket-policy.md](references/oac-and-bucket-policy.md) — OAC parameters, bucket policy patterns, signing deep dive (now also holds the bucket-policy-principal heuristic and the multi-distribution JSON)
- [references/oai-migration-and-sse-kms.md](references/oai-migration-and-sse-kms.md) — migration and SSE-KMS detail (now also holds the sigv4 heuristic, KMS key policy CLI, and the Step 8 migration flow)

## Domain

AWS CloudOps / Amazon CloudFront Origin Access Control Provisioning &
S3 Origin Security.

## AWS documentation

- **CloudFront OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **Create OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html#oac-create
- **S3 bucket policy for OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html#S3BucketPolicy-for-OAC
- **Migrate from OAI to OAC** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html#migrate-from-oai-to-oac
- **SSE-KMS with CloudFront** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html#oac-sse-kms
- **CloudFront API (create-origin-access-control)** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_CreateOriginAccessControl.html
- **S3 origin vs Website Endpoint** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/DownloadDistS3AndCustomOrigins.html
- **CloudFront geo restriction** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/georestrictions.html
