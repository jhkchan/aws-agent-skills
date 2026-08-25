# Advanced Patterns — STS Cross-Account Role Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Expert note — the root ARN expansion rule

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

## Expert note — same-account root ARN

**Expert note — same-account root ARN:** `arn:aws:iam::123456789012:root`
where 123456789012 IS the owning account is technically safe in the
trust-policy sense (no external entity can assume the role), but it grants
access to EVERY principal in the account, not just root. This is
acceptable for internal tooling roles but should be flagged for tightening
if the role has privileged permissions — prefer naming the specific role
ARN rather than the account root.

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
