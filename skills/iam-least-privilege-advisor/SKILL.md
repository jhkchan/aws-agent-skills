---
name: iam-least-privilege-advisor
description: >-
  Analyzes AWS IAM policies to identify over-permissive grants — wildcard
  actions, wildcard resources, privilege-escalation actions (PassRole,
  AssumeRole), inverse wildcards (NotAction/NotResource), and condition-key
  bypasses — then provides least-privilege remediation. Use when reviewing
  IAM policies, checking for wildcard or escalation permissions, auditing
  role or user privileges, or tightening access control scope.
version: 0.3.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf). No AWS
  CLI required for offline policy-document classification. Live-account
  audits use aws iam simulate-principal-policy and aws cloudtrail
  lookup-events (AWS CLI v2, SSO or key-based credentials).
keywords:
  - IAM
  - least privilege
  - policy analysis
  - wildcard permissions
  - privilege escalation
  - over-permissive
  - IAM audit
  - PassRole
  - AssumeRole
  - NotAction
  - NotResource
  - condition bypass
  - policy remediation
tags: [iam, security, least-privilege, policy-analysis, privilege-escalation]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "OVERPERMISSIVE | LEAST_PRIVILEGE | AMBIGUOUS"
  when_to_use: >-
    Reviewing an IAM policy document (inline or managed), auditing a role or
    user before production deployment, checking for wildcard or escalation
    permissions, tightening access-control scope, or scoping down a policy
    derived from CloudTrail activity.
---

# IAM Least-Privilege Advisor

## Activation

Activate this skill when the user provides an IAM policy document (JSON),
references a role/user/group policy for review, or asks whether a policy is
safe, least-privilege, or over-permissive. Trigger phrases: "review this
policy", "is this least privilege?", "check my IAM policy", "tighten these
permissions", "audit this role", "scan for wildcard permissions", "is this
policy secure?".

## Mindset

Classify IAM policy documents against least-privilege principles and provide
specific remediation. The goal is not just "avoid wildcards" — it is to
identify the **blast radius** of every statement: what could a principal with
this policy actually do, and could an attacker chain these permissions for
privilege escalation?

A policy with `s3:GetObject` on one bucket has a narrow blast radius. A policy
with `iam:PassRole` on `"*"` has a catastrophic blast radius even though
neither the action nor the resource is `"*"`. The classification must catch
both obvious wildcards and subtle escalation paths.

## Quick reference

If the policy has `Action: "*"` on `Resource: "*"` or a service wildcard on
`"*"`, it is OVERPERMISSIVE. If it uses `NotAction`/`NotResource`, it is
OVERPERMISSIVE. If it grants `iam:PassRole` or `sts:AssumeRole` on `"*"`, it
is OVERPERMISSIVE. Named actions on specific ARNs are LEAST_PRIVILEGE. See
the steps below for edge cases (conditions, resource scope, exceptions).

## Process — Classification logic (apply in order)

### Step 0: Validate input and policy version

If the policy document is not valid JSON (malformed syntax, trailing commas,
unquoted keys, YAML where JSON is expected), output:

```text
POLICY: <name>
VERDICT: ERROR
REASON: Policy document is not valid JSON — cannot parse statements.
REMEDIATION: Validate the policy JSON with a linter or aws iam simulate-custom-policy --policy-input-list.
```

Do not attempt classification on malformed input. Additionally, check the
`Version` field: if it is `"2008-10-17"` (the legacy version), flag it —
policy variables like `${aws:username}` silently fail to resolve, and
several condition operators are unsupported. The correct version is
`"2012-10-17"`. A policy with the wrong version may behave differently
than its text suggests, making classification unreliable.

### Step 1: Separate Deny from Allow (with overlap resolution)

If a statement has `Effect: Deny`, it **narrows** effective permissions — it
never grants access. Deny statements are security controls. **Exclude Deny
statements from the verdict** — they can only reduce the policy's blast
radius, never increase it. However, if a Deny statement uses `NotAction` or
`NotResource`, append a **DENY_FLAG** note to the REMEDIATION field:

```text
DENY_FLAG: Statement <N> uses NotAction/NotResource in a Deny — this denies
all actions/resources except those listed, which may break workloads
silently. Review whether the deny is intentionally broad.
```

**Allow/Deny overlap resolution:** when the same action+resource pair appears
in both an Allow and a Deny statement within the same policy, the Deny
**always** wins regardless of statement order or Sid. This is the IAM
evaluation rule: explicit Deny takes absolute precedence. For classification,
do NOT let the presence of a Deny "cancel" an over-permissive Allow for a
*different* action+resource — only the exact overlapping pair is denied. A
policy that Allows `s3:*` on `*` and Denies `s3:DeleteBucket` on a specific
bucket is still OVERPERMISSIVE for every other S3 action and resource.

**Cross-policy overlap:** if a permissions boundary or SCP denies the action,
the effective permission is denied even though the identity-based policy
allows it. However, classify the identity-based policy on its own text — a
boundary can be removed, so the identity policy's blast radius is the
classification truth. Note the boundary presence in REMEDIATION.

### Step 2: Admin wildcard — maximum blast radius

If a statement has `Effect: Allow` with `Action: "*"` AND `Resource: "*"`,
the policy is **OVERPERMISSIVE** with **CRITICAL** risk. This grants every
action on every resource in the account — equivalent to
`AdministratorAccess`.

### Step 3: Service-level wildcards on all resources

If a statement has `Effect: Allow` with any wildcard action (e.g., `s3:*`,
`ec2:*`, `s3:Get*`, `iam:List*`) AND `Resource: "*"`, the policy is
**OVERPERMISSIVE** with **HIGH** risk — no scope restriction on either axis.
A generic service wildcard (e.g., `s3:*`, `ec2:*`) is **HIGH**, NOT CRITICAL —
only the privilege-escalation-service wildcards (Step 5) escalate to **CRITICAL**.

**Risk-level mapping (emit exactly one RISK per statement, derived from VERDICT):**
- `OVERPERMISSIVE` + admin wildcard (`Action: "*"` `Resource: "*"`) → **CRITICAL**
- `OVERPERMISSIVE` + privilege-escalation-service wildcard (Step 5 list) → **CRITICAL**
- `OVERPERMISSIVE` + any other service wildcard on `Resource: "*"` → **HIGH**
- `AMBIGUOUS` → **MODERATE** (access is conditionally restricted — bounded exposure)
- `LEAST_PRIVILEGE` → **LOW**

**Severity escalation:** If the wildcard action is on a **privilege-escalation
service**, escalate risk to **CRITICAL**:

- `iam:*` — full IAM control; can create users, roles, policies, and attach
  them to any principal.
- `sts:*` — can assume any role in the account or cross-account if the trust
  policy allows.
- `kms:*` — can decrypt any ciphertext, modify key policies, schedule key
  deletion. KMS is a data-access multiplier because most encrypted data
  flows through it.
- `secretsmanager:*` — can read every secret in the vault.
- `ssm:*` — can read all Parameter Store `SecureString` values (often
  credentials stored outside Secrets Manager).
- `lambda:*` — can create functions with any execution role when combined
  with `iam:PassRole`.
- `cloudformation:*` — can create stacks that instantiate any AWS resource
  with any passed role, bypassing the principal's own policy.

### Step 4: Inverse wildcards (NotAction / NotResource)

If a statement uses `NotAction` or `NotResource`, classify as
**OVERPERMISSIVE** regardless of what actions or resources are listed.
`NotAction` grants every action EXCEPT the listed ones — when AWS ships a
new API for that service, it is automatically included in the grant.
`NotResource` similarly grants access to all resources except those
explicitly excluded. These are inverse wildcards and are almost always a
misconfiguration or a debugging shortcut left in production.

### Step 5: Privilege-escalation actions on wildcard resources

If a statement grants any of these specific actions with `Resource: "*"`
(even without wildcard actions), classify as **OVERPERMISSIVE**. These
actions enable privilege escalation by design — a principal can use them to
gain permissions beyond their own policy:

- `iam:PassRole` on `"*"` — the single most common privesc vector. Allows
  passing any role to EC2, Lambda, CloudFormation, or any service that
  accepts a role ARN. The passed role's permissions then execute under that
  service's identity, not the caller's.
- `sts:AssumeRole` on `"*"` — allows assuming any role in the account.
- `iam:CreatePolicy` / `iam:CreatePolicyVersion` on `"*"` — can create
  arbitrary permission documents and attach them to any principal.
- `iam:AttachRolePolicy` / `iam:PutRolePolicy` on `"*"` — can attach any
  managed policy or inject an inline policy into any role.
- `iam:UpdateAssumeRolePolicy` on `"*"` — can modify the trust policy of any
  role, allowing arbitrary principals to assume it.
- `iam:CreateServiceLinkedRole` on `"*"` — frequently overlooked. Creates a
  service-linked role that grants the linked service permissions to act on
  the caller's behalf (e.g., `AWSServiceRoleForEC2Spot` grants Spot Fleet
  access). The principal effectively delegates escalated permissions to the
  service, bypassing their own policy limits.

### Step 6: Wildcard actions scoped to specific resources

If a statement has `Effect: Allow` with wildcard actions (e.g., `s3:Get*`,
`s3:List*`) but scoped to specific concrete ARNs, the policy is
**AMBIGUOUS**. Wildcard action patterns on narrow resources are often
acceptable for read-only workloads, but AWS adds new APIs over time —
`s3:Get*` silently included `s3:GetObjectTorrent`, and any future `Get*`
action is automatically granted.

### Step 7: Evaluate Condition keys for bypass paths

If an Allow statement includes a `Condition` block, check whether the
condition actually restricts access or creates a bypass. See the
**Condition-key bypass catalog** in the Expert edge cases section for the
full list with exploitation mechanics. Quick checklist:

- `aws:SourceIp` containing `0.0.0.0/0` — equivalent to no IP restriction.
- `ForAllValues:StringEquals` — evaluates true when request has zero
  matching values (absent-key bypass).
- `Null` operator with `"false"` — means "key must be ABSENT".
- `StringLike` without `*` anchors — exact match, but with unanchored
  wildcards like `${aws:username}`, user-controlled values may match
  unintended resources.

Statements with bypass-prone conditions classify as **AMBIGUOUS** at best.

### Step 8: Check resource ARN scope

If the resource ARN uses a partition wildcard (`arn:aws-*:`), it spans all
partitions — commercial, AWS GovCloud (US), and AWS China. If it uses a
broad pattern like `arn:aws:s3:::*`, it includes every S3 bucket globally,
not just the caller's account. These classify as **OVERPERMISSIVE** even
when the action is explicitly named — the resource scope is effectively
unconstrained.

### Step 9: Specific named actions on specific resources (LEAST_PRIVILEGE)

If all Allow statements have specific named actions (no wildcards, no
`NotAction`) AND specific resource ARNs (no `"*"`, no `NotResource`), the
policy is **LEAST_PRIVILEGE**.

**Legitimate `Resource: "*"` exception:** Some AWS actions only support
`Resource: "*"` by design and do NOT break LEAST_PRIVILEGE when paired with
explicitly named actions:

- `s3:ListAllMyBuckets`, `s3:HeadBucket`
- `iam:ListRoles`, `iam:ListUsers`, `iam:GetAccountSummary`
- `ec2:Describe*` (describe operations — resource-level permissions optional)
- `organizations:DescribeOrganization`, `organizations:ListAccounts`
- `cloudwatch:GetMetricStatistics`, `logs:DescribeLogGroups`,
  `sts:GetCallerIdentity`

These are safe as long as the action is explicitly named, not a service
wildcard like `ec2:*`.

### Step 10: IAM policy size check

After classification, verify the policy's serialized JSON size against IAM
limits:

- **Managed policy:** 6,144 characters max
- **Inline policy:** 10,240 characters max
- **Managed policy versions:** 10 versions max (oldest auto-deleted)

If the policy exceeds the limit, append a **SIZE_WARNING** to the
REMEDIATION field regardless of verdict:

```text
SIZE_WARNING: Policy is <N> characters, exceeding the <managed|inline> limit
of <limit>. Split into multiple statements scoped by service or resource
group. Use AWS IAM Access Analyzer policy generation to produce a compressed
form. If derived from CloudTrail, partition by service prefix.
```

### Step 11: Aggregation

When a policy contains multiple statements, the policy-level verdict is the
**worst** verdict across all Allow statements, where OVERPERMISSIVE is worse
than AMBIGUOUS and AMBIGUOUS is worse than LEAST_PRIVILEGE.

## Output format (per policy)

```text
POLICY: <name>
VERDICT: OVERPERMISSIVE | LEAST_PRIVILEGE | AMBIGUOUS
REASON: <1-2 sentences citing the specific statement and config>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if least-privilege>
```

### Multi-statement aggregation example

A policy with two statements — one tight, one broad:

```text
POLICY: mixed-policy
VERDICT: OVERPERMISSIVE
REASON: Statement 1 (s3:GetObject on arn:aws:s3:::app-data-prod/*) is LEAST_PRIVILEGE, but Statement 2 (iam:PassRole on "*") is OVERPERMISSIVE (privilege escalation). Policy verdict is the worst statement.
RISK: CRITICAL
REMEDIATION: Restrict iam:PassRole in Statement 2 to the specific role ARN the workload needs (e.g., arn:aws:iam::123456789012:role/app-execution-role).
```

## Expert edge cases

These patterns represent genuine, non-obvious IAM attack surface that a
senior security engineer would catch but a generalist would miss.

### S3 dual-ARN requirement

S3 bucket actions and object actions use **different ARN shapes**, and a
correct policy must grant both:

- **Bucket-level actions** (e.g., `s3:ListBucket`, `s3:DeleteBucket`,
  `s3:GetBucketLocation`) require `arn:aws:s3:::bucket-name` (no trailing `/*`).
- **Object-level actions** (e.g., `s3:GetObject`, `s3:PutObject`,
  `s3:DeleteObject`) require `arn:aws:s3:::bucket-name/*` (with trailing `/*`).

A policy granting `s3:GetObject` on `arn:aws:s3:::bucket-name` (without `/*`)
silently fails — the action never matches. Conversely, granting `s3:*` on
both ARNs to "fix" the mismatch grants destructive bucket-level actions.
Classify such mismatches as **AMBIGUOUS** (the policy does not work as
written, but broadening it introduces over-permission).

### Scoping PassRole with `iam:PassedToService`

The safest way to scope `iam:PassRole` is not just to a specific role ARN
but also via the `iam:PassedToService` condition key, which restricts
*which AWS service* may receive the role:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::123456789012:role/app-execution-role",
  "Condition": {
    "StringEquals": { "iam:PassedToService": "lambda.amazonaws.com" }
  }
}
```

This prevents the role from being passed to EC2, CloudFormation, or any
other service that accepts role ARNs. Without this condition, a principal
with `iam:PassRole` on a specific role can still pass it to any service,
potentially escalating via a service with broader network access (e.g.,
EC2 with a public IP).

### Cross-account data exfiltration via `aws:ResourceAccount`

A policy that grants `s3:GetObject` on `arn:aws:s3:::*/*` allows reading
objects from **any AWS account's buckets**, not just the caller's account,
if the bucket owner cross-accounts the principal. The defense is the
`aws:ResourceAccount` condition:

```json
"Condition": { "StringEquals": { "aws:ResourceAccount": "123456789012" } }
```

Without this condition, any resource wildcard spanning `*` is a
cross-account exfiltration vector. Flag broad S3/KMS/SQS resource patterns
without `aws:ResourceAccount` as **AMBIGUOUS** at minimum.

### Tag-mutation bypass of `aws:ResourceTag` conditions

ABAC policies conditioned on `aws:ResourceTag/Environment: prod` are
**bypassable** if the principal also has `tag:TagResources` (or a broad
permission like `ec2:*` that includes tagging). The principal can tag any
resource with `Environment=prod` and then access it. When evaluating
tag-based conditions, check whether the same policy (or other policies
attached to the principal) grants tagging permissions on the same resource
type. If so, downgrade the classification — the tag condition provides no
real boundary.

### `kms:Decrypt` on `Resource: "*"`

Even without `kms:*`, a grant of `kms:Decrypt` on `"*"` is a silent data
exfiltration vector. If any AWS service uses a customer-managed KMS key for
encryption (S3 server-side encryption, EBS volumes, RDS snapshots, Secrets
Manager), a principal with `kms:Decrypt` on `"*"` can decrypt that data
*if they can first access the ciphertext*. Classify `kms:Decrypt` on `"*"`
as **OVERPERMISSIVE** with **HIGH** risk — it is a data-access multiplier
that silently extends the blast radius of every encrypted resource.

### Condition-key bypass catalog

| Pattern | Exploitation mechanic | Correct defense |
| --- | --- | --- |
| `aws:SourceIp: 0.0.0.0/0` | CIDR covers entire internet; no restriction | Use real egress CIDR or remove condition |
| `ForAllValues:StringEquals` | True when request has zero matching values — absent key bypasses | Use `ForAnyValue` or add explicit Deny on `Null` |
| `Null: { key: "false" }` | Means "key must be absent" — true when MFA never checked | Use `"true"` (require presence) + `Bool` check |
| `StringLike` without anchors | `${aws:username}` in a resource ARN with `StringLike` can match unintended paths if username contains special chars | Use `StringEquals` for exact, or anchor with explicit `*` placement |
| `aws:PrincipalArn` in trust policy | A trust policy granting `sts:AssumeRole` to `aws:PrincipalArn` matching a broad pattern can be exploited by any matching principal | Restrict to exact ARN, never pattern-match on principal |
| `aws:RequestTag` without `ForAllValues` | Only checks tags present in request; does not enforce required tags exist | Pair with `Null` check or `ForAllValues:StringEquals` |
| Missing `aws:SecureTransport` | Allows HTTP alongside HTTPS for API calls supporting both | Add `Bool: { aws:SecureTransport: "true" }` |
| `aws:MultiFactorAuthPresent` via `Bool` alone | `Bool` check fails silently if key absent (e.g., programmatic call never sets MFA key) | Combine `Null: false` (require key present) with `Bool: true` (require MFA value) |

### MFA condition interaction

The correct MFA enforcement pattern requires **two** conditions working
together — a common error is using only one:

1. `Null: { "aws:MultiFactorAuthPresent": "false" }` — ensures the key EXISTS
   in the request (programmatic calls via CLI/SDK without MFA do NOT include
   this key at all, so a `Bool` check alone silently passes).
2. `Bool: { "aws:MultiFactorAuthPresent": "true" }` — ensures the value is
   true (MFA was actually used).

Using only `Bool` is the most common MFA bypass: the condition evaluates to
false (key absent → not true → condition fails → access denied) in many
cases, BUT certain long-lived credentials (e.g., role assumption chains) may
forward the key unexpectedly, and the absence semantics are
account-dependent. Always use both conditions together.

### Service-specific PassRole variants

`iam:PassRole` is not the only action that passes roles to services.
Several services have their own "pass-role" semantics that do NOT require
`iam:PassRole` but achieve a similar effect:

- `states:CreateStateMachine` / `states:UpdateStateMachine` — passes an
  execution role to Step Functions.
- `glue:CreateJob` / `glue:CreateCrawler` — passes a role to Glue.
- `lex:CreateBot` / `lex:UpdateBot` — passes a role to Lex.
- `opsworks:CreateStack` — passes a role to OpsWorks.

If the policy grants `iam:PassRole` on `"*"`, check whether these service
actions are also allowed — they compound the escalation surface because
each service executes under the passed role's identity.

### Cross-account trust policy abuse

A role trust policy (`Resource`-based policy on the IAM role itself) that
uses `aws:PrincipalArn` or `aws:PrincipalAccount` with a wildcard pattern
(e.g., `arn:aws:iam::*:role/*`) allows **any AWS account** to attempt
assumption. The `sts:ExternalId` condition is the standard defense for
cross-account trust:

```json
"Condition": { "StringEquals": { "sts:ExternalId": "<unique-hardcoded-id>" } }
```

Without `sts:ExternalId`, a confused-deputy attack is possible: any
principal matching the trust pattern can assume the role. Flag trust
policies with broad principal patterns and no `sts:ExternalId` as
**OVERPERMISSIVE**.

## Effective permissions context

The classification logic above evaluates a single identity-based policy
document in isolation. In production, AWS computes **effective permissions**
by intersecting multiple policy layers in this evaluation order:

1. **Explicit Deny** in ANY policy (identity, resource-based, SCP, permissions
   boundary, session policy) → request is DENIED. Deny wins everywhere.
2. **Permissions boundary** (if attached to the role) → if the boundary does
   not allow the action, request is DENIED. A boundary caps the maximum
   effective permissions regardless of what the identity-based policy grants.
3. **Service Control Policy (SCP)** (if the account is in an Organization) →
   SCPs set the maximum permissions for the account. An Allow in an SCP does
   nothing; only a Deny restricts.
4. **Session policy** (if the role was assumed with a session policy) → the
   effective permissions are the INTERSECTION of the role's policy and the
   session policy.
5. **Identity-based policy** Allow → grants access if no above layer denied.
6. **Resource-based policy** (S3 bucket policy, KMS key policy, SQS policy,
   Lambda function policy):
   - **Same-account access**: EITHER the identity-based OR the resource-based
     policy can grant access (union). A principal with no identity-based
     policy can still access a resource if the resource-based policy allows
     it.
   - **Cross-account access**: BOTH the identity-based AND the resource-based
     policy must allow access (intersection).

**Cross-account resource-based policy decision branch:**
When evaluating a resource-based policy (e.g., S3 bucket policy):

1. If `Principal: "*"` with no condition → **OVERPERMISSIVE** (any AWS
   account principal can access, limited only by the caller's identity-based
   policy, which the resource owner does not control).
2. If `Principal: "*"` with `aws:SourceAccount` or `aws:SourceArn`
   condition → **AMBIGUOUS** (scoped to a specific account/ARN, but the
   resource owner depends on the caller's account configuration).
3. If `Principal` is a specific ARN → evaluate the action/resource scope as
   normal for LEAST_PRIVILEGE / OVERPERMISSIVE.
4. For **same-account** resource-based policies with `Principal: "*"`:
   **AMBIGUOUS** — the blast radius is wider than the identity-based policy
   alone suggests (any principal in the account can access without their
   own Allow).

**Classification implication:** Always classify the identity-based policy on
its own text. Note the presence of resource-based policies and boundaries in
the REMEDIATION field — they affect effective permissions but do not change
the classification of the policy document under review.

## Anti-Patterns — NEVER

- NEVER classify `Action: "*", Resource: "*"` as anything other than
  OVERPERMISSIVE. This grants administrative access to every service and
  resource — the most dangerous pattern in AWS IAM.

- NEVER classify a service wildcard on `Resource: "*"` (e.g., `s3:*` on
  `"*"`) as LEAST_PRIVILEGE. The resource wildcard means every bucket,
  every object, every setting; the action wildcard adds deletion and
  configuration changes.

- NEVER treat `NotAction` or `NotResource` as a scoped grant. These are
  inverse wildcards that grant everything except the listed values. New AWS
  APIs are automatically included.

- NEVER assume a policy is safe because the role name sounds harmless
  (e.g., "ReadOnlyRole", "app-service-role"). Role names are human labels;
  always verify the policy document.

- NEVER recommend managed policies (`AdministratorAccess`,
  `PowerUserAccess`, `AmazonS3FullAccess`) as remediation. They reintroduce
  the exact blast radius being constrained. `PowerUserAccess` grants full
  access to every service except IAM — still effectively admin-level.

- NEVER ignore `Condition` keys using `ForAllValues` — this operator
  evaluates true when the request contains zero matching values, creating
  a bypass when the attribute is absent from the request.

- NEVER treat `iam:PassRole` on `"*"` as safe. This is the most common
  privilege-escalation vector — it lets a principal pass any role to any
  service, executing under the passed role's permissions.

- NEVER classify a policy as OVERPERMISSIVE based on its `Effect: Deny`
  statements. Deny statements only restrict; they cannot grant access.

- NEVER accept `aws:SourceIp` with `0.0.0.0/0` as a real condition — it is
  the CIDR for the entire internet and provides zero restriction.

- NEVER trust `aws:ResourceTag` conditions as a hard boundary when the
  principal has `tag:TagResources` or a broad service wildcard that includes
  tagging (e.g., `ec2:*`). The principal can self-tag resources to satisfy
  the condition and bypass the ABAC boundary.

- NEVER use `aws:PrincipalArn` with a wildcard pattern in a role trust
  policy. This allows any principal matching the pattern (potentially
  any account) to assume the role. Always use exact ARNs.

- NEVER assume a `StringLike` condition without explicit `*` anchors is
  safe against injection. If the matched value is user-controlled (e.g.,
  `${aws:username}` expanded into a resource ARN), a username containing
  path separators or wildcards can cause unintended matches.

- NEVER assume a scoped policy fits within IAM limits without checking.
  Inline policies are capped at 10,240 characters; managed policies at
  6,144 characters; a maximum of 10 versions per managed policy. A policy
  derived from CloudTrail with hundreds of unique actions may exceed these
  limits — split across multiple statements or policies.

- NEVER trust `iam:simulate-principal-policy` results blindly for
  cross-service scenarios. The simulator tests individual actions in
  isolation and may report a permission as denied when the workload uses
  a chained API flow (e.g., `lambda:InvokeFunction` calling `s3:GetObject`
  under the function's role). Always cross-reference simulator results
  with actual CloudTrail activity.

- NEVER treat `kms:Decrypt` on `Resource: "*"` as a minor issue. It is a
  silent data-exfiltration multiplier — any encrypted resource in the
  account becomes readable if the ciphertext is accessible.

- NEVER overlook `iam:CreateServiceLinkedRole` as a privilege-escalation
  vector. It delegates permissions to the linked service, which may exceed
  the principal's own policy limits.

## Remediation guidance

### CloudTrail-derived least-privilege workflow

The authoritative procedure for generating a scoped policy from observed
API usage:

1. **Identify the principal** — get the role or user ARN from the policy
   under review.
2. **Query CloudTrail** — pull a minimum of 90 days of events where
   `userIdentity.arn` matches the principal. 90 days captures quarterly
   batch jobs and monthly rotations that a 30-day window would miss. Use
   CloudTrail LookupEvents for targeted queries or Athena for high-volume
   trails.
3. **Extract unique API calls** — build a set of `EventSource` +
   `EventName` pairs and map to IAM action format (e.g.,
   `s3.amazonaws.com` + `GetObject` maps to `s3:GetObject`).
4. **Extract resource ARNs** — from `requestParameters` and the `resources`
   field. For S3, map `bucketName` to both `arn:aws:s3:::<bucket>` and
   `arn:aws:s3:::<bucket>/*`.
5. **Account for implicit calls** — SDKs often call list/describe before
   write operations (e.g., `s3:ListBuckets` before `s3:PutObject`). Include
   these if the workload depends on them.
6. **Preserve service-list exceptions** — actions that only support
   `Resource: "*"` (see Step 9) must keep `"*"` or the policy will fail.
7. **Generate the policy** — use AWS IAM Access Analyzer policy generation
   or build manually from the action + resource lists.
8. **Validate** — run `aws iam simulate-principal-policy` with the scoped
   action list to confirm the principal can still perform required
   operations without `AccessDenied`.
9. **Apply and monitor** — attach the scoped policy, then watch CloudTrail
   for `AccessDenied` events for 1-2 weeks. Add any missing actions and
   iterate.

### For OVERPERMISSIVE policies

- Replace wildcard actions with specific named actions derived from
  CloudTrail (workflow above).
- Replace `Resource: "*"` with the specific ARN(s) the workload accesses.
- For privilege-escalation actions (`iam:PassRole`, `sts:AssumeRole`):
  restrict to the minimum role ARN the workload needs — never leave on
  `"*"`. Add `iam:PassedToService` to constrain which service can receive
  the role.
- For `NotAction` / `NotResource`: convert to explicit `Action` and
  `Resource` allow-lists.
- For partition wildcards (`arn:aws-*:`): pin to `arn:aws:` for the
  partition the workload operates in.
- For `kms:Decrypt` on `"*"`: scope to specific key ARNs and add
  `aws:ResourceAccount` to prevent cross-account decryption.

### For AMBIGUOUS policies

- Expand wildcard patterns to explicit named actions (e.g., replace
  `s3:Get*` with the specific `s3:GetObject`, `s3:GetObjectVersion`).
- Review Condition keys for bypass paths (Step 7, Condition-key bypass
  catalog).
- Validate that the resource ARN scope matches the workload boundary.
- For tag-based conditions: verify the principal does NOT have tagging
  permissions on the same resources, or add an explicit Deny on
  `tag:TagResources`.

### For LEAST_PRIVILEGE policies

- No remediation required.
- Confirm the policy is attached only to the intended principal.
- Verify a permissions boundary is set on the role if the account has a
  broad SCP — the boundary caps the maximum effective permissions.

### For policies exceeding IAM size limits

- Split by service prefix (e.g., all `s3:*` actions in one statement, all
  `ec2:*` in another).
- Use customer-managed policies instead of inline (larger size limit).
- Factor common action+resource pairs into a reusable managed policy.
- If the policy is CloudTrail-derived, partition by event source.

## Recent AWS features (2024-2026)

- **IAM Access Analyzer unused-access GA (2024):** Access Analyzer's unused-access analysis is now GA, generating findings for unused IAM roles, access keys, passwords, permissions, and SCPs. This directly supports the least-privilege audit — auditors should cross-reference unused-access findings with the IAM policy analysis to identify both over-broad AND unused permissions.
- **Identity Center (SSO) updates (2024-2025):** AWS IAM Identity Center received enhanced permission set management and application assignment features. Auditors should verify that Identity Center permission sets do not include wildcard actions and that application assignments are scoped to necessary principals only.
- **New condition keys (2024-2025):** AWS added new global condition keys including `aws:SourceOrgID`, `aws:SourceOrgPaths`, and enhanced `aws:CalledVia` / `aws:CalledViaFirst` / `aws:CalledViaLast`. Auditors should verify that policies use the strongest available condition key for service-to-service integrations.
- **Session policies and permissions boundaries awareness:** The analysis should account for permissions boundaries and session policies when computing effective permissions — an over-permissive IAM policy may be mitigated by a boundary. However, the absence of a boundary means the IAM policy IS the effective permission.

## References

See `references/policy-analysis-guide.md` for the wildcard pattern reference
table, common over-permissive patterns found in the wild, and the
remediation tool reference.

## Domain

AWS CloudOps / IAM Security & Compliance.

## AWS documentation

- **AWS IAM User Guide** — https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html
- **IAM Security Best Practices** — https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- **IAM API Reference** — https://docs.aws.amazon.com/IAM/latest/APIReference/
- **IAM CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/iam/
- **IAM Access Analyzer policy validation** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html
