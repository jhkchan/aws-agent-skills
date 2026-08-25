---
name: sts-cross-account-role-auditor
description: 'Audits IAM role trust policies (AssumeRolePolicyDocument) for cross-account exposure, wildcard Principal grants, confused-deputy service-principal vectors, and condition-strength weaknesses. Emits a deterministic EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK verdict per role with severity and remediation. Use when reviewing IAM role trust policies, checking who can assume a role, auditing cross-account access, validating ExternalId or SourceArn guards, or hardening role trust before production. Triggers: STS, AssumeRole, trust policy, AssumeRolePolicyDocument, cross-account, ExternalId, confused deputy, Principal AWS root, Principal Service, Principal star, SAML federated, SourceArn, SourceAccount, NotPrincipal, role trust audit, role assumption exposure.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline trust-policy classification. Live account audits use aws iam get-role --query Role.AssumeRolePolicyDocument and aws iam list-roles (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: sts, iam, security, trust-policy, cross-account, external-id, confused-deputy, role-audit
  dependencies: aws-orchestrator
  keywords: STS, trust policy, AssumeRole, AssumeRolePolicyDocument, cross-account, ExternalId, confused deputy, Principal, wildcard principal, role trust, SAML, OIDC, federated, SourceArn, SourceAccount, NotPrincipal, role assumption, IAM audit, security
  when_to_use: Reviewing an IAM role trust policy (AssumeRolePolicyDocument), auditing who can assume a role, checking cross-account or external access exposure, validating ExternalId / SourceArn / SourceAccount guards, hardening a service-role trust before production, or investigating confused-deputy attack surface.
---

# STS Cross-Account Role Auditor

## Mindset

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset).
> One-line: classify WHO can assume the role (trust policy, not permissions policy); catch wildcard `"*"`, unguarded cross-account root, and unguarded confused-deputy service principals; grade condition strength.

## What this skill is NOT

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#what-this-skill-is-not).
> Scope: trust policy only — permissions-policy audits belong to iam-least-privilege-advisor; run both when the permissions policy is available.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#the-confused-deputy-problem-core-concept).
> Core: Principal.Service trusts the SERVICE, not your resources — any AWS customer can trigger it; fix with aws:SourceAccount (StringEquals, minimum) or aws:SourceArn (ArnLike, strongest).

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


> Expert note moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-note--the-root-arn-expansion-rule).
> Root ARN expansion: `arn:aws:iam::ACCOUNT:root` = EVERY authenticated principal in that account, not just root — name the specific role ARN.

### Step 4: Confused-deputy service Principal without source guard

If ANY Allow statement has `Principal.Service` set to a
**confused-deputy-risk service** (see list below) and the `Condition` block
does NOT contain `aws:SourceAccount` or `aws:SourceArn`, classify as
**EXTERNAL_TRUST**, **HIGH**.


> Service catalogs moved to [references/trust-policy-hardening-guide.md](references/trust-policy-hardening-guide.md#confused-deputy-risk-service-principal-catalogs-moved-from-skillmd).
> High-risk: lambda, ec2, cloudformation, eks/ecs, states, events/pipes, sns/sqs, codebuild/codepipeline, apigateway, backup, cloudtrail, config, controltower, security services, waf, firehose/es/aoss, bedrock. Lower-risk: awslambda (legacy), dynamodb, ds, ssm, transfer, quicksight.

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


> Expert note moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-note--same-account-root-arn).
> Same-account `:root` is safe externally but grants EVERY principal in the account — prefer naming the specific role ARN for privileged roles.

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

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#multi-statement-and-malformed-input-handling).
> Rules: worst statement wins; Deny statements narrow (exclude from verdict); evaluate EACH Principal entry; missing Action = inert; non-STS Action = misplaced; unparseable → VERDICT: ERROR.

## Edge case walkthroughs

> Moved to [references/worked-examples.md](references/worked-examples.md#edge-case-walkthroughs).
> Six worked edges: ForAllValues trap on aws:SourceArn, mixed strong+weak keys, multi-statement aggregation, aws:PrincipalTag role-chaining bypass, SAML valid vs missing condition, Action-principal mismatch.

## Output format (per role)

```text
ROLE: <name>
VERDICT: EXTERNAL_TRUST | WILDCARD_TRUST | CONDITIONAL | OK
REASON: <1-2 sentences citing the specific statement, the Principal type, and the guard status>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required" if OK>
```

### Multi-statement aggregation example

> Moved to [references/worked-examples.md](references/worked-examples.md#multi-statement-aggregation-example).
> Full WILDCARD_TRUST / CRITICAL report for a mixed three-statement trust policy (Step 9 aggregation).

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

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-remediation-cli).
> Gates: back up the trust policy (get-role), service-linked-role check, CloudTrail AssumeRole lookup before restricting trust, prefer additive remediation, treat WILDCARD_TRUST as incident response.

## Remediation guidance

> Moved to [references/trust-policy-hardening-guide.md](references/trust-policy-hardening-guide.md#remediation-guidance-moved-from-skillmd).
> Per-verdict playbooks: WILDCARD_TRUST (contain → audit CloudTrail → rotate), EXTERNAL_TRUST (add opaque ExternalId / SourceArn+SourceAccount, tighten Principal), CONDITIONAL (verify ExternalId opacity + rotation, verify ARN still correct), OK (recommend iam-least-privilege-advisor).

## Effective trust boundary (expert note)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#effective-trust-boundary-expert-note).
> Full evaluation order (trust policy → identity policy → SCP → session policy), role chaining + session-tag ABAC bypass, maxSessionDuration blast radius, and permissions-boundary containment.

## Recent AWS features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026).
> STS session tagging, ExternalId enforcement guidance, Access Analyzer cross-referencing, role-chaining CloudTrail detection.

## References

See `references/trust-policy-hardening-guide.md` for the confused-deputy
service-principal reference table, the ExternalId generation snippet,
the `aws:SourceArn` vs `aws:SourceAccount` decision tree, and
copy-pasteable remediation commands for each verdict.

## Section taxonomy (CloudOps auditor pattern)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#section-taxonomy-cloudops-auditor-pattern).
> The 13-section canonical CloudOps auditor layout this skill follows.


## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — Mindset, scope note, the confused-deputy concept, root-ARN expansion, multi-statement/malformed handling, effective trust boundary + role chaining, Recent AWS features, and section taxonomy moved from SKILL.md
- [worked-examples](references/worked-examples.md) — the six edge-case walkthroughs and the multi-statement aggregation example moved from SKILL.md
- [diagnostic-commands](references/diagnostic-commands.md) — pre-flight safety checks (trust-policy backup, service-linked-role check, CloudTrail lookup) moved from SKILL.md
- [trust-policy-hardening-guide](references/trust-policy-hardening-guide.md) — now also holds the confused-deputy service-principal catalogs and the per-verdict remediation guidance moved from SKILL.md

## Domain

AWS CloudOps / STS & IAM Trust-Policy Security.

## AWS documentation

- **AWS STS User Guide (temporary security credentials)** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html
- **IAM Security Best Practices** — https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- **STS API Reference** — https://docs.aws.amazon.com/STS/latest/APIReference/
- **AWS CLI STS Command Reference** — https://docs.aws.amazon.com/cli/latest/reference/sts/
- **Confused deputy problem** — https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html
- **Session tags** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_session-tags.html
