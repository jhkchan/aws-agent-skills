---
name: s3-access-points-deployer
description: >-
  Provisions S3 Access Points and dependent primitives with production
  defaults: network-origin selection (Internet vs VPC), VPC endpoint +
  private DNS, the through-AP-only bucket invariant via
  s3:DataAccessPointArn bucket-policy Deny, per-AP prefix-scoped policies
  distinct from the bucket policy, Object Lambda APs (supporting AP +
  transform Lambda + reserved concurrency), Multi-Region Access Points
  (MRAP) with failover, DNS-compatible aliases, per-AP Block Public
  Access, cross-account AP delegation with containment, and S3 on
  Outposts APs. Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every
  item verified and copy-pasteable s3control / s3api / ec2 / lambda
  commands. Use when creating a per-team or per-application access point,
  enforcing VPC-only access, transforming objects on retrieval, building
  a multi-region active-active or failover data plane, or hardening an
  existing AP. Triggers: S3 access point, create access point, VPC-only
  bucket, Object Lambda, MRAP, alias, cross-account AP, Outposts AP.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Live provisioning uses AWS CLI v2 with s3control (create-access-
  point, put-access-point-policy, get-access-point, create-multi-region-
  access-point, create-access-point-for-object-lambda), s3api
  (put-bucket-policy), lambda (create-function, put-function-event-invoke-
  config), ec2 (describe-vpc-endpoints, modify-vpc-endpoint), and
  cloudformation / terraform aws_s3_access_point equivalents.
keywords:
  - aws
  - s3
  - s3-access-points
  - access-point
  - object-lambda
  - mrap
  - multi-region
  - vpc-endpoint
  - private-dns
  - network-origin
  - vpc-only
  - bucket-policy
  - access-point-policy
  - cross-account
  - s3-on-outposts
  - alias
  - cloudops
  - deploy
tags:
  - aws
  - s3
  - access-point
  - object-lambda
  - mrap
  - vpc-endpoint
  - deploy
  - storage
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
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new S3 Access Point (Internet or VPC network origin),
    enforcing VPC-only access to a shared bucket via VPC endpoint + private
    DNS + bucket-policy Deny, creating an Object Lambda access point to
    transform objects on retrieval, building a Multi-Region Access Point
    for active-active or failover data access, scoping per-team or
    per-application access via prefix-scoped access point policies,
    configuring cross-account access point delegation, hardening an
    existing access point with BPA, or generating IaC (CloudFormation /
    Terraform) for any of the above. Do NOT invoke for plain bucket
    hardening without an access point (use s3-secure-bucket-deployer), or
    for S3 Tables / S3 Catalog (separate primitives).
  activation_triggers:
    - "S3 access point"
    - "create access point"
    - "VPC-only bucket access"
    - "Object Lambda"
    - "multi-region access point"
    - "MRAP"
    - "S3 access point alias"
    - "access point policy"
    - "cross-account access point"
    - "S3 on Outposts access point"
    - "Block Public Access on access point"
  invocation_schema: >-
    Input: either (a) a bucket ARN/name + access point name + network
    origin (Internet|VPC) + optional VPC ID, or (b) an Object Lambda
    spec (supporting AP + Lambda transform), or (c) a Multi-Region
    Access Point spec (regions + failover). Output: deterministic
    ACCESS_POINT / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per
    the STRICT output contract, where VERDICT is READY_TO_DEPLOY or
    PREREQUISITES_MISSING.
---

# S3 Access Points Deployer

## What this skill does

Provisions S3 Access Points and surrounding primitives (VPC endpoint,
through-AP-only bucket-policy invariant, Object Lambda transform,
Multi-Region Access Point) with correct defaults. The skill walks a
9-step procedure, surfaces the silent-failure modes unique to access
points (most dangerous: the bucket policy is NOT enforced through the
AP hostname by default, and MRAP does not backfill), and emits a
READY_TO_DEPLOY checklist verifying every item against actual state.
The single most common incident this skill prevents: an operator
creates a VPC-origin AP, assumes the bucket is VPC-only, but the
bucket is still reachable via its global hostname by any principal
with `s3:GetObject` — the VPC-only invariant requires an explicit
bucket-policy Deny keyed on `s3:DataAccessPointArn`.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds, dependency graph | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 9-step order matters; network-origin semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "policy doesn't take effect" |
| **Expert heuristic** | The VPC-only invariant myth; MRAP cost-amplification; OLAP concurrency | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required ACCESS_POINT / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Outposts AP, MRAP failover improvements, Object Lambda deprecation signals | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm bucket baseline (BPA, SSE, versioning) | — | AP inherits bucket weaknesses |
| 2 | Choose network origin (Internet vs VPC) | Yes | wrong origin = wrong threat model |
| 3 | (VPC only) Provision / confirm VPC gateway endpoint + private DNS | Yes | VPC-only AP silently bypassable via global hostname |
| 4 | Create the access point | Yes | — |
| 5 | Attach access point policy (scope to prefix + principal) | Yes | over-broad principal |
| 6 | Enforce "through-AP-only" via bucket policy Deny on `s3:DataAccessPointArn == null` | Yes | **silent bypass** via bucket hostname |
| 7 | Per-AP Block Public Access (VPC-origin APs only) | Yes | public-ACL leak through AP |
| 8 | Optional: Object Lambda AP / MRAP / cross-account delegation / alias | Yes | see per-feature silent failures |
| 9 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** bucket baseline before AP (the AP
does not override bucket-level weaknesses); VPC endpoint before AP
creation when the AP is VPC-origin (otherwise the AP creates but is
unreachable and operators fall back to the global hostname); AP before
AP policy; AP policy before the through-AP-only bucket-policy Deny (the
Deny references access-point ARNs); per-AP BPA last among the public-
access controls (it is the innermost layer). Rationale and the silent-
failure table are below.

## Activation keywords

S3 access point, create access point, VPC-only bucket, network origin,
VPC endpoint for S3, private DNS for S3, bucket access through access
point only, s3:DataAccessPointArn, access point policy, prefix-scoped
policy, Object Lambda access point, transform S3 objects on the fly,
multi-region access point, MRAP, MRAP failover, S3 access point alias,
DNS-compatible hostname, per-access-point Block Public Access,
cross-account access point, S3 on Outposts access point, Outposts AP.

## Invocation contract (hard requirement)

When this skill is invoked with an access-point provisioning request,
the agent MUST respond with the checklist defined in §"STRICT output
contract" using the literal all-caps labels `ACCESS_POINT:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Reasoning framework (why the provisioning order matters)

S3 Access Points look like "a named entry point to a bucket" but the
underlying model has four traps:

1. **An access point is a separate ARN with its own policy, but the
   BUCKET policy still applies cumulatively.** Effective permission on
   a request through the AP = (AP policy) ∩ (bucket policy) ∩ (IAM).
   A permissive bucket policy cannot be tightened by tightening the AP
   policy. A restrictive bucket policy can silently block AP traffic.

2. **The bucket's global hostname stays reachable after AP creation.**
   Creating a VPC-origin AP does NOT disable the
   `s3.<region>.amazonaws.com` path. A principal with `s3:GetObject`
   in the bucket policy still reaches data through the global hostname.
   The only way to make a bucket truly VPC-only is a bucket policy
   `Deny` with `Null: { s3:DataAccessPointArn: true }` — deny if the
   request did NOT come through an access point.

3. **The AP policy is NOT a subset of the bucket policy.** It is a
   parallel document. Operators who copy a bucket policy into the AP
   policy and leave the bucket ARN in `Resource` produce dead text —
   the AP ARN is the resource on AP-routed requests.

4. **MRAP and Object Lambda have their own silent-failure modes.** MRAP
   does not backfill. Object Lambda invokes synchronously; throttles
   surface to the client as S3 errors, not Lambda errors.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Access point (Internet origin) | bucket exists in same region | — | AP policy; AP BPA; alias |
| Access point (VPC origin) | bucket exists; VPC ID valid | VPC ID from another account silently accepted (cross-account VPC is allowed but unintended) | VPC-only bucket enforcement |
| VPC gateway endpoint for S3 | route table attached to VPC | **endpoint policy Permissive = bucket reachable via global hostname inside the VPC, defeating "VPC-only"** | private DNS; in-VPC only traffic |
| Private DNS for S3 (interface endpoint, optional) | interface endpoint in VPC | private DNS off → S3 SDK still resolves to public IP; works but is not "VPC-only" | in-VPC DNS resolution |
| Per-AP Block Public Access | access point exists | — | public ACL / policy block at AP layer |
| Through-AP-only bucket-policy Deny | AP exists; AP ARN resolvable | **Deny with wrong condition key (`aws:SourceAp` instead of `s3:DataAccessPointArn`) silently matches nothing; bucket still bypassable** | true VPC-only / AP-only invariant |
| Access point policy | access point exists | policy references a prefix that doesn't exist → request matched, list empty (not an error) | per-team scoping |
| Object Lambda AP | supporting standard AP exists; Lambda function in same region | transform function throttles → client sees S3 AccessDenied, not Lambda error | transform-on-read |
| Multi-Region Access Point | buckets in >= 2 regions; versioning recommended | **objects written before MRAP creation are NOT routed through the MRAP hostname retroactively; reads via MRAP return only post-MRAP-create objects** | active-active or failover |
| Cross-account access point | bucket owner grants `s3:CreateAccessPoint` to foreign account in bucket policy | foreign account creates AP with permissive policy → data leak that the bucket owner's BPA at the BUCKET level does not prevent if BPA is per-AP only | delegated ownership |
| S3 on Outposts AP | Outpost equipped; S3 on Outposts bucket exists | Outposts AP ARN format differs (`arn:aws:s3-outposts`) — using the regional AP API is a silent no-op | on-prem latency |

**The four silent-failure rows are the ones a baseline model misses.**
VPC endpoint with a permissive policy, the wrong through-AP-only
condition key, Object Lambda throttling, and MRAP non-backfill all
return success / wrong-shaped errors and only post-config verification
(Step 9) catches the gap. This is why the procedure verifies every item
rather than trusting the API response.

## Expert heuristic: the VPC-only invariant myth

The most dangerous misconception: "VPC network origin = bucket is
VPC-only." It is not.

```text
Operator thinks:       What actually happens:
VPC-origin AP →        VPC-origin AP →
  bucket VPC-only        bucket reachable from VPC via AP hostname
                         bucket ALSO reachable from anywhere via
                         s3.<region>.amazonaws.com
```

The VPC-origin setting controls the **network path to the AP hostname
only**. The global bucket hostname is unaffected. To make a bucket
truly VPC-only you need: (1) a VPC-origin AP (Step 2 + Step 4), (2) a
bucket policy `Deny` keyed on `Null: { s3:DataAccessPointArn: true }`
(Step 6), and optionally (3) a VPC endpoint policy restricting to the
AP ARN (Step 3). The wrong condition key is the most common
implementation bug: `aws:SourceVpce` / `aws:SourceVpc` are for VPC-
endpoint enforcement and are NOT set on AP-routed requests. The
correct key is `s3:DataAccessPointArn`.

## Expert heuristic: MRAP cost amplification and non-backfill

A Multi-Region Access Point looks like "one hostname, write/read
nearest region." Two operational truths are routinely missed:

1. **MRAP does not backfill.** Objects written before the MRAP was
   created are NOT visible through the MRAP hostname. Operators who
   expect "MRAP = one global namespace over all my data" get a partial
   namespace with no error signal. Remedy: Batch Operations copy.

2. **MRAP cross-region pricing is real.** A GET via the MRAP hostname
   billed at the serving region's rate; cross-region routing adds data
   transfer fees. At 100 TB/month of cross-region egress this is
   multiple thousands of dollars per month with no default alarm.
   Remedy: pin clients to regions, alarm on `BytesRequested` /
   `4xxErrors` per region, prefer failover-only topologies unless
   active-active is a hard product requirement.

## Expert heuristic: Object Lambda concurrency

Object Lambda invokes the transform function synchronously on every
GET. The function's concurrency budget IS the access point's
throughput ceiling — there is no S3-side queue. At throttle, clients
see S3-shaped errors (`AccessDenied`, `SlowDown`), NOT Lambda
`ThrottledException`. Operators blame S3. Remedy: set reserved
concurrency equal to expected peak GET rate, alarm on Lambda
`Throttles` and `Errors`, and log the original GET ARN for correlation.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Bucket exists and meets baseline | AP inherits bucket-level weaknesses (no BPA, no SSE) | `aws s3api get-public-access-block`, `get-bucket-encryption` |
| Account ID | Required for AP ARN construction | `aws sts get-caller-identity --query Account --output text` |
| Region | AP is region-scoped (Internet + VPC); MRAP is global | `aws configure get region` |
| VPC ID (VPC origin only) | The VPC the AP will be reachable from | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| VPC endpoint for S3 (recommended) | Enables in-VPC routing + private DNS | `aws ec2 describe-vpc-endpoints --service-name com.amazonaws.<region>.s3` |
| Lambda function ARN (Object Lambda only) | The transform function must exist in-region | `aws lambda get-function --function-name <name>` |
| MRAP regions list (MRAP only) | >= 2 buckets in >= 2 regions required | `aws s3control list-access-points-for-object-lambda` is NOT it; use `aws s3api list-buckets` per region |
| Outpost ARN (Outposts AP only) | Outposts APs use a different ARN namespace and API | `aws s3outposts list-endpoints` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm bucket baseline

An access point does NOT remediate bucket-level weaknesses. Before
creating the AP, confirm the underlying bucket meets the production
baseline: Block Public Access (account + bucket), default encryption
(SSE-S3 or SSE-KMS with BucketKeyEnabled), and versioning if the
workload needs lifecycle non-current rules or replication. See the
s3-secure-bucket-deployer skill for the bucket baseline procedure.

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-versioning --bucket <BUCKET>
```

**Common mistake:** skipping this step because "the AP will enforce
access." The AP policy is evaluated alongside the bucket policy, not
instead of it; a permissive bucket policy nullifies AP-level tightening.

### Step 2 — Choose network origin

Pick `Internet` if the AP should be reachable from anywhere (typical
for a shared-data-lake AP used by analytics services), or `VPC` if the
AP should be reachable only from a specific VPC. The decision changes
the threat model: Internet-origin APs rely on the AP policy + BPA for
access control; VPC-origin APs add a network boundary that you SHOULD
pair with the Step 6 bucket-policy Deny for the true VPC-only invariant.

### Step 3 — VPC endpoint + private DNS (VPC origin only)

Create or confirm a VPC gateway endpoint for S3 in the target VPC, and
(optionally, for private-DNS enforcement) an interface endpoint with
private DNS enabled. The endpoint policy should restrict the bucket to
AP-ARN-only access:

```bash
# Gateway endpoint with restrictive policy
aws ec2 create-vpc-endpoint \
  --vpc-id <VPC_ID> \
  --service-name com.amazonaws.<REGION>.s3 \
  --route-table-ids <ROUTE_TABLE_ID> \
  --vpc-endpoint-type Gateway \
  --policy-document file://vpce-policy.json
```

The `vpce-policy.json` should `Allow` only `s3:*` on the access-point
ARN (not the bucket ARN), forcing all in-VPC traffic through the AP:

```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>",
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>/*"
    ]
  }]
}
```

**Common mistake:** leaving the endpoint policy as `FullAccess`. The
bucket is then reachable via the global hostname from inside the VPC,
defeating VPC-only intent. The Step 6 bucket-policy Deny is the real
enforcement; the endpoint policy is defense-in-depth.

### Step 4 — Create the access point

```bash
# Internet-origin
aws s3control create-access-point \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --bucket <BUCKET>

# VPC-origin
aws s3control create-access-point \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --bucket <BUCKET> \
  --vpc-configuration VpcId=<VPC_ID>
```

**Common mistake:** using a hyphen in `<AP_NAME>` is fine, but using
uppercase letters fails — access point names are lowercase-only within
the account and must be unique within the account-region (not within
the bucket, as operators sometimes assume).

**If it fails:** `AccessDenied` usually means the caller lacks
`s3:CreateAccessPoint`. `BucketAlreadyOwnedByYou` is a sign the AP
name is reused. `VpcId` rejection means the VPC is in a different
region from the AP — VPC-origin APs are region-bound.

### Step 5 — Attach access point policy

The AP policy is a separate document from the bucket policy. Scope it
to a principal + prefix:

```bash
aws s3control put-access-point-policy \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --policy file://ap-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "TeamAReadWritePrefix",
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::<ACCOUNT>:role/TeamARole" },
    "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
    "Resource": [
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>",
      "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>/team-a/*"
    ]
  }]
}
```

**Common mistake:** using the bucket ARN in the AP policy's `Resource`.
The resource must be the access-point ARN (`arn:aws:s3:<region>:<account>:accesspoint/<name>`),
NOT the bucket ARN — requests through the AP present the AP ARN as
resource. Operators who copy a bucket policy into the AP policy and
forget to rewrite the ARN get a policy that matches nothing.

### Step 6 — Enforce "through-AP-only" via bucket policy Deny

This is the step that makes a VPC-only claim true. Add a Deny statement
to the BUCKET policy keyed on the absence of the access-point ARN:

```bash
aws s3api put-bucket-policy --bucket <BUCKET> --policy file://bucket-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "RequireThroughAccessPoint",
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": [
      "arn:aws:s3:::<BUCKET>",
      "arn:aws:s3:::<BUCKET>/*"
    ],
    "Condition": {
      "StringNotEqualsIfExists": { "s3:DataAccessPointArn": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>" },
      "Null": { "aws:SourceVpc": "false" }
    }
  }]
}
```

The condition reads: "Deny if the request did NOT come through this
specific access point." Requests via the global hostname fail the
`s3:DataAccessPointArn` match and are denied. Requests via the AP
match and proceed (subject to the AP policy).

**Common mistake:** using `aws:SourceVpce` or `aws:SourceVpc` as the
sole condition. Those keys are NOT set on AP-routed requests in the
way operators expect; `s3:DataAccessPointArn` is the authoritative
key. Also: do NOT combine this with `StringNotEqualsIfExists` set to
a list of multiple AP ARNs unless you genuinely intend to allow all
of them — a typo silently widens access.

### Step 7 — Per-AP Block Public Access (VPC-origin only)

For VPC-origin access points, enable per-AP Block Public Access as the
innermost public-access layer:

```bash
aws s3control put-access-point-public-access-block \
  --account-id <ACCOUNT_ID> \
  --name <AP_NAME> \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**Common mistake:** assuming account-level or bucket-level BPA covers
the AP. Per-AP BPA is a separate control; account-level BPA does
propagate, but per-AP BPA gives you explicit visibility into the AP's
public-access posture, which matters for cross-account AP scenarios
where the bucket owner's BPA does not control the AP.

### Step 8 — Optional: Object Lambda / MRAP / cross-account / alias

#### 8a. Object Lambda access point

Provision a supporting standard AP first (Steps 4-6), then create the
Object Lambda AP on top of it:

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id <ACCOUNT_ID> \
  --name <OLAP_NAME> \
  --configuration \
    SupportingAccessPoint=arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<AP_NAME>,\
    TransformationConfigurations='[{Action=GetObject,ContentTransformation=AWSLambda:{FunctionArn=arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC>}}]'
```

Set reserved concurrency on the transform function before traffic
starts; see the Object Lambda heuristic above.

#### 8b. Multi-Region Access Point (MRAP)

```bash
aws s3control create-multi-region-access-point \
  --account-id <ACCOUNT_ID> \
  --details Name=<MRAP_NAME>,Regions='[{Bucket=arn:aws:s3:::<BUCKET_A>},{Bucket=arn:aws:s3:::<BUCKET_B>}]'
```

Verify with `get-multi-region-access-point` (async — poll until READY).
Remember: pre-existing objects are NOT backfilled; copy them via Batch
Operations if they need to be reachable through the MRAP.

#### 8c. Cross-account access point

The bucket owner grants the foreign account `s3:CreateAccessPoint` in
the bucket policy:

```json
{
  "Sid": "DelegateAPCreation",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<FOREIGN_ACCOUNT>:root" },
  "Action": "s3:CreateAccessPoint",
  "Resource": "arn:aws:s3:::<BUCKET>"
}
```

The foreign account then runs `create-access-point` as in Step 4. The
foreign-owned AP uses the foreign account in the ARN — verify with
`get-access-point` and ensure the bucket owner's per-AP BPA posture
is not weakened.

#### 8d. Alias

Each access point gets an auto-generated alias (`<AP_NAME>-<random>.s3-accesspoint.<region>.amazonaws.com`)
that is DNS-compatible and can be used in CNAME records. There is no
explicit create step; verify with `get-access-point --query Alias`.
For a custom alias, register a CNAME in your DNS provider pointing to
the auto-generated alias hostname.

#### 8e. S3 on Outposts access points

Outposts APs use the `s3outposts` API and a different ARN namespace:

```bash
aws s3outposts create-access-point \
  --container-arn arn:aws:s3-outposts:<REGION>:<ACCOUNT>:outpost/<OUTPOST_ID>/bucket/<BUCKET> \
  --name <AP_NAME>
```

Do NOT use the regional `s3control create-access-point` for Outposts —
it returns success but does not provision the Outposts AP.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3control get-access-point-public-access-block --account-id <ACCOUNT_ID> --name <AP_NAME>
aws s3api get-bucket-policy --bucket <BUCKET>     # confirm through-AP Deny
aws ec2 describe-vpc-endpoints --filters Name=service-name,Values=com.amazonaws.<REGION>.s3
aws s3control get-access-point-configuration-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>  # OLAP only
aws s3control get-multi-region-access-point --account-id <ACCOUNT_ID> --name <MRAP_NAME>                       # MRAP only
```

## NEVER do these things

These anti-patterns cause silent exposure, data-plane bugs, or
compliance violations. Each is observed in real production incidents —
the "why it's wrong" line is the post-mortem finding.

1. **NEVER claim "VPC-only" without the bucket-policy Deny on
   `Null: { s3:DataAccessPointArn: true }`.** Why it's wrong: the VPC
   network-origin setting controls the network path to the AP hostname
   ONLY. The bucket's global hostname stays reachable by any principal
   with `s3:GetObject`. Without the Deny, every VPC-only claim is
   false. This is the single most common S3 access-point incident.

2. **NEVER copy a bucket policy into the access-point policy without
   rewriting the `Resource` ARN to the access-point ARN.** Why it's
   wrong: requests through the AP present the AP ARN as the resource,
   not the bucket ARN. A policy whose Resource is `arn:aws:s3:::bucket`
   matches nothing when evaluated for an AP-routed request — the policy
   is dead text with no effect.

3. **NEVER assume account-level or bucket-level BPA protects a
   cross-account access point.** Why it's wrong: cross-account APs are
   owned by the foreign account; the bucket owner's per-AP BPA does
   not apply. The foreign account can attach a permissive AP policy
   and expose data the bucket owner thought was contained. Always
   pair cross-account delegation with an explicit bucket-policy
   condition on the AP ARN.

4. **NEVER configure an Object Lambda access point without reserved
   concurrency on the transform function.** Why it's wrong: Object
   Lambda invokes synchronously; the function's concurrency budget IS
   the AP's throughput ceiling. At throttle, clients see S3-shaped
   errors (`AccessDenied`, `SlowDown`) — operators blame S3. Set
   reserved concurrency + a CloudWatch alarm on Lambda `Throttles`.

5. **NEVER assume an MRAP backfills pre-existing objects.** Why it's
   wrong: MRAP routes only requests that arrive via the MRAP hostname;
   objects written before the MRAP was created are not retroactively
   available through it. The MRAP returns partial results with no
   error signal. Copy pre-existing objects via Batch Operations if
   they need to be reachable through the MRAP.

## Output format

```
ACCESS_POINT: <ap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Network origin: Internet | VPC (VPC ID: <id>)
  [✓|✗] VPC endpoint + private DNS: configured (VPC origin only)
  [✓|✗] Access point created: <AP_NAME> (alias: <alias>)
  [✓|✗] Access point policy: attached (principal: <role>, prefix: <prefix>)
  [✓|✗] Through-AP-only bucket-policy Deny: present (s3:DataAccessPointArn)
  [✓|✗] Per-AP Block Public Access: all 4 settings True (VPC origin)
  [✓|✗] Optional feature: Object Lambda | MRAP | cross-account | none
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
ACCESS_POINT: <ap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Network origin: Internet | VPC (VPC ID: <id>)
  [✓|✗] VPC endpoint + private DNS: configured (VPC origin only)
  [✓|✗] Access point created: <AP_NAME> (alias: <alias>)
  [✓|✗] Access point policy: attached (principal: <role>, prefix: <prefix>)
  [✓|✗] Through-AP-only bucket-policy Deny: present (s3:DataAccessPointArn)
  [✓|✗] Per-AP Block Public Access: all 4 settings True (VPC origin)
  [✓|✗] Optional feature: Object Lambda | MRAP | cross-account | none
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 8
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[OPTIONAL]` (not needed for this workload). Omitting a row
   implies it was not evaluated.

2. **NEVER mark Network origin as `[✓] VPC` without also marking the
   Through-AP-only bucket-policy Deny.** VPC origin without the Deny
   is a false VPC-only claim (see Expert heuristic). If the operator
   declined the Deny, Network origin MUST be `[✓]` AND the Deny row
   MUST be `[✗]` with a one-line warning, OR the verdict MUST be
   `PREREQUISITES_MISSING`.

3. **NEVER mark Access point policy as `[✓]` without confirming the
   `Resource` ARN uses the access-point ARN format.** Policies whose
   Resource is the bucket ARN match nothing for AP-routed requests;
   they are dead text. The verification MUST include
   `get-access-point-policy` and the rationale MUST cite the AP ARN.

4. **NEVER mark MRAP as `[✓]` without a one-line note that
   pre-existing objects are NOT backfilled.** This silent-failure mode
   is the #1 MRAP production incident; suppressing it from the
   checklist is non-compliant.

5. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] VPC endpoint not found — create gateway endpoint for
   com.amazonaws.<region>.s3 in VPC <id>`. A bare `[✗]` with no
   explanation is non-compliant.

6. **NEVER mark the Through-AP-only Deny as `[✓]` without confirming
   the condition key is `s3:DataAccessPointArn`.** Using
   `aws:SourceVpce` or `aws:SourceVpc` instead produces a Deny that
   matches the wrong thing; the bucket is still bypassable.

### Perfect example output — READY_TO_DEPLOY

```text
ACCESS_POINT: team-a-vpc-ap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket baseline: prod-shared-data, BPA all 4 True, SSE-KMS, versioning Enabled
  [✓] Network origin: VPC (VPC ID: vpc-0abc123, endpoint: vpce-0def456)
  [✓] VPC endpoint + private DNS: gateway endpoint with AP-scoped policy
  [✓] Access point created: team-a-vpc-ap (alias: team-a-vpc-ap-12ab34cd.s3-accesspoint.us-east-1.amazonaws.com)
  [✓] Access point policy: principal arn:aws:iam::111111111111:role/TeamAReadRole, prefix team-a/
  [✓] Through-AP-only bucket-policy Deny: present (Null: s3:DataAccessPointArn)
  [✓] Per-AP Block Public Access: all 4 settings True
  [OPTIONAL] Object Lambda / MRAP / cross-account: none
VERIFICATION_COMMANDS:
  aws s3control get-access-point --account-id 111111111111 --name team-a-vpc-ap
  aws s3control get-access-point-policy --account-id 111111111111 --name team-a-vpc-ap
  aws s3control get-access-point-public-access-block --account-id 111111111111 --name team-a-vpc-ap
  aws s3api get-bucket-policy --bucket prod-shared-data
  aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-0abc123
```

### Perfect example output — PREREQUISITES_MISSING

```text
ACCESS_POINT: team-a-vpc-ap
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Bucket baseline: prod-shared-data, BPA all 4 True, SSE-S3
  [✓] Network origin: VPC (VPC ID: vpc-0abc123)
  [✗] VPC endpoint: no gateway endpoint for com.amazonaws.us-east-1.s3 in VPC vpc-0abc123 — create endpoint with AP-scoped policy first
  [✓] Access point created: team-a-vpc-ap (alias: team-a-vpc-ap-12ab34cd.s3-accesspoint.us-east-1.amazonaws.com)
  [✓] Access point policy: attached, principal TeamAReadRole, prefix team-a/
  [✗] Through-AP-only bucket-policy Deny: NOT present — bucket still bypassable via global hostname
  [✓] Per-AP Block Public Access: all 4 settings True
  [OPTIONAL] Object Lambda / MRAP / cross-account: none
VERIFICATION_COMMANDS:
  aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=vpc-0abc123
  aws s3api get-bucket-policy --bucket prod-shared-data
```

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] If Network origin is VPC, Through-AP-only Deny is also `[✓]` (or verdict is PREREQUISITES_MISSING)?
- [ ] AP policy `Resource` uses the access-point ARN format?
- [ ] MRAP row, if `[✓]`, includes the non-backfill warning?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **S3 Access Points for S3 on Outposts**: separate `s3outposts` API
  and ARN namespace (`arn:aws:s3-outposts`). Regional `s3control`
  calls return success but do NOT provision the Outposts AP — verify
  with `s3outposts list-access-points`.
- **Multi-Region Access Points with failover controls**: active-passive
  failover via top-level `PublicDnsName` and route-control; objects
  written before MRAP creation still NOT backfilled.
- **Per-access-point Block Public Access**: separate `PutAccessPointPublicAccessBlock`
  API; distinct from bucket-level and account-level BPA.
- **Object Lambda runtime deprecation signals**: AWS guidance is to
  prefer S3 Batch Operations for transformation at write time when
  feasible; Object Lambda remains supported for transform-on-read.
- **Access Point alias auto-generation**: every AP gets a DNS-
  compatible alias; no manual registration needed for standard use.
- **Cross-account Access Point delegation**: bucket owner grants
  `s3:CreateAccessPoint` in the bucket policy; the foreign-owned AP
  is subject to the foreign account's policies, NOT the bucket
  owner's per-AP BPA — the bucket owner MUST add a bucket-policy
  condition on the AP ARN for containment.
