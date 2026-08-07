---
name: iam-permission-troubleshooter
description: >-
  Diagnoses AWS IAM AccessDenied, ExplicitDeny, Client.UnauthorizedOperation,
  and NotAuthorized sts:AssumeRole errors via a systematic policy-evaluation
  decision tree — Organisation SCP, resource-based, identity-based, permissions
  boundary, and session policy layers — and pinpoints the specific policy
  statement that denied the request. Emits a deterministic verdict
  (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the failing evaluation
  path and the exact policy edit. Use when an AWS API call returns
  AccessDenied, when sts:AssumeRole fails, when a Lambda/EC2/ECS task cannot
  reach a cross-account resource, when a new SCP or permissions boundary
  silently breaks a workload, or when iam simulate-principal-policy returns
  an unexpected implicit deny.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works on supplied policy JSON. Live-account
  diagnosis uses aws iam simulate-principal-policy, aws iam
  list-attached-role-policies / list-role-policies, aws organizations
  describe-policy, aws cloudtrail lookup-events, aws sts get-caller-identity
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - IAM
  - AccessDenied
  - ExplicitDeny
  - Client.UnauthorizedOperation
  - NotAuthorized
  - sts:AssumeRole
  - trust policy
  - SCP
  - permissions boundary
  - session policy
  - policy evaluation
  - cross-account
  - KMS key policy
  - PassRole
  - simulate-principal-policy
  - CloudTrail
  - implicit deny
tags: [iam, security, troubleshoot, access-denied, policy-evaluation, scp, permissions-boundary]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: troubleshoot
  skill_class: capability
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing an AWS AccessDenied / ExplicitDeny / Client.UnauthorizedOperation
    error, debugging sts:AssumeRole failures, investigating why a Lambda or
    ECS task cannot reach a cross-account resource, validating SCP or
    permissions-boundary impact after a recent change, or interpreting an
    unexpected implicit deny from iam simulate-principal-policy.
  activation_triggers:
    - "AccessDenied on"
    - "why am I getting AccessDenied"
    - "sts:AssumeRole failed"
    - "NotAuthorized to perform"
    - "Client.UnauthorizedOperation"
    - "Lambda cannot access cross-account"
    - "ECS task AccessDenied"
    - "implicit deny on simulate-principal-policy"
    - "SCP blocked the call"
    - "permissions boundary blocking"
  invocation_schema: >-
    Input: either (a) a symptom description (the error string, the failing API
    call, the principal ARN) plus any policy documents already gathered, OR
    (b) a live-account scenario where the agent must run diagnostic CLI
    commands to gather context. Output: a deterministic INCIDENT / VERDICT /
    ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND,
    NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific policy layer
    and statement that produced the deny.
---

# IAM Permission Troubleshooter

## Activation

Activate this skill when the user reports an AWS permission error or asks why
a principal cannot perform an action. Trigger phrases: "AccessDenied",
"why am I getting AccessDenied", "sts:AssumeRole failed", "NotAuthorized to
perform", "Client.UnauthorizedOperation", "Lambda cannot access cross-account",
"ECS task AccessDenied", "implicit deny on simulate-principal-policy", "SCP
blocked the call", "permissions boundary blocking".

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Error-type → evaluation-path map (AccessDenied, ExplicitDeny, etc.) | Identify which error type you're dealing with |
| **§ Process** | Six-layer diagnostic decision tree (SCP → resource → identity → boundary → session → VPCe) | Walk this in order for every diagnosis |
| **§ Output format** | ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE template | Format the response |
| **§ Diagnostic commands** | Exact CLI commands for each diagnostic step | When you need to gather evidence |
| **§ Expert edge cases** | Non-obvious gotchas (KMS cross-account, PassRole, service-linked roles) | When the standard tree doesn't find the cause |
| **§ Anti-Patterns** | NEVER list — common misdiagnoses and shortcuts that miss the real cause | Review before concluding |
| **§ Remediation** | Step-by-step fix procedures for each root cause | After root cause is identified |

## Mindset

**One-line takeaway:** an AWS permission decision is the intersection of up to
six independent policy layers evaluated in a fixed order. AccessDenied is
symptom, not cause — the cause is the specific layer and statement that
produced the deny. Treat the symptom as the entry point to a deterministic
walk, not as the answer.

Three facts make IAM troubleshooting different from generic "check your
policy":

- **Explicit Deny wins everywhere, in every layer.** A Deny statement in any
  of the six layers (Organisation SCP, resource-based, identity-based,
  permissions boundary, session policy, service control) is final. Adding
  more Allow statements does not help — operators often "fix" AccessDenied
  by widening identity-based policy, which has zero effect because the real
  deny lives in an SCP they did not check.
- **Same-account vs cross-account evaluation differs structurally.**
  Same-account access needs EITHER identity-based OR resource-based Allow
  (union). Cross-account needs BOTH (intersection). The same S3 bucket
  policy that grants access to a same-account Lambda will not grant access
  to a cross-account Lambda unless the caller's identity-based policy also
  Allows the action. Misdiagnosing same-account as cross-account is the
  most common evaluation error.
- **`AccessDenied` does not distinguish implicit from explicit deny.**
  AWS returns the same string whether no Allow matched (implicit) or a Deny
  statement matched (explicit). Only `CloudTrail`'s `errorCode` /
  `errorMessage` field, `iam simulate-principal-policy`'s
  `matchedStatements`, or careful policy reading can distinguish them. The
  decision tree below forces the operator to identify which kind of deny
  before recommending a fix.

## Quick reference — error-type to evaluation-path map

| Error string | Likely layer | First probe |
|---|---|---|
| `AccessDenied` (no other context) | Identity-based implicit OR any layer Deny | CloudTrail `errorMessage`; `simulate-principal-policy` |
| `Client.UnauthorizedOperation` | EC2 service-level — almost always identity-based implicit | `ec2:Describe*` actions rarely need resource ARNs; check identity policy for missing action |
| `NotAuthorized to perform sts:AssumeRole` | Trust policy on the target role (resource-based) | Read target role's `assumeRolePolicyDocument` for the caller principal |
| `AccessDenied` on `kms:Decrypt` during S3 GetObject | KMS key policy (resource-based) | Read key policy for the caller's role ARN |
| `AccessDenied` after recent SCP deployment | Organisation SCP (Deny or absent Allow in SCP) | `aws organizations list-policies-for-target` |
| `AccessDenied` only when assuming via console | Session policy injected by console federation | Check `assumeRoleInput` session policy / SAML claim |
| `User: arn:... is not authorized to perform: lambda:GetFunction` (cross-account) | Caller identity-based OR target resource-based | Both must Allow; check both |
| `because no identity-based policy allows the ... action` | Identity-based implicit (AWS added explicit text in 2023+) | Identity policy missing the action |

## Process — Diagnostic decision tree (apply in order, do NOT skip steps)

### Step 0: Validate the symptom and surface the explicit deny signal

Before any policy reading, capture the precise error string and the
CloudTrail event. A correct diagnosis requires knowing whether the deny is
explicit or implicit — and the only authoritative sources are CloudTrail
and the policy simulator.

If the input lacks BOTH the CloudTrail event AND a policy simulator result,
output:

```text
INCIDENT: <principal> → <action> on <resource>
VERDICT: NEED_MORE_INFO
REASON: Cannot distinguish implicit from explicit deny from the supplied
context. The decision tree branches on which kind of deny is in play.
MISSING:
  - CloudTrail event for the denied API call (lookup-events), OR
  - iam simulate-principal-policy output with --detail-evaluation
```

If a CloudTrail event is available, parse these fields:

- `errorMessage` — AWS sometimes appends the exact reason (e.g., "with an
  explicit deny in an SCP").
- `errorCode` — `Client.UnauthorizedOperation` for EC2; `AccessDenied` for
  most other services.
- `userIdentity.sessionContext` — reveals whether the call was made under
  an assumed role, federated principal, or root. Session policies and SAML
  attribute mappings live here.
- `sourceIPAddress` — required to evaluate `aws:SourceIp` conditions.
- `requestParameters` — required to evaluate condition keys like
  `aws:RequestedRegion`, `aws:SourceVpce`, `aws:SourceArn`.

### Step 1: Identify the error type (drives the rest of the tree)

Map the error to a category. Each category has a different first probe —
choosing the wrong category wastes 90% of the diagnostic time.

| Category | Signature | First probe |
|---|---|---|
| **A. Implicit AccessDenied** | `AccessDenied` and CloudTrail shows no explicit-deny text, OR `simulate-principal-policy` returns `implicitDeny` | Step 3 — full evaluation walk |
| **B. Explicit AccessDenied** | CloudTrail `errorMessage` mentions "explicit deny", OR simulator returns `explicitDeny` | Step 4 — Deny-statement hunt |
| **C. EC2 Client.UnauthorizedOperation** | `Client.UnauthorizedOperation` | Step 5 — EC2-specific path |
| **D. sts:AssumeRole NotAuthorized** | `NotAuthorized to perform sts:AssumeRole` OR `The role ... cannot be assumed` | Step 6 — trust policy path |
| **E. Cross-account resource access** | Caller principal ARN account ≠ resource ARN account | Step 7 — cross-account intersection |

**If the symptom matches more than one category**, pick the most specific
(EC2-specific > AssumeRole-specific > cross-account > explicit > implicit).
The most specific probe usually answers in one step; the generic probe
walks every layer.

### Step 2: Gather context (mandatory before any policy reading)

Without these four values, the evaluation walk cannot terminate. State each
in the output `INCIDENT` line.

| Field | Why required | Source |
|---|---|---|
| **Principal ARN** | Identity-based policy, trust policy, and `aws:PrincipalArn` condition keys all evaluate against this | `aws sts get-caller-identity` (if you have credentials), or CloudTrail `userIdentity.arn` |
| **Action (exact)** | Policy `Action` patterns must match the service-prefixed name (e.g., `s3:GetObject`, not "get object") | The error message includes the action verbatim if AWS produced it |
| **Resource ARN** | Resource-based policy and condition keys (`aws:ResourceAccount`, `aws:ResourceTag`) depend on the exact ARN including path | The error message includes the resource if the service supports resource-level; otherwise `Resource: "*"` |
| **Request context** | Region, source IP, source VPCE, source VPC, federation attributes — every condition key depends on this | CloudTrail `requestParameters` and `sourceIPAddress` |

**ARN format gotcha (Step 4 root cause #1).** The single most common IAM
misdiagnosis is "the policy has `s3:GetObject` on the bucket ARN." For S3:

- Bucket-level actions (`s3:ListBucket`, `s3:DeleteBucket`, `s3:GetBucketLocation`) require `arn:aws:s3:::bucket-name` (no `/*`).
- Object-level actions (`s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`) require `arn:aws:s3:::bucket-name/*` (with `/*`).

Confusing the two produces AccessDenied on a policy that "looks right." A
similar pattern exists for SQS (`arn:aws:sqs:...:queue-name` vs queue URL),
and for Secrets Manager (`arn:aws:secretsmanager:...:secret:name-??????`
with the random 6-char suffix).

If the operator cannot supply the exact action or resource ARN, do not
guess — emit `NEED_MORE_INFO` listing the missing field.

### Step 3: Policy evaluation walkthrough — same-account, implicit deny

AWS evaluates policies in a fixed order. The first layer to deny wins. The
first layer to allow is NOT necessarily final — every layer above an allow
must also permit the request. Walk these in order:

```
1. Organisation SCPs (root → OU → account)
        │ if a Deny matches → DENY (Step 4)
        │ if no SCP Allows the action → DENY (implicit, account-level)
        ▼
2. Resource-based policy (same-account: union with identity-based)
        │ for SAME-ACCOUNT: if resource-based Allows → proceed (with #3)
        │ for CROSS-ACCOUNT: BOTH #2 AND #3 must Allow (Step 7)
        ▼
3. Identity-based policy (managed + inline on the principal)
        │ if no Allow matches → DENY (implicit)
        │ if Allow matches → proceed
        ▼
4. Permissions boundary (if attached)
        │ if boundary does not Allow → DENY (implicit)
        ▼
5. Session policy (if assumed role with session policy)
        │ effective permissions = role policy ∩ session policy
        │ if session policy does not Allow → DENY (implicit)
        ▼
6. Service-linked role / service control specifics
        │ some services (e.g., AWS CloudFormation) make second-order
        │ calls under a service-linked role — caller's policy is not enough
        ▼ ALLOW
```

**Critical rule for SCPs:** SCPs do NOT grant access — they only set the
maximum allowed scope. An SCP that contains only `Allow` statements is a
no-op. An SCP that contains a `Deny` statement (e.g.,
`aws:RequestedRegion != us-east-1`) restricts the entire account below
the OU. A common footgun: the SCP lives at the root or an OU above the
account, and the operator never thinks to check above the account.

If the walk reaches the bottom with at least one Allow at each required
layer and no Deny anywhere → the request should succeed. If it still
fails, re-check Step 0 — the error is likely a service-level issue (e.g.,
the resource does not exist, the API parameters are wrong) being reported
as AccessDenied.

### Step 4: Deny-statement hunt (for explicit-deny cases)

When CloudTrail or the simulator confirms an explicit deny, walk every
layer in the same order as Step 3 but look for `Effect: Deny` statements
whose `Action`, `Resource`, and `Condition` all match the request. The
first match is the cause. Output its layer, policy name, statement Sid,
and the matched condition keys.

**Common Deny patterns to look for first:**

- **Region restriction SCP.** `Condition: { "StringNotEquals": { "aws:RequestedRegion": ["us-east-1", "us-west-2"] } }` — denies anything outside the listed regions. Often deployed org-wide and forgotten when a workload moves regions.
- **IP restriction in identity policy or boundary.** `Condition: { "NotIpAddress": { "aws:SourceIp": ["10.0.0.0/8"] } }` — denies anything outside the corporate CIDR. Breaks when a Lambda runs from a VPC with a NAT gateway whose EIP is not on the allowlist.
- **VPC endpoint restriction.** `Condition: { "StringNotEqualsIfExists": { "aws:sourceVpce": "vpce-aaaaaaa" } }` — denies anything not coming through the specified VPC endpoint. Breaks cross-region or cross-account traffic.
- **MFA requirement.** `Condition: { "Bool": { "aws:MultiFactorAuthPresent": "false" } }` — programmatic calls without MFA fail. Note that long-lived access keys never set the MFA key, so `Bool` evaluates false; the correct pattern is `Null` + `Bool` together.
- **Resource tag requirement.** `Condition: { "StringNotEquals": { "aws:ResourceTag/Environment": "prod" } }` — denies access to resources without the tag. Breaks when a new resource is created without tags.
- **`aws:SourceArn` / `aws:SourceAccount` on a service-to-service chain.** A KMS key policy that requires `aws:SourceAccount: "111111111111"` denies a cross-account S3 access because the KMS call is made by S3 on behalf of the caller — the `aws:SourceAccount` is the S3 service account, not the caller's.

**NotAction in a Deny is the easiest to miss.** A Deny statement with
`NotAction: ["iam:*"]` denies every action except `iam:*`. Operators read
"iam:*" and think the statement is about IAM; it is actually denying
everything else. Scan all Deny statements for `NotAction` / `NotResource`
first — they are the broadest denies.

### Step 5: EC2-specific path (Client.UnauthorizedOperation)

EC2 returns `Client.UnauthorizedOperation` instead of `AccessDenied`. The
meaning is identical but operators often misread it as a service-level
issue. Run this probe list in order:

1. **Identity-based policy missing the action.** Most EC2 actions require
   the explicit action (`ec2:RunInstances`, `ec2:DescribeInstances`).
   `ec2:Describe*` historically supported `Resource: "*"`; some newer
   Describe actions now support resource-level permissions and may be
   scoped down.
2. **Resource-level permission missing on a specific ARN.** `ec2:RunInstances`
   requires permission on the AMI, instance profile, subnet, security
   group, and EBS volume. A common failure: identity policy allows
   `ec2:RunInstances` on `"*"` but the SCP restricts `ec2:RunInstances`
   to specific subnets — running in any other subnet fails.
3. **`iam:PassRole` missing for the instance profile.** Launching an EC2
   instance with an instance profile requires `iam:PassRole` on the
   profile's role ARN. The error reports as `Client.UnauthorizedOperation`
   with no hint that PassRole is the missing permission.
4. **EBS-encrypted volume with no KMS key policy.** If the account default
   EBS encryption is on and uses a customer-managed KMS key, the caller
   needs `kms:CreateGrant` on the key. The error reports at instance
   launch but the cause is in KMS.

For each EC2 failure, run
`aws ec2 describe-...` with `--dry-run` to surface the exact missing
permission, or `aws iam simulate-principal-policy` with the EC2 action
list.

### Step 6: Trust policy path (sts:AssumeRole NotAuthorized)

`NotAuthorized to perform sts:AssumeRole` is almost always a resource-based
issue on the TARGET role — the trust policy (`assumeRolePolicyDocument`)
does not include the caller. Read the target role's trust policy first.

| Symptom variant | Trust policy defect |
|---|---|
| `User is not authorized to perform sts:AssumeRole on resource arn:aws:iam::ACCOUNT:role/NAME` | Trust policy does not list the caller in `Principal` |
| `The role ... cannot be assumed by externalId` | Trust policy requires `sts:ExternalId` and the caller passed the wrong value (confused-deputy protection) |
| AssumeRole works in CLI but not from a service | Trust policy lists the service principal (`lambda.amazonaws.com`) but the call comes from a service-linked role, not the bare service principal. Add the service-linked role ARN. |
| AssumeRole fails only when MFA is required | Trust policy has `Condition: Bool: aws:MultiFactorAuthPresent: true` but caller did not pass MFA. Note: long-lived keys never set the MFA key. |
| Session policy rejected | The caller passed a session policy that exceeds the role's effective permissions. The session policy can only NARROW, never widen. |
| Cross-org AssumeRole fails after org change | The trust policy used `aws:PrincipalOrgID` and the caller's account left the org. Update the condition or the org membership. |

**Cross-account AssumeRole is the highest-leverage diagnostic.** The
caller's identity-based policy must Allow `sts:AssumeRole` on the target
ARN, AND the target role's trust policy must include the caller. Both
must be true. If only one is true, the call fails. Check both
explicitly — never assume the caller's side is fine.

### Step 7: Cross-account resource access path

For cross-account calls (caller account ≠ resource account), BOTH the
caller's identity-based policy AND the resource's resource-based policy
must Allow the action. This is the intersection rule and is non-negotiable.

```
Same-account:   identity-based  ∪  resource-based  (either Allows = grant)
Cross-account:  identity-based  ∩  resource-based  (both must Allow)
```

Common cross-account failures:

1. **S3 bucket policy missing the cross-account principal.** A Lambda in
   account B reading an object in account A's bucket needs the bucket
   policy in A to list B's role ARN in `Principal`. Adding the IAM
   permission to B's Lambda role is necessary but not sufficient.
2. **KMS key policy does not grant decrypt to the cross-account caller.**
   Even if the S3 bucket policy allows B to read the object, if the
   object is encrypted with a KMS key in account A, the key policy must
   also grant `kms:Decrypt` to B's role. This is a three-party chain
   (Lambda role → S3 → KMS) that fails at KMS even though S3 works.
3. **SQS queue policy does not grant `sqs:SendMessage` cross-account.**
   Same pattern as S3.
4. **Secrets Manager secret policy missing the cross-account principal.**
   Same pattern; additionally, the KMS key used to encrypt the secret
   must also grant decrypt to the caller.
5. **Cross-account Lambda invocation.** `lambda:InvokeFunction`
   resource-based policy on the function must list the cross-account
   caller. The caller's identity policy must also Allow `lambda:InvokeFunction`.

For any cross-account failure, output both sides in the EVIDENCE block:
"Caller identity policy: <Allowed / Denied / Missing action>. Target
resource-based policy: <Allowed / Denied / Missing principal>."

### Step 8: Map to the common root-cause catalog

After the walk identifies the failing layer, cross-reference with the
catalog below. These are the eight root causes that account for ~90% of
AccessDenied incidents in production:

| # | Root cause | Signature | Fix pattern |
|---|---|---|---|
| 1 | Wrong ARN format (bucket vs object, secret without 6-char suffix) | Policy "looks right" but action never matches | Add the second ARN shape (S3 dual-ARN), use `describe-` to copy exact ARN |
| 2 | Missing `Resource: "*"` for list/describe actions that only support account-level resources | `s3:ListAllMyBuckets`, `iam:ListRoles`, `ec2:Describe*` fail on scoped ARNs | Add a separate statement with `Resource: "*"` for those actions only |
| 3 | Region restriction in SCP or boundary | New region deployment fails; same call works in another region | Add the region to the SCP allowlist OR add the workload's region explicitly |
| 4 | IP restriction (`aws:SourceIp`) mismatching the egress CIDR | Lambda in VPC fails; same role works from corporate network | Add the NAT gateway EIP CIDR, OR use `aws:SourceVpce` instead |
| 5 | Service-linked role missing | Service-specific: e.g., `AWSServiceRoleForSupport` missing → no Trusted Advisor | `aws iam create-service-linked-role --aws-service-name <service>` |
| 6 | `iam:PassRole` missing for resource creation | Lambda creation fails when assigning an execution role; EC2 launch fails with instance profile | Add `iam:PassRole` on the specific role ARN the workload needs |
| 7 | KMS key policy does not grant decrypt to the calling role | S3 GetObject on encrypted object fails with AccessDenied but ListObject works | Add a statement in the key policy granting `kms:Decrypt` to the caller's role ARN |
| 8 | STS trust policy missing the caller principal | AssumeRole fails with NotAuthorized | Add the caller ARN to the trust policy `Principal` list |

When the walk reaches a fix that matches the catalog, name the catalog
number in the output — this lets the operator verify the fix against a
known pattern instead of re-deriving it.

### Step 9: Verify with the policy simulator

After proposing a fix, validate it with `aws iam simulate-principal-policy`
BEFORE applying. This catches second-order effects (e.g., the new
statement is shadowed by a Deny the operator forgot).

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/app-role \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::app-data-prod/file.txt \
  --eval-decision SHAPE \
  --output json \
  --profile <profile>
```

A return of `allowed` means the simulator confirms the principal can
perform the action. `explicitDeny` means a Deny statement still matches.
`implicitDeny` means no Allow matches. Add `--markers` or
`--detail-evaluation` to surface the matched statement.

**Simulator caveat.** The simulator tests individual actions in isolation.
It does NOT catch chained API flows (e.g., a Lambda function calling S3
under the function's role — the simulator tests `lambda:InvokeFunction`
and `s3:GetObject` separately but cannot detect that the Lambda runtime
needs the second permission on the function's role, not the caller's).
Always cross-reference simulator results with CloudTrail for chained flows.

### Step 10: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a single policy layer and
  statement (or a specific missing permission like PassRole) as the
  cause, and the fix is a known pattern from the catalog or a specific
  statement edit. Output REMEDIATION with the exact policy edit.
- **NEED_MORE_INFO.** The walk reached a layer the operator cannot supply
  (e.g., "the SCP is in the parent account and I have no access"). Output
  the list of missing inputs.
- **ESCALATE.** The walk identifies a layer that requires action outside
  the operator's scope: an SCP owned by a central security team, a KMS
  key owned by another team, a cross-account role whose trust policy is
  in another account. Output the escalation target and the specific
  request to make.

## Output format

```text
INCIDENT: <principal ARN> → <action> on <resource ARN>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <layer name> — <statement Sid or "missing permission"> —
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

### Worked example — KMS-decrypt AccessDenied on encrypted S3 object

```text
INCIDENT: arn:aws:sts::111111111111:assumed-role/app-lambda/app-instance →
s3:GetObject on arn:aws:s3:::prod-data/report.csv
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: KMS key policy (resource-based on
arn:aws:kms:us-east-1:222222222222:key/abc123) — implicit deny — caller
role not granted kms:Decrypt
EVIDENCE:
  - Identity-based policy: Allowed — s3:GetObject on bucket/* (verified)
  - S3 bucket policy: Allowed — Principal includes the Lambda role ARN
  - KMS key policy: NOT Allowed — key policy lists account 222222222222
    roles only, no cross-account grant
ROOT_CAUSE_CATALOG: #7 (KMS key policy not granting decrypt to the
calling role)
REMEDIATION:
  1. Add to the KMS key policy (in account 222222222222):
     {
       "Sid": "AllowDecryptCrossAccount",
       "Effect": "Allow",
       "Principal": { "AWS": "arn:aws:iam::111111111111:role/app-lambda" },
       "Action": "kms:Decrypt",
       "Resource": "*"
     }
  2. Verify the Lambda's identity-based policy ALSO has kms:Decrypt on
     the key ARN (cross-account intersection rule — both sides needed).
  3. Validate with:
     aws kms simulate-principal-policy --policy-source-arn
       arn:aws:iam::111111111111:role/app-lambda --action-names kms:Decrypt
       --resource-arns arn:aws:kms:us-east-1:222222222222:key/abc123
  4. Monitor CloudTrail for Decrypt events in account 222222222222.
```

## Diagnostic command reference

Run these in order. Each command's output narrows the decision tree.

```bash
# 1. Confirm the caller identity. The ARN reveals assumed-role vs user
#    vs federated. Federation paths carry session policies.
aws sts get-caller-identity --profile <profile>

# 2. Pull the CloudTrail event. errorMessage disambiguates implicit vs
#    explicit deny. sourceIPAddress and requestParameters give the
#    condition-key context.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --profile <profile>

# 3. List every policy attached to the principal. Include inline.
aws iam list-attached-role-policies --role-name <role> --profile <profile>
aws iam list-role-policies --role-name <role> --profile <profile>
aws iam get-role-policy --role-name <role> --policy-name <inline> --profile <profile>
aws iam get-policy-version \
  --policy-arn arn:aws:iam::111111111111:policy/<managed> \
  --version-id v1 --profile <profile>

# 4. For assumed-role failures, read the target role's trust policy.
aws iam get-role --role-name <target-role> --query 'Role.AssumeRolePolicyDocument' --profile <profile>

# 5. For SCP-blocked calls, list the policies attached at every level
#    above the account (root, parent OUs, account itself).
aws organizations list-policies-for-target \
  --target-id <account-id> --filter SERVICE_CONTROL_POLICY --profile <profile>
aws organizations describe-policy --policy-id <policy-id> --profile <profile>

# 6. For permissions boundary, check the boundary ARN on the role.
aws iam get-role --role-name <role> --query 'Role.PermissionsBoundary' --profile <profile>

# 7. Simulate the principal against the exact action and resource.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/<role> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::bucket/key \
  --eval-decision SHAPE \
  --output json --profile <profile>

# 8. For KMS-encrypted resources, read the key policy. The key policy
#    is the authoritative source — IAM grants on the caller do not
#    help if the key policy does not include them.
aws kms get-key-policy --key-id <key-id> --policy-name default --profile <profile>

# 9. For S3 access specifically, use the S3 access analyzer to surface
#    the bucket ACL and policy combined view.
aws accessanalyzer validate-policy-resource \
  --policy-arn arn:aws:s3:::bucket --profile <profile>
```

## Expert edge cases

These patterns represent genuine, non-obvious IAM AccessDenied causes
that a senior security engineer would catch but a generalist would miss.

### The `aws:SourceAccount` chain on service-to-service calls

When S3 reads an object encrypted with a KMS key, the KMS `Decrypt` call
is made BY S3 on behalf of the calling principal — not by the principal
directly. A KMS key policy that requires `aws:SourceAccount: "111111111111"`
expects the source account of the S3 service call to be `111111111111`,
but if the bucket is in `222222222222`, the S3 service call originates
from `222222222222`, not the caller's account. The key policy denies
the call even though the principal appears in the policy. Fix: scope on
`aws:SourceArn` of the bucket instead, OR list the bucket's account in
`aws:SourceAccount`.

### The VPC endpoint policy shadow

A VPC endpoint has its own policy that is independent of IAM. If a VPC
endpoint policy denies an action, the request fails even though every
IAM policy allows it. The CloudTrail event will show AccessDenied with
no hint that the VPC endpoint policy is the cause. The diagnostic is to
bypass the endpoint (route over the internet or a different endpoint)
and see if the call succeeds. VPC endpoint policies are the most
overlooked layer because they live in the VPC console, not IAM.

### Session policies injected by federation

When a user federates via IAM Identity Center or a SAML provider, the
federation flow can inject a session policy that narrows the role's
effective permissions. The session policy is NOT visible in the role's
policy list — it lives in the `assumeRole` request parameters. A common
failure: a SAML claim maps to a session policy that includes a
`Resource: "arn:aws:s3:::personal-${aws:username}/*"` restriction, and
the username has special characters that cause the substitution to fail
silently. The CloudTrail `userIdentity.sessionContext.sessionIssuer`
field reveals the session policy presence.

### The CloudFormation service-linked role pass-through

When CloudFormation creates a stack, it makes calls under its own
service-linked role (`AWSServiceRoleForCloudFormation`) for some
operations and under the passed role for others. A caller with
`cloudformation:CreateStack` but without `iam:PassRole` on the stack's
execution role gets `AccessDenied` on CreateStack even though the policy
allows CreateStack — CloudFormation needs PassRole to receive the
execution role. The error message rarely mentions PassRole. The fix is
to add `iam:PassRole` on the specific execution role ARN with
`iam:PassedToService: cloudformation.amazonaws.com`.

### Condition-key mismatch on `aws:ResourceTag`

Tag-based conditions are case-sensitive. A policy conditioned on
`aws:ResourceTag/Environment: prod` does NOT match a tag `environment:
prod` (lowercase key). AWS normalises tag VALUES to lowercase for some
services but not tag KEYS. The diagnostic is to read the actual tag key
case from `aws <service> describe-tags` output, not from the policy.

### The `StringLike` wildcard anchor trap

A trust policy with
`"StringLike": { "sts:RoleName": "dev-*" }` matches `dev-app` AND
`development-app` AND `devops-app`. Operators intend "starts with dev-"
but the wildcard matches anywhere. The fix is to anchor explicitly:
`dev-*` is correct only if the role names always start with `dev-`. For
service-role patterns, prefer `StringEquals` on a full role-name list
over `StringLike` patterns.

### Resource-based policy principal format

For Lambda function policies, the `Principal` MUST be a service principal
(`lambda.amazonaws.com`), an account root (`111111111111`), or an IAM
ARN. SAML/OIDC federation principals are NOT supported in Lambda function
policies — they must assume an IAM role first. A common failure is to
try granting a SAML principal direct access to a Lambda function via the
function policy.

### IAM database authentication quasi-policy

RDS IAM authentication uses a special quasi-policy mechanism. The caller
needs `connect:DB` on the DB cluster ARN — NOT `rds-db:connect`. The
action prefix changed in 2018 but old documentation still references
`rds-db:connect`. The error is AccessDenied on a policy that has the
wrong action name.

## Anti-Patterns — NEVER

- NEVER recommend adding `Action: "*", Resource: "*"` to "fix" an
  AccessDenied. This is the most common operator reflex and the most
  damaging. The correct fix is to identify the specific missing action
  and resource ARN. Wildcard remediation reopens the attack surface the
  policy was designed to close.

- NEVER assume `AccessDenied` means the identity-based policy is wrong.
  The deny could be in any of the six layers. Identity-based is the most
  visible but not the most common cause for cross-account or SCP-bound
  accounts.

- NEVER read only the identity-based policy when the symptom is
  cross-account. Cross-account requires BOTH identity and resource-based
  Allow. Reading only one side misses half the possible causes.

- NEVER assume the simulator result matches production. The simulator
  tests individual actions in isolation; chained API flows (Lambda → S3
  → KMS) are not modeled. Always validate simulator output against the
  actual CloudTrail event.

- NEVER trust the CloudTrail `errorMessage` to mention the explicit
  deny. AWS added the "explicit deny" suffix in 2023 but it is not
  present for every service or every layer. SCP denies are often
  reported as plain `AccessDenied`. Use `simulate-principal-policy` to
  disambiguate.

- NEVER recommend removing an SCP, permissions boundary, or Deny
  statement as a fix. These are security controls. The fix is to scope
  the control to include the workload's required scope, not to remove
  the control.

- NEVER assume `aws:SourceIp` matches the operator's workstation IP for
  Lambda or ECS workloads. Lambda functions in a VPC egress through a
  NAT gateway whose EIP is the source IP from AWS's perspective. ECS
  tasks in Fargate egress through a NAT gateway or VPC endpoint. The
  IP-restriction fix is to use `aws:SourceVpce` or `aws:SourceVpc`,
  not to widen the CIDR.

- NEVER recommend `iam:PassRole` on `"*"` as a fix for any
  resource-creation AccessDenied. `iam:PassRole` on `"*"` is a
  privilege-escalation vector — scope to the specific role ARN the
  workload needs and add `iam:PassedToService` condition.

- NEVER assume the operator can see the SCP. SCPs live in the
  Organizations management account (or a delegated administrator for
  AWS Organizations). Application teams rarely have read access. Output
  ESCALATE for SCP issues with the specific request to make to the
  central security team.

- NEVER conflate same-account and cross-account evaluation. The
  intersection vs union rule is non-negotiable. A same-account Lambda
  reading a same-account S3 bucket needs EITHER identity OR resource
  policy. A cross-account Lambda needs BOTH.

- NEVER overlook the VPC endpoint policy layer. It is independent of
  IAM and can deny requests that all IAM policies allow. Bypass the
  endpoint to test.

- NEVER trust role names as evidence of policy contents. "ReadOnlyRole"
  can have any policy attached. Always read the actual policy documents.

- NEVER recommend adding an Allow statement without checking for an
  existing Deny that shadows it. Explicit Deny wins — adding an Allow
  on the same action+resource does nothing if a Deny matches. The fix
  is to scope or remove the Deny, not to add more Allows.

- NEVER report ROOT_CAUSE_FOUND when the only evidence is the error
  string. The error string does not distinguish implicit from explicit
  deny. Require CloudTrail `errorMessage` or simulator output before
  declaring the root cause.

## Remediation guidance

### For implicit deny (most common)

1. Identify the specific missing action and resource ARN from
   `simulate-principal-policy` output.
2. Add the minimum-scope Allow statement to the identity-based policy:
   specific action, specific ARN, no wildcards.
3. For cross-account, also add the corresponding Allow on the
   resource-based policy.
4. Re-run the simulator. If the simulator now returns `allowed`, the
   fix is complete.
5. Apply the policy change via a new managed policy version (do not
   edit inline — preserve audit history).

### For explicit deny

1. Identify the Deny statement from CloudTrail `errorMessage` or
   simulator matched statements.
2. Determine whether the Deny SHOULD match this request:
   - If yes (the workload should be in scope of the deny): the workload
     must be re-architected (different region, different resource tag,
     different network path) — do not weaken the deny.
   - If no (the deny was written too broadly): scope the deny to
     exclude the workload via a `Condition` (e.g.,
     `StringNotEqualsIfExists: aws:ResourceTag/Allow: "true"`).
3. Apply the deny-policy change. Test that the previously-denied call
   now succeeds AND that the deny still blocks the calls it was
   designed to block (regression test).

### For SCP denies (escalation path)

1. Identify the SCP from `organizations list-policies-for-target`.
2. Read the SCP from the management account.
3. If the workload is genuinely in scope, no SCP change — the workload
   must comply. Output ESCALATE if the SCP is owned by a central team.
4. If the SCP was written too broadly (e.g., region restriction
   excludes a region the workload legitimately uses), request an
   exception or a scoped exclude condition.

### For KMS key policy denies

1. Identify the calling role ARN.
2. Add a statement to the KEY policy (resource-based) granting
   `kms:Decrypt` (and `kms:DescribeKey` if the workload needs it) to
   the calling role ARN.
3. ALSO verify the caller's identity-based policy has `kms:Decrypt` on
   the key ARN (cross-account intersection).
4. If the key has a grant-based access pattern, prefer
   `kms:CreateGrant` over editing the key policy.

### For trust-policy AssumeRole denies

1. Read the target role's `assumeRolePolicyDocument`.
2. Identify the missing principal, condition, or external ID.
3. Add the caller's ARN to the `Principal.AWS` list. If the caller is
   a service, use the service principal
   (`lambda.amazonaws.com`) AND the service-linked role ARN if
   applicable.
4. If `sts:ExternalId` is required, ensure the caller passes the
   correct external ID (configured on both sides).

## Recent AWS features (2024-2026)

- **Access Analyzer policy validation (2024 GA):** Access Analyzer now
  surfaces logical errors, unused actions, and notable findings directly
  in the IAM console. For troubleshooting, generate a policy from
  CloudTrail activity via Access Analyzer to see what the principal
  actually does — the generated policy is the authoritative scope.
- **IAM Identity Center (SSO) permission sets and session policies
  (2024-2025):** Identity Center can inject session policies via
  permission set associations. Troubleshoot SSO-routed AccessDenied by
  reading the permission set's inline policy AND the session policy
  that Identity Center attaches.
- **`aws:CalledVia` / `aws:CalledViaFirst` / `aws:CalledViaLast` (2024):**
  These condition keys identify service-chain calls. Use them to scope
  Deny statements that should apply only when a call is made through a
  specific service (e.g., deny direct S3 access but allow S3 access via
  CloudFormation).
- **`aws:SourceOrgID` / `aws:SourceOrgPaths` (2024-2025):** For
  organizations-wide trust policies, these keys are more stable than
  `aws:SourceAccount` because they survive account moves between OUs.
- **Cross-account S3 access with bucket-owner-enforced ACLs (2024):**
  The default S3 ACL model now uses bucket-owner-enforced ACLs. Cross-
  account uploads work differently — the bucket owner automatically owns
  the object. This changes which KMS key policy entries are required for
  encrypted cross-account writes.

## References

See `references/policy-evaluation-logic.md` for the full policy
evaluation order with worked examples per layer, and
`references/common-gotchas.md` for the catalog of 30+ real-world
AccessDenied patterns and their fixes.

## Domain

AWS CloudOps / IAM Security & Access Control Diagnostics.

## AWS documentation

- **AWS IAM User Guide — Policy evaluation logic** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- **Cross-account access** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies-cross-account-resource-access.html
- **Troubleshooting IAM** — https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_general.html
- **Service control policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **Permissions boundaries** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html
- **IAM policy simulator** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html
- **STS AssumeRole troubleshooting** — https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_roles.html
