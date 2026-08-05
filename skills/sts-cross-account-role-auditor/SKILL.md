---
name: sts-cross-account-role-auditor
description: >-
  Audits IAM role trust policies (AssumeRolePolicyDocument) for cross-account
  exposure, wildcard Principal grants, confused-deputy service-principal
  vectors, and condition-strength weaknesses. Emits a deterministic
  EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK verdict per role with
  severity and remediation. Use when reviewing IAM role trust policies,
  checking who can assume a role, auditing cross-account access, validating
  ExternalId or SourceArn guards, or hardening role trust before production.
  Triggers: STS, AssumeRole, trust policy, AssumeRolePolicyDocument,
  cross-account, ExternalId, confused deputy, Principal AWS root, Principal
  Service, Principal star, SAML federated, SourceArn, SourceAccount,
  NotPrincipal, role trust audit, role assumption exposure.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline trust-policy classification. Live
  account audits use aws iam get-role --query Role.AssumeRolePolicyDocument
  and aws iam list-roles (AWS CLI v2, SSO or key-based credentials).
keywords:
  - STS
  - trust policy
  - AssumeRole
  - AssumeRolePolicyDocument
  - cross-account
  - ExternalId
  - confused deputy
  - Principal
  - wildcard principal
  - role trust
  - SAML
  - OIDC
  - federated
  - SourceArn
  - SourceAccount
  - NotPrincipal
  - role assumption
  - IAM audit
  - security
tags: [sts, iam, security, trust-policy, cross-account, external-id, confused-deputy, role-audit]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [sts, iam, security, trust-policy, cross-account, external-id, confused-deputy, role-audit]
  dependencies:
    - aws-orchestrator
  keywords:
    - STS
    - trust policy
    - AssumeRole
    - cross-account
    - ExternalId
    - confused deputy
    - Principal
    - wildcard principal
    - SourceArn
    - SourceAccount
    - role trust
  when_to_use: >-
    Reviewing an IAM role trust policy (AssumeRolePolicyDocument), auditing who
    can assume a role, checking cross-account or external access exposure,
    validating ExternalId / SourceArn / SourceAccount guards, hardening a
    service-role trust before production, or investigating confused-deputy
    attack surface.
---

# STS Cross-Account Role Auditor

## Mindset

Classify IAM role **trust policies** (the `AssumeRolePolicyDocument` attached to
every IAM role) against cross-account and external-trust principles. The trust
policy is the single gate that controls WHO can assume a role and obtain its
permissions — it is the highest-leverage security surface in IAM because a
misconfigured trust policy grants an external entity the **entire permission
set** of the role.

The goal is not just "is the Principal `"*"`?" — it is to identify the **trust
boundary** of every statement: could an entity outside the owning account
assume this role, and if so, is there a guard (ExternalId, SourceArn,
SourceAccount) that constrains the assumption to a verified caller?

A trust policy with `Principal: "*"` is an open door — anyone on the internet
with AWS credentials can assume the role. A trust policy with a cross-account
root ARN but no ExternalId is a door that the third party's account admin can
open to any principal in their account. A trust policy with a confused-deputy
service principal and no SourceArn is a door that any AWS customer can walk
through via that service. The classification must catch all three patterns,
plus the subtler condition-bypass paths.

## What this skill is NOT

This skill audits the **trust policy** (who can assume the role). It does NOT
audit the role's **permissions policy** (what the role can do after assuming
it) — that is the domain of `iam-least-privilege-advisor`. A role with a clean
trust policy but an over-permissive permissions policy is still dangerous; the
two surfaces must be audited independently. When the permissions policy is
available, recommend running both skills.

## Quick reference

If the trust policy has `Principal: "*"` or `{"AWS": "*"}` with no strong
condition, it is WILDCARD_TRUST. If it grants to a cross-account ARN without
`sts:ExternalId`, it is EXTERNAL_TRUST. If it grants to a confused-deputy-risk
service without `aws:SourceArn`/`aws:SourceAccount`, it is EXTERNAL_TRUST. If
it has an external surface but a strong guarding condition, it is CONDITIONAL.
If it only allows same-account principals or properly guarded service links,
it is OK. See the steps below for edge cases (NotPrincipal, SAML/OIDC,
weak conditions, session tags).

**Condition strength at a glance** (see full matrix below):
- STRONG (→ CONDITIONAL): `sts:ExternalId` (StringEquals),
  `aws:SourceAccount` (StringEquals), `aws:SourceArn` (ArnLike),
  `aws:sourceVpce`/`aws:sourceVpc`, `SAML:sub`/`SAML:aud`, `oidc:sub`/`oidc:aud`.
- WEAK (→ still WILDCARD_TRUST/EXTERNAL_TRUST): `aws:SourceIp` with
  `0.0.0.0/0`, `aws:Referer`, `aws:UserAgent`, `sts:ExternalId` with
  `StringLike` + wildcard.
- TRAP: `ForAllValues:StringEquals` on `aws:SourceArn` evaluates TRUE when
  the key is absent — use `ForAnyValue` or `ArnLike` instead.

## The confused-deputy problem (core concept)

This is the single most important STS trust concept and the most commonly
misunderstood. When you write:

```json
{
  "Principal": {"Service": "lambda.amazonaws.com"},
  "Action": "sts:AssumeRole"
}
```

you are NOT granting access to YOUR Lambda functions. You are granting access
to the **Lambda service** — an AWS-owned service endpoint that ANY AWS
customer can invoke. If another AWS account creates a Lambda function that
triggers an AssumeRole call to your role, the Lambda service (which your
trust policy trusts) will make that call on behalf of the other account.
Your role is now assumed by an attacker.

This is the **confused-deputy problem**: a trusted service (the deputy) is
confused about which customer it is acting for, and an attacker exploits that
confusion to access resources they should not reach.

**The fix** is to add a condition that identifies the calling customer:

```json
"Condition": {
  "StringEquals": {
    "aws:SourceAccount": "123456789012"
  }
}
```

or, more precisely:

```json
"Condition": {
  "ArnLike": {
    "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"
  }
}
```

`aws:SourceArn` is stronger than `aws:SourceAccount` because it scopes to a
specific resource, not just an account. `aws:SourceAccount` is the minimum
acceptable guard.

## Process — Classification logic (apply in order)

### Step 0: Validate input and extract owning account

If the trust policy document is not valid JSON, output:

```text
ROLE: <name>
VERDICT: ERROR
REASON: Trust policy document is not valid JSON — cannot parse statements.
REMEDIATION: Validate with aws iam get-role --role-name <name> --query Role.AssumeRolePolicyDocument.
```

Do not attempt classification on malformed input.

**Extract the owning account ID** from the role ARN (e.g.,
`arn:aws:iam::123456789012:role/my-role` → owning account is
`123456789012`). If the role ARN is not provided, extract from context or
flag that same-account verification cannot be performed and treat all
account-root principals as potentially cross-account.

Check the `Version` field: `"2008-10-17"` is legacy and causes policy
variables (`${aws:username}`) and some condition operators to fail silently.
The correct version is `"2012-10-17"`.

### Step 1: NotPrincipal / NotAction inverse wildcards

If ANY statement uses `NotPrincipal` or `NotAction`, classify as
**WILDCARD_TRUST** with **CRITICAL** risk.

`NotPrincipal` in a trust policy grants the AssumeRole action to EVERY
principal EXCEPT the listed ones — this is effectively an open role and is
almost always a misconfiguration. `NotAction` grants every STS action
(`sts:AssumeRole`, `sts:AssumeRoleWithSAML`,
`sts:AssumeRoleWithWebIdentity`, `sts:DecodeAuthorizationMessage`) except
the listed ones, broadening the attack surface unpredictably.

Cite "Step 1: inverse wildcard (NotPrincipal/NotAction)".

### Step 2: Unrestricted wildcard Principal

If ANY Allow statement has `Principal` of `"*"`, `{"AWS": "*"}`, or any
principal element that resolves to all principals, evaluate the condition:

- **No `Condition` block at all** → **WILDCARD_TRUST**, **CRITICAL**. Anyone
  with AWS credentials (which anyone can obtain via the free tier) can assume
  the role. This grants the role's entire permission set to the public
  internet.

- **Condition present** → proceed to the **Condition strength matrix** below.
  If the condition contains ONLY weak keys (Referer, UserAgent, SourceIp
  `0.0.0.0/0`) → still **WILDCARD_TRUST**, **CRITICAL**. The condition
  provides no real restriction.

- **Condition contains at least one STRONG key** (sourceVpce, sourceVpc,
  SourceAccount, SourceArn) → **CONDITIONAL**, **MODERATE**. The wildcard
  principal is narrowed by a real guard, but a policy edit or condition
  removal could expose it.

Cite "Step 2: wildcard Principal" with the condition evaluation result.

### Step 3: Cross-account Principal without ExternalId

If ANY Allow statement has a `Principal.AWS` that is an account-root ARN
(`arn:aws:iam::<ACCOUNT>:root`), role ARN, or user ARN where `<ACCOUNT>` ≠
the role's owning account, evaluate the ExternalId guard:

- **No `sts:ExternalId` condition** → **EXTERNAL_TRUST**, **HIGH**. The
  trusting account has no verification that the assuming principal is the
  intended third party. The third party's account administrator can grant
  `sts:AssumeRole` on this role's ARN to ANY principal in their account
  (including new users, new roles, or compromised credentials).

- **`sts:ExternalId` present in `StringEquals`** → **CONDITIONAL**,
  **MODERATE**. The ExternalId is a shared secret that the trusting account
  sets and the third party must provide. It prevents the third party's
  account admin from unilaterally granting access — without the ExternalId,
  even root in the third-party account cannot assume the role.

- **`sts:ExternalId` with `StringLike` and a wildcard pattern** (e.g.,
  `"*-prod"`) → still **EXTERNAL_TRUST**, **HIGH**. `StringLike` with
  wildcards weakens the guard — an attacker who knows or guesses the pattern
  suffix can bypass it. ExternalId must be an opaque, unguessable string
  matched with `StringEquals`.

Cite "Step 3: cross-account without ExternalId" or "Step 3: cross-account
with ExternalId (CONDITIONAL)".

**Critical expert note — the root ARN expansion rule:**
`arn:aws:iam::123456789012:root` does NOT mean "only the root user of
account 123456789012". It means **every authenticated principal** in that
account — root, every IAM user, every IAM role, and every assumed-role
session. This is because the trust policy is evaluated at the IAM layer,
which matches the account-level root principal pattern. A common mistake is
to assume that granting to `:root` limits exposure to the root user only;
it does not. If the intent is to allow only a specific role, the Principal
must name that role ARN explicitly:
`arn:aws:iam::123456789012:role/specific-role`.

### Step 4: Confused-deputy service Principal without source guard

If ANY Allow statement has `Principal.Service` set to a
**confused-deputy-risk service** (see list below) and the `Condition` block
does NOT contain `aws:SourceAccount` or `aws:SourceArn`, classify as
**EXTERNAL_TRUST**, **HIGH**.

**Confused-deputy-risk services** (services that can be invoked by any AWS
customer and therefore can be triggered cross-account):

- `lambda.amazonaws.com` — any AWS customer can create a Lambda function
  that calls `sts:AssumeRole`.
- `ec2.amazonaws.com` — any customer can launch an EC2 instance with an
  instance profile.
- `cloudformation.amazonaws.com` — any customer can create a stack that
  passes a role.
- `eks.amazonaws.com` / `eks-nodegroup.amazonaws.com` / `eks-fargate.amazonaws.com`
  — EKS service roles; confused-deputy via EKS cluster creation.
- `ecs-tasks.amazonaws.com` / `ecs.amazonaws.com` — ECS task execution.
- `states.amazonaws.com` — Step Functions can be invoked cross-account.
- `events.amazonaws.com` / `pipes.amazonaws.com` — EventBridge rules and
  Pipes can be targeted cross-account.
- `sns.amazonaws.com` / `sqs.amazonaws.com` — messaging services that
  accept cross-account subscriptions.
- `codebuild.amazonaws.com` / `codepipeline.amazonaws.com` — CI/CD services.
- `apigateway.amazonaws.com` / `apigateway.amazonaws.com` — API Gateway
  can forward AssumeRole calls.
- `backup.amazonaws.com` — AWS Backup service roles.
- `cloudtrail.amazonaws.com` — CloudTrail can be configured cross-account.
- `config.amazonaws.com` / `config-multiaccountsetup.amazonaws.com` —
  Config aggregator roles.
- `controltower.amazonaws.com` / `member.org.stacksets.cloudformation.amazonaws.com`
  — Control Tower / Organizations member roles.
- `auditmanager.amazonaws.com` — Audit Manager service-linked roles.
- `macie.amazonaws.com` / `securityhub.amazonaws.com` / `guardduty.amazonaws.com`
  — security services with cross-account aggregation.
- `wafv2.amazonaws.com` / `waf-regional.amazonaws.com` — WAF service roles.
- `firehose.amazonaws.com` / `es.amazonaws.com` / `aoss.amazonaws.com` —
  data services with cross-account delivery.
- `bedrock.amazonaws.com` — Bedrock service roles.

**Lower-risk service principals** (services that operate within a single
account boundary by design and are less commonly exploited as confused-deputy
vectors, but should still be reviewed):

- `awslambda.amazonaws.com` (legacy Lambda spelling — same risk as the modern spelling)
- `dynamodb.amazonaws.com` — DynamoDB Streams service role (single-account by design, but verify if cross-account streams are configured)
- `ds.amazonaws.com` — Directory Service (single-account by design)
- `ssm.amazonaws.com` — Systems Manager (can operate cross-account via Session Manager delegations; verify deployment scope)
- `transfer.amazonaws.com` — AWS Transfer Family (single-account by design)
- `quicksight.amazonaws.com` — QuickSight (single-account by design)

For any service principal NOT on either list above, classify as CONDITIONAL
with a note to manually verify the service's confused-deputy posture via the
AWS documentation for that service.

**Expert note — `aws:SourceArn` vs `aws:SourceAccount`:**
`aws:SourceArn` is stronger because it identifies the exact resource making
the call (e.g., a specific Lambda function ARN). `aws:SourceAccount`
identifies only the account. If the source account has many principals, any
of them can trigger the service to assume the role. Use `ArnLike` for
`aws:SourceArn` (allows wildcard in the resource path) and `StringEquals`
for `aws:SourceAccount`. For maximum precision, use BOTH:
`aws:SourceArn` for resource-level scope AND `aws:SourceAccount` as a
defense-in-depth guard.

If the service principal IS on the risk list and `aws:SourceAccount` or
`aws:SourceArn` IS present → proceed to Step 5.

If the service principal is NOT on the risk list above (e.g., a rare or
internal service), classify as **CONDITIONAL** with a note to verify the
service's confused-deputy posture manually.

### Step 5: Confused-deputy service Principal WITH source guard

If a confused-deputy-risk service principal has `aws:SourceAccount` or
`aws:SourceArn` in the `Condition` block (with `StringEquals`, `StringLike`,
`ArnLike`, or `ArnEquals`), classify as **CONDITIONAL**, **MODERATE**.

The source guard narrows the trust to a specific account or resource, but
the role is still assumable via a service that operates outside the owning
account's direct control. A condition removal or service-principal change
could expose it.

Cite "Step 5: confused-deputy with source guard (CONDITIONAL)".

### Step 6: SAML / OIDC federated Principal

If ANY Allow statement has `Principal.Federated` (SAML or OIDC identity
provider), evaluate the condition:

- **`Principal.Federated` is an account-specific IdP ARN**
  (e.g., `arn:aws:iam::123456789012:saml-provider/CorporateIdP`) AND the
  `Condition` constrains `SAML:sub` (subject), `SAML:aud` (audience), or
  `SAML:sub_type` → **CONDITIONAL**, **MODERATE**. The IdP controls who can
  assume the role; the condition narrows which assertions are accepted.

- **Same as above but NO `Condition` block** → **EXTERNAL_TRUST**, **HIGH**.
  Any assertion from the IdP that matches the provider ARN is accepted —
  the IdP admin (or anyone who compromises the IdP) controls access to
  your AWS role.

- **`Principal.Federated` is `cognito-identity.amazonaws.com`** (Cognito) →
  **CONDITIONAL**, **MODERATE** if `Condition` has
  `cognito-identity.amazonaws.com:aud` (user-pool/client ID) and
  `cognito-identity.amazonaws.com:amr` (authenticated/unauthenticated).
  Without these → **EXTERNAL_TRUST**, **HIGH**.

- **`Principal.Federated` is `"*"`, `{"AWS": "*"}`, or a wildcard OIDC URL**
  (e.g., `accounts.google.com` without audience constraint) →
  **WILDCARD_TRUST**, **CRITICAL**. Any federated identity can assume.

**Action field check for federated statements:** the `Action` must be
`sts:AssumeRoleWithSAML` (for SAML) or `sts:AssumeRoleWithWebIdentity` (for
OIDC). If the Action is `sts:AssumeRole` with a Federated principal, flag
as a misconfiguration — the combination is invalid and the statement will
silently fail at runtime.

Cite "Step 6: federated trust — <SAML|OIDC|Cognito>".

### Step 7: Session tag injection risk

If ANY Allow statement in the trust policy grants `sts:TagSession` (or the
broader `sts:AssumeRole` which implicitly allows tag propagation), check
for `sts:TransitiveTagKeys`:

- **`sts:TagSession` allowed with no `sts:TransitiveTagKeys` limit** → append
  a **TAG_INJECTION_FLAG** to the REMEDIATION field. The assuming principal
  can set arbitrary session tags, which may propagate to downstream ABAC
  (attribute-based access control) evaluations and bypass resource-level
  tag conditions.

- **`sts:TransitiveTagKeys` present** → the tag-propagation surface is
  bounded. Note the allowed tag keys in the REMEDIATION field for review.

This does not change the verdict but appends a warning. Session-tag
injection is a privilege-escalation vector when downstream policies trust
session-set tags for authorization decisions.

### Step 8: Same-account principals — OK

If ALL Allow statements have:

- `Principal.AWS` with ARNs in the **same account** as the role (the account
  ID in the ARN matches the owning account), OR
- `Principal.Service` for a non-confused-deputy-risk service, OR
- No wildcard principals, no `NotPrincipal`, no cross-account ARNs

then classify as **OK**, **LOW**.

**Expert note — same-account root ARN:** `arn:aws:iam::123456789012:root`
where 123456789012 IS the owning account is technically safe in the
trust-policy sense (no external entity can assume the role), but it grants
access to EVERY principal in the account, not just root. This is
acceptable for internal tooling roles but should be flagged for tightening
if the role has privileged permissions — prefer naming the specific role
ARN rather than the account root.

### Step 9: Aggregation

When a trust policy contains multiple statements, the role-level verdict is
the **worst** verdict across all Allow statements, where:

```
WILDCARD_TRUST > EXTERNAL_TRUST > CONDITIONAL > OK
```

A single WILDCARD_TRUST statement makes the entire role WILDCARD_TRUST,
even if all other statements are OK.

## Condition strength matrix

When evaluating a condition block on a wildcard or external Principal,
classify each condition key to determine if it provides real protection:

**STRONG condition keys (→ CONDITIONAL):**

| Key | Operator | Why it is strong |
|---|---|---|
| `sts:ExternalId` | `StringEquals` | Shared secret set by the trusting account; the third party cannot guess or bypass it. The canonical cross-account guard. |
| `aws:SourceAccount` | `StringEquals` | Restricts the calling service to act only on behalf of a specific AWS account. Prevents confused-deputy exploitation. |
| `aws:SourceArn` | `ArnLike` / `ArnEquals` | Restricts to a specific resource ARN — the strongest source-scoping option. Identifies the exact resource making the call. |
| `aws:sourceVpce` | `StringEquals` | VPC Endpoint ID — request must traverse the named endpoint. Not forgeable by the caller. |
| `aws:sourceVpc` | `StringEquals` | VPC ID — request must originate in the named VPC. |
| `SAML:sub` | `StringEquals` | SAML subject — identifies the specific federated user. |
| `SAML:aud` | `StringEquals` | SAML audience — restricts to a specific relying-party trust. |
| `oidc:sub` | `StringEquals` | OIDC subject — identifies the specific federated identity. |
| `oidc:aud` | `StringEquals` | OIDC audience — restricts to a specific client ID. |

**WEAK condition keys (→ still WILDCARD_TRUST or EXTERNAL_TRUST):**

| Key | Operator | Why it is weak |
|---|---|---|
| `aws:SourceIp` | `IpAddress` with `0.0.0.0/0` | The CIDR for the entire internet — zero restriction. Treat as no condition. |
| `aws:SourceIp` | `IpAddress` with public CIDR | Restrictive in theory but bypassable via proxy, VPN, or a compromised host in the CIDR range. |
| `aws:Referer` | `StringLike` / `StringEquals` | HTTP Referer header — trivially forgeable by any HTTP client. Provides NO real access control. |
| `aws:UserAgent` | `StringLike` / `StringEquals` | HTTP User-Agent header — trivially forgeable. Same weakness as Referer. |
| `sts:ExternalId` | `StringLike` with wildcard | Pattern matching weakens the shared secret — if the pattern is guessable, the guard is bypassable. Must use `StringEquals` with an opaque value. |

**MIXED condition blocks:** If a statement has BOTH strong and weak keys
(e.g., `aws:SourceIp` + `aws:SourceAccount`), the strong key dominates —
classify as CONDITIONAL. The weak key is redundant but does not weaken the
strong key.

**ForAllValues / ForAnyValue trap:** `ForAllValues:StringEquals` evaluates
to TRUE when the request contains ZERO matching values. If the tested key is
absent from the request, the condition passes — a known bypass. Use
`ForAnyValue:StringEquals` instead, or add an explicit existence check.
This is especially dangerous with `aws:SourceArn` — if the service does not
populate `aws:SourceArn` for certain call paths, `ForAllValues:aws:SourceArn`
will pass and grant access unexpectedly.

## Risk / severity matrix

The RISK field is derived from the VERDICT and the specific pattern:

| Verdict | Pattern | Risk |
|---|---|---|
| WILDCARD_TRUST | `Principal: "*"` no condition | CRITICAL |
| WILDCARD_TRUST | `Principal: "*"` weak condition only | CRITICAL |
| WILDCARD_TRUST | `NotPrincipal` or `NotAction` | CRITICAL |
| WILDCARD_TRUST | `Principal: "*"` with strong condition | MODERATE (→ CONDITIONAL) |
| EXTERNAL_TRUST | Cross-account root/role without ExternalId | HIGH |
| EXTERNAL_TRUST | Confused-deputy service without source guard | HIGH |
| EXTERNAL_TRUST | SAML/OIDC without condition | HIGH |
| CONDITIONAL | Cross-account with ExternalId | MODERATE |
| CONDITIONAL | Confused-deputy with SourceAccount/SourceArn | MODERATE |
| CONDITIONAL | SAML/OIDC with constrained assertion | MODERATE |
| OK | Same-account scoped | LOW |

**Severity escalation to CRITICAL:** If the role's permissions policy (when
known) grants privileged actions (`iam:*`, `sts:*`, `AdministrativeAccess`),
escalate any EXTERNAL_TRUST or WILDCARD_TRUST finding by one level (HIGH →
CRITICAL, or CRITICAL stays CRITICAL). A role with `Principal: "*"` that
also has `iam:PassRole` permissions is a full account-takeover vector.

## Multi-statement and malformed input handling

- **Iterate every statement** in the trust policy. A role is WILDCARD_TRUST
  if ANY statement matches Steps 1-2. A role is EXTERNAL_TRUST if ANY
  statement matches Steps 3-4 (and no statement is worse).

- **`Effect: Deny` statements** in a trust policy are unusual but valid —
  they prevent the listed principal from assuming the role even if another
  statement allows it. Deny statements narrow the trust surface; they do
  not widen it. Exclude Deny statements from the verdict. If a Deny
  targets `"Principal": "*"`, it blocks ALL assumption — flag as
  potentially over-restrictive but not a security exposure.

- **Multiple `Principal` entries.** A statement can have:
  ```json
  "Principal": {"AWS": ["arn:aws:iam::111:root", "arn:aws:iam::222:root"]}
  ```
  Evaluate EACH entry independently. If any entry is cross-account without
  ExternalId, the statement is EXTERNAL_TRUST.

- **Missing `Action` field.** If an Allow statement has a Principal but no
  Action, the statement is inert (grants nothing). Flag as a
  misconfiguration but do not classify based on it.

- **Action is not `sts:AssumeRole*`.** If the Action is a non-STS action
  (e.g., `s3:GetObject`), the statement is misplaced — trust policies only
  evaluate STS actions. Flag as a misconfiguration and ignore for verdict
  purposes.

- **Malformed JSON.** If the trust policy fails to parse, output
  `VERDICT: ERROR` with a reason citing the parse failure. Do NOT silently
  classify as OK.

## Edge case walkthroughs

Concrete worked examples for the most commonly mis-classified patterns. An
agent should apply these patterns when the classification steps produce an
ambiguous result.

### Edge 1: ForAllValues trap on aws:SourceArn

```json
{
  "Principal": {"Service": "lambda.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "ForAllValues:StringEquals": {
      "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:my-fn"
    }
  }
}
```

**Analysis:** `ForAllValues:StringEquals` evaluates TRUE when the request
contains zero matching values. If Lambda does not populate `aws:SourceArn`
on certain internal code paths (e.g., service-invoked functions, edge
optimizations), the key is absent and the condition passes — granting
access to any caller, including confused-deputy exploitation.

**Verdict:** EXTERNAL_TRUST (Step 4) — the condition is a bypass, not a
guard.

**Remediation:** Replace with `ArnLike` (which requires the key to be
present and match):
```json
"Condition": {"ArnLike": {"aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"}}
```

### Edge 2: Mixed strong + weak condition keys

```json
{
  "Principal": "*",
  "Action": "sts:AssumeRole",
  "Condition": {
    "IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
    "StringEquals": {"aws:SourceAccount": "123456789012"}
  }
}
```

**Analysis:** Two condition operators at the same level are ANDed — both
must be true. `aws:SourceAccount` (STRONG) requires the request to
originate from account 123456789012. `aws:SourceIp` (WEAK for RFC1918)
restricts to a private CIDR. The strong key dominates — classify as
CONDITIONAL. The `aws:SourceIp` is redundant but does not weaken the
strong key.

**Verdict:** CONDITIONAL (Step 2 — wildcard principal with strong condition).

### Edge 3: Multi-statement aggregation — mixed verdicts

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/app-role"},
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
      "Action": "sts:AssumeRole",
      "Condition": {"StringEquals": {"sts:ExternalId": "opaque-id-12345"}}
    },
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Analysis:** Statement 1 is OK (same-account scoped). Statement 2 is
CONDITIONAL (cross-account with ExternalId). Statement 3 is WILDCARD_TRUST
(Principal `"*"` with no condition). Per Step 9 aggregation, the role-level
verdict is the worst: WILDCARD_TRUST.

**Verdict:** WILDCARD_TRUST / CRITICAL.

**Remediation:** Remove Statement 3 immediately (containment). Statement 2
is acceptable if the ExternalId is opaque and rotated on relationship
change. Statement 1 requires no change.

### Edge 4: Role chaining and aws:PrincipalTag ABAC bypass

```json
{
  "Principal": {"AWS": "*"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals": {"aws:PrincipalTag/Team": "data-engineering"}
  }
}
```

**Analysis:** `aws:PrincipalTag/Team` reads the assuming principal's session
tags. If an attacker can assume an intermediate role that allows
`sts:TagSession` with `Team=data-engineering` (role chaining), they inject
the tag and satisfy this condition. The trust policy trusts attacker-
controlled data.

**Verdict:** WILDCARD_TRUST / CRITICAL — the condition is bypassable via
role chaining. `Principal: "*"` gated by `aws:PrincipalTag` is not a
security boundary.

**Remediation:** Replace `Principal: "*"` with a specific account or role
ARN. Do not rely on `aws:PrincipalTag` as the sole guard for wildcard
principals — the tag source must be admin-set (not session-injected) and
the tag-setting roles must themselves be audited for `sts:TagSession`
exposure.

### Edge 5: SAML federated trust with valid vs missing condition

Valid (constrained):
```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRoleWithSAML",
  "Condition": {
    "StringEquals": {
      "SAML:sub": "corp-ad:data-engineering-group",
      "SAML:aud": "https://signin.aws.amazon.com/saml"
    }
  }
}
```
**Verdict:** CONDITIONAL — the IdP controls who can assert, and the
condition narrows the accepted assertions to a specific subject and
audience.

Missing condition (dangerous):
```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRoleWithSAML"
}
```
**Verdict:** EXTERNAL_TRUST — any assertion from the IdP that matches the
provider ARN is accepted. The IdP admin (or anyone who compromises the
IdP) controls access to your AWS role.

### Edge 6: Action-principal mismatch (silent failure)

```json
{
  "Principal": {"Federated": "arn:aws:iam::123456789012:saml-provider/CorpIdP"},
  "Action": "sts:AssumeRole"
}
```

**Analysis:** This statement is invalid. SAML federated principals require
`sts:AssumeRoleWithSAML`, not `sts:AssumeRole`. The combination silently
fails at runtime — no principal can assume the role via this statement. Flag
as a misconfiguration.

**Verdict:** ERROR with reason "Action-principal mismatch:
`sts:AssumeRole` cannot be used with a Federated principal — use
`sts:AssumeRoleWithSAML` for SAML or `sts:AssumeRoleWithWebIdentity` for
OIDC."

## Output format (per role)

```text
ROLE: <name>
VERDICT: EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK
REASON: <1-2 sentences citing the specific statement, the Principal type, and the guard status>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

### Multi-statement aggregation example

```text
ROLE: multi-trust-role
VERDICT: WILDCARD_TRUST
REASON: Statement 1 (Principal: {"AWS": "arn:aws:iam::123456789012:role/internal-app"} on same account) is OK. Statement 2 (Principal: "*" with no condition) is WILDCARD_TRUST — anyone with AWS credentials can assume this role. Role verdict is the worst statement (Step 9 aggregation).
RISK: CRITICAL
REMEDIATION: Remove Statement 2 entirely. If public access was never intended, this is a critical misconfiguration — rotate all credentials exposed via this role immediately and audit CloudTrail for unauthorized AssumeRole events.
```

## Anti-Patterns — NEVER

- NEVER classify a trust policy as OK when `Principal: "*"` or
  `{"AWS": "*"}` appears in any Allow statement without a strong condition.
  This grants the role's entire permission set to any AWS credential holder.
  Cite Step 2.

- NEVER classify `Principal: "*"` with a WEAK condition
  (`aws:SourceIp`, `aws:Referer`, `aws:UserAgent`) as CONDITIONAL. These
  keys are forgeable and provide no real restriction — the verdict is
  WILDCARD_TRUST. This is the inverse mistake of treating every condition
  as protective.

- NEVER assume `arn:aws:iam::ACCOUNT:root` means "only the root user".
  The root ARN expands to EVERY authenticated principal in that account —
  every IAM user, every role, every session. If the intent is a specific
  principal, name it explicitly. This is the most common misunderstanding
  in trust-policy review.

- NEVER classify a confused-deputy-risk service principal
  (`lambda.amazonaws.com`, `ec2.amazonaws.com`, `cloudformation.amazonaws.com`,
  `events.amazonaws.com`, etc.) without `aws:SourceAccount` or
  `aws:SourceArn` as OK. The service can be invoked by ANY AWS customer —
  the correct verdict is EXTERNAL_TRUST. Cite Step 4 and the confused-deputy
  problem above.

- NEVER treat `NotPrincipal` as a scoped grant. `NotPrincipal` is an inverse
  wildcard — it grants access to everyone EXCEPT the listed principal(s).
  In a trust policy this is almost always a catastrophic misconfiguration.
  Classify as WILDCARD_TRUST.

- NEVER treat `ForAllValues:StringEquals` on `aws:SourceArn` as a reliable
  guard. `ForAllValues` evaluates TRUE when the key is absent from the
  request — if the calling service does not populate `aws:SourceArn` on
  certain code paths, the condition passes and grants access. Use
  `ForAnyValue` or an explicit `ArnLike` condition instead.

- NEVER classify a cross-account principal with `sts:ExternalId` in
  `StringLike` with a wildcard pattern (e.g., `"*-prod"`) as CONDITIONAL.
  The wildcard weakens the shared secret — an attacker who guesses the
  suffix bypasses the guard. ExternalId must be opaque and matched with
  `StringEquals`.

- NEVER classify `sts:AssumeRole` with a `Principal.Federated` as valid.
  The Action must be `sts:AssumeRoleWithSAML` (SAML) or
  `sts:AssumeRoleWithWebIdentity` (OIDC). The `sts:AssumeRole` +
  Federated combination silently fails at runtime — flag as a
  misconfiguration.

- NEVER assume the permissions policy is safe just because the trust policy
  is OK. The trust policy controls WHO assumes the role; the permissions
  policy controls WHAT the role can do. Both must be audited. Recommend
  running `iam-least-privilege-advisor` on the role's permissions policy.

- NEVER recommend deleting a trust policy statement without first capturing
  the current policy. Use `aws iam get-role --role-name <name> --query
  Role.AssumeRolePolicyDocument > /tmp/<name>-trust-backup-$(date +%s).json`
  before any modification. Some trust relationships are load-bearing for
  CI/CD pipelines or cross-account monitoring.

- NEVER conflate `aws:SourceAccount` with the trusting (role-owning)
  account. `aws:SourceAccount` identifies the account that the calling
  service is acting ON BEHALF OF — it is the source of the request, not
  the destination. A role in account A with `Principal: {"Service":
  "lambda.amazonaws.com"}` and `aws:SourceAccount: "B"` means "Lambda may
  assume this role only when invoked from account B" — which is a
  cross-account delegation, not a same-account trust.

- NEVER ignore session-tag injection when `sts:TagSession` is allowed
  without `sts:TransitiveTagKeys`. The assuming principal can inject
  arbitrary session tags that propagate to downstream ABAC evaluations,
  potentially bypassing tag-based authorization on resources.

- NEVER trust `aws:PrincipalTag` conditions in a trust policy without
  tracing the tag origin. `aws:PrincipalTag` reads the tags of the
  assuming principal — but if those tags were set by a prior
  `sts:TagSession` call on a different role in the chain (role chaining),
  the tag values are attacker-controlled. ABAC trust policies that gate on
  `aws:PrincipalTag` without verifying that the tag is admin-set (not
  session-injected) are bypassable via role chaining: an attacker assumes
  an intermediate role, sets the expected tag via `sts:TagSession`, then
  assumes the target role with the injected tag satisfying the condition.

- NEVER assume a session policy narrows the trust boundary. The session
  policy (passed during `sts:AssumeRole`) narrows the role's effective
  **permissions**, not its **trust surface**. The trust policy alone
  determines who can attempt assumption. A broad trust policy with
  "the caller will pass a restrictive session policy" is not a security
  control — the caller controls the session policy and can pass an empty
  or permissive one.

- NEVER attempt to remediate a service-linked role's trust policy. Roles
  whose name starts with `AWSServiceRoleFor...` have trust policies
  managed by AWS and cannot be modified via `update-assume-role-policy`.
  Flagging them as remediable wastes the operator's time and may cause
  the remediation CLI to fail silently.

## Pre-flight safety checks (run before any remediation CLI)

- **Confirm the role exists** and capture its current state:
  ```bash
  aws iam get-role --role-name <name> --query Role.AssumeRolePolicyDocument \
    --output json > /tmp/<name>-trust-backup-$(date +%s).json
  ```
  Fail closed (skip remediation) if `get-role` returns an error.

- **Check if the role is a service-linked role** (role name starts with
  `AWSServiceRoleFor...`). Service-linked roles have trust policies managed
  by AWS and CANNOT be modified via `update-assume-role-policy`. Flagging
  them as remediable wastes the operator's time.

- **Check CloudTrail for recent AssumeRole events** on the role before
  restricting trust — an active cross-account trust may be load-bearing
  for a CI/CD pipeline or monitoring integration:
  ```bash
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
    --max-results 50
  ```

- **Prefer additive remediation** (adding a condition) over destructive
  remediation (removing a statement). Adding `aws:SourceAccount` to a
  service-principal statement narrows the trust without breaking it;
  removing the statement may break a production workload immediately.

- **For WILDCARD_TRUST findings** (Principal `"*"`), treat as
  incident-response. The role may have been assumed by unauthorized parties.
  Contain first (restrict the Principal), then investigate (CloudTrail
  AssumeRole events, session activity), then rotate credentials.

## Remediation guidance

### For WILDCARD_TRUST (Principal `"*"` — CRITICAL)

1. **Contain immediately.** Replace `Principal: "*"` with the specific
   principal ARN that needs the role. If the principal is unknown, remove
   the statement entirely — a role that nobody should assume should not
   have a trust policy granting everyone.

2. **Audit CloudTrail.** Search for `AssumeRole` events where the role ARN
   is the target, for the entire window of exposure. Look for `userIdentity`
   entries from unexpected accounts or services.

3. **Rotate credentials.** If the role had access to secrets, KMS keys, or
   data stores, rotate all credentials accessible via the role's permissions
   policy.

### For WILDCARD_TRUST (NotPrincipal / NotAction)

1. Rewrite the statement with an explicit `Principal` allow-list. The
   inverse-wildcard pattern is never correct in a trust policy.

### For EXTERNAL_TRUST (cross-account without ExternalId)

1. **Add an ExternalId condition.** If the cross-account access is
   intentional (e.g., a third-party SaaS integration), add:
   ```json
   "Condition": {
     "StringEquals": {
       "sts:ExternalId": "<opaque-random-string>"
     }
   }
   ```
   The ExternalId should be a cryptographically random string (at least 16
   characters), NOT a human-readable name or a derivable pattern.

2. **If the cross-account access is NOT intentional**, remove the statement.
   The role should not be assumable by external accounts without explicit
   design and a guard.

3. **Tighten the Principal.** If the current Principal is an account-root
   ARN (`arn:aws:iam::ACCOUNT:root`), replace it with the specific role ARN
   the third party uses:
   `arn:aws:iam::ACCOUNT:role/third-party-integration-role`.

### For EXTERNAL_TRUST (confused-deputy without source guard)

1. **Add a source guard condition.** Use `aws:SourceArn` for maximum
   precision, or `aws:SourceAccount` as the minimum:
   ```json
   "Condition": {
     "ArnLike": {
       "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"
     },
     "StringEquals": {
       "aws:SourceAccount": "123456789012"
     }
   }
   ```

2. **Use BOTH `aws:SourceArn` and `aws:SourceAccount`** for
   defense-in-depth. `SourceArn` scopes to a specific resource;
   `SourceAccount` is a fallback if the service does not populate
   `SourceArn` on all code paths.

### For CONDITIONAL (cross-account with ExternalId)

1. **Verify the ExternalId rotation policy.** The ExternalId should be
   rotated when the third-party relationship changes (vendor switch,
   contract renewal). It should NOT be rotated frequently (it is a
   shared secret, not a credential) — but it MUST be changed if compromised.

2. **Verify the ExternalId is opaque.** It must be a random string, not
   a guessable pattern. If it reads like a company name, project code, or
   sequential ID, rotate it.

### For CONDITIONAL (confused-deputy with source guard)

1. **Verify the source account/resource ARN is still correct.** If the
   source resource was deleted and recreated (e.g., a Lambda function
   recreated after an IaC teardown), the ARN may have changed.

2. **Consider adding a permissions boundary** on the role to cap the
   maximum effective permissions, as a defense-in-depth measure.

### For OK

1. No remediation required for trust-policy exposure.

2. **Recommend running `iam-least-privilege-advisor`** on the role's
   permissions policy — a clean trust policy with an over-permissive
   permissions policy is still a security risk.

3. For same-account root ARN principals, recommend tightening to the
   specific role ARN if the role has privileged permissions.

## Effective trust boundary (expert note)

The trust policy is necessary but not sufficient for role assumption. AWS
evaluates role assumption in this order:

1. **Trust policy** (AssumeRolePolicyDocument) — must explicitly Allow the
   principal + action + (optional) condition. This is the first gate.

2. **Identity-based policy of the assuming principal** — the principal's
   own policy must also Allow `sts:AssumeRole` on the role's ARN. For
   same-account access, EITHER the trust policy OR the identity policy can
   allow (union). For cross-account, BOTH must allow (intersection).

3. **SCP (Service Control Policy)** — if the assuming principal's account
   is in an Organization, an SCP Deny blocks the assumption regardless of
   the trust policy.

4. **Session policy** — if the role was assumed via a chained AssumeRole
   with a session policy, the effective permissions are the INTERSECTION of
   the role's policy and the session policy. The trust boundary, however,
   is determined by the trust policy alone.

**Classification implication:** the trust policy is the widest boundary.
Even if the assuming principal's identity-based policy is scoped down, a
broad trust policy means any future principal in the trusted account (or
any future service invocation) can attempt assumption. The trust policy
must be scoped independently of the assuming principal's permissions.

### Role chaining and tag propagation

Role chaining — assuming Role A, then from Role A's session assuming Role B
— creates a trust chain where each hop's trust policy is evaluated
independently. Key expert insights:

- **`aws:PrincipalType`**: distinguishes the principal type of the assuming
  entity. `AssumedRole` means the caller is already an assumed-role session
  (role chaining). `User` means an IAM user. `Service` means an AWS service.
  Use this in conditions to block role-chaining attacks: e.g., require
  `"aws:PrincipalType": "Service"` for a service-role trust to prevent
  user/session assumption.

- **Session tag propagation**: if Role A's trust policy allows
  `sts:TagSession`, the assuming principal can set tags that propagate to
  the Role A session. If Role B's trust policy gates on `aws:PrincipalTag`,
  the attacker who controls the tags on Role A satisfies Role B's condition.
  This is the **session-tag ABAC bypass** — the most subtle trust-policy
  vulnerability. To detect it: audit whether any role in the chain allows
  `sts:TagSession` without `sts:TransitiveTagKeys`, and whether any
  downstream role trusts `aws:PrincipalTag` conditions.

- **`maxSessionDuration` interaction**: the role's `maxSessionDuration`
  property (NOT in the trust policy — it is a separate role attribute) caps
  the session length. A long duration (up to 43200 seconds / 12 hours) means
  a compromised session persists longer. This is not a trust-policy finding,
  but it affects the blast radius of any trust-policy misconfiguration: a
  WILDCARD_TRUST role with a 12-hour session duration gives an attacker a
  12-hour persistent credential.

### Permissions boundary on the trusted role

A permissions boundary on the role being assumed caps the role's effective
permissions (the intersection of the identity-based policy and the boundary).
This is a defense-in-depth measure: even if the trust policy is broad and the
permissions policy is over-permissive, a tight boundary limits what an
attacker who assumes the role can actually do. Recommend adding a permissions
boundary to any role classified as EXTERNAL_TRUST or WILDCARD_TRUST as an
interim containment measure while the trust policy is being remediated.

## Recent AWS features (2024-2026)

- **STS session tagging (2024-2025):** STS now supports passing session tags during AssumeRole, enabling attribute-based access control. Auditors should verify that cross-account trust policies that accept session tags use `aws:RequestTag` conditions to constrain which tags can be assumed — an unconstrained session tag policy can be abused to bypass ABAC controls.
- **External ID enforcement improvements (2024):** Enhanced confused-deputy protection guidance and API validation. Auditors should verify that all cross-account trust policies for third-party (SaaS vendor) roles include a strong `sts:ExternalId` condition — this remains the primary defense against confused-deputy attacks.
- **IAM Access Analyzer integration with STS (2024):** Access Analyzer now flags cross-account trust policies that allow assumption without conditions. Auditors should cross-reference STS trust policy analysis with Access Analyzer external-access findings.
- **Role chaining detection (2024-2025):** Enhanced CloudTrail logging for role chaining (AssumeRole followed by AssumeRole). Auditors should verify that role-chaining patterns (A assumes B which assumes C) are documented and that the effective trust boundary includes all intermediary roles.

## References

See `references/trust-policy-hardening-guide.md` for the confused-deputy
service-principal reference table, the ExternalId generation snippet,
the `aws:SourceArn` vs `aws:SourceAccount` decision tree, and
copy-pasteable remediation commands for each verdict.

## Section taxonomy (CloudOps auditor pattern)

This skill follows the CloudOps auditor skill pattern, with sections in
this canonical order:

1. **Frontmatter** — name, description, version, metadata.
2. **Mindset** — the auditor's frame: trust boundary, not permissions.
3. **Quick reference** — one-paragraph decision summary.
4. **Confused-deputy problem** — the core expert concept.
5. **Classification logic** — the ordered decision tree (Steps 0-9).
6. **Condition strength matrix** — strong vs weak keys.
7. **Risk / severity matrix** — verdict + pattern → risk level.
8. **Edge-case handling** — multi-statement, Deny, malformed input.
9. **Output format** — the fixed per-role report shape.
10. **NEVER** — anti-patterns with explicit reasoning.
11. **Pre-flight safety checks** — non-destructive operation guards.
12. **Remediation guidance** — per-verdict action plan.
13. **References** — pointer to deeper references.

## Domain

AWS CloudOps / STS & IAM Trust-Policy Security.
