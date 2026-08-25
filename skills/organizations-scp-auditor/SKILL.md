---
name: organizations-scp-auditor
description: Audits AWS Organizations Service Control Policies (SCPs) for effective permission boundaries across the OU hierarchy — FullAWSAccess inheritance, deny-list guardrails (LeaveOrganization, security-service disruption, region restriction), account-level overrides, and silently ineffective conditions from unsupported SCP condition keys. Emits a deterministic verdict (PERMISSIVE_SCP | MISSING_GUARDRAIL | CONFIG_GAP | OK) per target account with enumerated findings and specific remediation. Use when reviewing SCPs, checking OU hierarchy guardrails, auditing effective permissions, validating deny-list strategy, or hardening organization-level security posture.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline SCP-document classification. Live-account audits use aws organizations list-policies-for-target, describe-policy, list-roots, and list-accounts-for-parent (AWS CLI v2, SSO or key-based credentials, management account or delegated administrator).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  verdict_shape: PERMISSIVE_SCP | MISSING_GUARDRAIL | CONFIG_GAP | OK
  when_to_use: Reviewing SCPs before attaching to production OUs, checking effective permissions across the OU hierarchy, auditing deny-list guardrails, validating FullAWSAccess strategy, inspecting account-level SCP overrides, or hardening organization-level security posture.
  activation_triggers: audit these SCPs, check SCP guardrails, effective permissions for this OU, is LeaveOrganization denied, FullAWSAccess strategy, SCP deny-list review, OU hierarchy security, organization guardrail audit
  invocation_schema: 'Input: either (a) an SCP policy document JSON plus OU hierarchy context (root -> OU -> account chain with attached SCPs at each level), OR (b) a target ID (root/OU/account) for live-account effective-SCP audit. Output: deterministic TARGET/VERDICT/REASON/FINDINGS/REMEDIATION block per target, where VERDICT in {PERMISSIVE_SCP, MISSING_GUARDRAIL, CONFIG_GAP, OK, ERROR}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Organizations, SCP, Service Control Policy, OU hierarchy, FullAWSAccess, deny-list, allow-list, LeaveOrganization, aws:RequestedRegion, guardrail, management account, account-level override, effective permissions, policy inheritance, organizational unit
  tags: organizations, scp, governance, guardrail, ou-hierarchy, policy-inheritance, audit
---

# Organizations SCP Auditor

## Mindset

**Core principle:** SCPs never grant access — they only filter. The
verdict is always the **worst** finding across the effective-SCP chain.

An SCP sets the **maximum permission boundary** for every account in an
OU — it is the ceiling, not the floor. Three concepts are routinely
misunderstood (full detail in Step 0):

- **FullAWSAccess** is a mode switch, not a safety net.
- **Deny** is absolute across the entire hierarchy — no Allow overrides it.
- **Service-specific condition keys** are silently unsupported — the Deny
  is dead.

## Quick reference — verdict thresholds

> **SCP-AUDIT framework map:** Mindset (triage) → Quick reference
> (verdict lookup) → Pre-flight (context gate) → Process (deep audit)
> → Output → Edge cases → Anti-Patterns → Remediation. Skim top for
> fast triage; descend into Process for full classification.

| Condition | Verdict | Step |
|---|---|---|
| FullAWSAccess detached + no Allow SCP replacement at target | CONFIG_GAP | 1a |
| SCP Deny uses service-specific condition key (silently dead) | CONFIG_GAP | 1b |
| Empty SCP / SCP attached to management account (wasted quota) | CONFIG_GAP | 1c |
| `organizations:LeaveOrganization` not denied in effective hierarchy | PERMISSIVE_SCP | 2a |
| Security-service disruption not denied (GuardDuty / SH / Config / CT) | PERMISSIVE_SCP | 2b |
| Root credential actions not restricted (`iam:*AccessKey` on root) | PERMISSIVE_SCP | 2c |
| Destructive IAM allowed in sensitive OU without Deny guardrail | PERMISSIVE_SCP | 2d |
| No region-restriction Deny (`aws:RequestedRegion`) for in-scope acct | MISSING_GUARDRAIL | 3a |
| No tag-based access control for sensitive resource types | MISSING_GUARDRAIL | 3b |
| All critical guardrails present + no permissive allows + no gaps | OK | 4 |

Deep SCP evaluation internals are in the
[Deep reference](#scp-audit-phase-7--deep-reference-scp-evaluation-internals)
at the end. Condition key support table is in the
[Condition key reference](#condition-key-reference-scp-specific) —
only `aws:` global keys work in SCPs; service-specific keys are dead.

## Pre-flight: organizational context gate (run before classification)

**Live-account pre-flight (skip for offline SCP-doc audit):**

1. Verify the caller can run `organizations:DescribeOrganization` and
   `organizations:ListPoliciesForTarget` — member-account auditors often
   CANNOT. Use the management account or a delegated administrator.
2. Confirm SCPs are enabled: `aws organizations describe-organization`
   and verify `Policies -> SUPPORTED` for `SERVICE_CONTROL_POLICY`. If
   SCPs are not enabled, NO attached SCP takes effect.
3. SCPs are **eventually consistent** — after attach/detach, effective
   permissions may lag several minutes. Re-audit after 5 minutes if
   `LastConmodifiedTimestamp` is recent.
4. For orgs with >50 accounts, paginate with `--next-token` on
   `list-accounts-for-parent` and `list-children` to enumerate all
   OUs. The Organizations API throttles at ~1 req/s — implement
   exponential backoff on `TooManyRequestsException`.

**Error branching for live API calls:**

| API error | Meaning | Action |
|---|---|---|
| `AccessDeniedException` | Caller lacks `organizations:*` permissions | Switch to management account or delegated admin |
| `AWSOrganizationsNotInUseException` | Org not created | SCPs do not apply — report as N/A |
| `PolicyTypeNotEnabledException` | SCPs not enabled for the org | Enable via `enable-policy-type --service-control-policy` |
| `TooManyRequestsException` | Throttled (~1 req/s limit) | Exponential backoff, retry after 2s/4s/8s |
| `TargetNotFoundException` | OU/account ID is wrong or deleted | Verify ID in `list-roots` / `list-organizational-units` |

| Target type | Effect |
|---|---|
| Management account | **Exempt from SCPs.** Attached SCPs have zero effect — flag as CONFIG_GAP (wasted quota). |
| Root | SCPs apply to all OUs and accounts. Root is not itself an account. |
| OU | SCPs apply to the OU and all descendants (inheritance). |
| Member account | SCPs apply to that account only (account-level override layer). |

If any SCP policy JSON is malformed (invalid JSON, missing `Statement`),
emit an ERROR note for that policy and skip it in the effective-SCP
evaluation. Do NOT mark the entire target as ERROR when one SCP is
broken — valid SCPs may still produce findings.

**Offline audit input shape** (minimum viable structure the agent
expects when no live API is available):

```json
{
  "target": "111111111111",
  "hierarchy": [
    {"level": "root", "id": "r-xxx", "scps": [{"Name": "FullAWSAccess", "Type": "Allow", "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]}]},
    {"level": "ou", "id": "ou-prod-xxx", "parent": "r-xxx", "scps": []},
    {"level": "account", "id": "111111111111", "parent": "ou-prod-xxx", "scps": []}
  ],
  "context": {"handles_regulated_data": true}
}
```

Key fields: `hierarchy` is root-to-account chain; each `scps[]` entry
has `Effect`, `Action`/`NotAction`, `Resource`, optional `Condition`.
The `context` block flags OU sensitivity for MISSING_GUARDRAIL checks.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious SCP behaviors that change classification

- **SCPs never grant access.** An Allow `*` SCP means "the SCP layer
  does not restrict this action." The actual permission still requires
  an IAM identity-based Allow. Do NOT treat an SCP Allow `*` as a
  permission grant — it is a filter pass-through.

- **FullAWSAccess is a mode switch, not a policy.** Detaching it from
  the ROOT without a replacement Allow SCP blocks every action in every
  member account — the most catastrophic Organizations misconfiguration.
  Detaching from an OU only removes the OU-level copy; the root's
  FullAWSAccess still inherits through.

- **SCP inheritance is a UNION.** All SCPs from root through every
  parent OU to the target combine. None shadow or replace others. A
  target with FullAWSAccess at root + 3 Deny SCPs at a parent OU has
  4 effective SCPs.

- **Deny is ABSOLUTE across the SCP layer.** A Deny at root cannot be
  overridden by an Allow at the account level. There is no "more
  specific Allow overrides broader Deny" — that is an IAM concept.

- **The 5-SCP quota per target is HARD.** Root, each OU, and each
  account can have at most 5 SCPs attached. FullAWSAccess counts. At
  quota, you cannot add guardrails without removing existing SCPs.

- **The management account is EXEMPT from SCPs.** SCPs do not affect
  the management account — not even root-level SCPs. An SCP attached to
  the management account has zero effect and wastes a quota slot.

- **Service-specific condition keys are SILENTLY UNSUPPORTED.** SCPs
  support only `aws:` global condition keys (`aws:RequestedRegion`,
  `aws:ResourceTag/tag-key`, `aws:PrincipalTag/tag-key`,
  `aws:PrincipalOrgID`, `aws:PrincipalOrgPaths`). Service-specific keys
  (`kms:ViaService`, `s3:prefix`, `ec2:ResourceTag/tag-key`) are NOT
  available in the SCP evaluation context. A Deny using `kms:ViaService`
  with `StringEquals` always evaluates FALSE — the Deny never applies.
  The guardrail is a dead statement.

- **`aws:RequestedRegion` does NOT apply to global services.** IAM,
  Organizations, Route53, CloudFront, WAF, Support — these have no
  region. A region-restriction SCP must use `NotAction` to exclude them,
  or it blocks legitimate global API calls.

- **`organizations:LeaveOrganization` is the SCP kill-switch.** If not
  denied, any account admin can leave the org — instantly escaping ALL
  SCPs. Deny this at ROOT level so it covers every account.

- **`NotAction` in a Deny SCP is a footgun.** `Deny` + `NotAction:
  ["s3:*"]` denies ALL actions except S3 — blocking IAM, EC2, Lambda,
  everything. This is the inverse of "allow only S3." Flag as
  CONFIG_GAP until verified intentional.

- **SCPs block break-glass access.** An SCP denying `iam:*` or
  `sts:AssumeRole` blocks ALL IAM operations including break-glass
  incident-response roles. Recommend a `Condition`-based escape hatch
  (e.g., `StringNotEquals` on `aws:PrincipalTag/break-glass`) so
  responders are not locked out during a security event.

- **`aws:RequestedRegion` breaks multi-region data-plane services.**
  S3 cross-region replication, DynamoDB global tables, and Aurora
  global databases make internal cross-region API calls that a region
  SCP silently breaks — replication fails without `AccessDenied`.
  Exclude data-plane actions for multi-region services via `NotAction`
  alongside global-service exclusions.

- **`aws:PrincipalOrgPaths` requires the full org-root path.** The
  condition value must match the complete path from the organization
  root: `o-xxxxxxxxxx/r-xxxxxxxx/ou-xxxx-xxxx/ou-yyyy-yyyy/`. Using
  only the OU ID without the org-root prefix silently never matches —
  the SCP appears attached but provides no OU scoping. Validate the
  full path string before relying on OU-level targeting.

- **SCP evaluation comes BEFORE resource-based policies in the request
  pipeline.** If an SCP Denies, S3 bucket policies and IAM
  resource-based grants never get a chance to allow the request. An
  SCP that restricts cross-account S3 access overrides any permissive
  bucket policy — the bucket policy is irrelevant if the SCP blocks
  first.

### Step 1: CONFIG_GAP — structural SCP misconfiguration (highest severity)

**1a — FullAWSAccess detached without Allow replacement.** If
FullAWSAccess is NOT in the effective SCP set AND no other Allow `*`
(or broad-enough Allow) SCP exists in the chain, the target has ZERO
effective permissions at the SCP layer. Every IAM Allow is filtered
out — uniform `AccessDenied` across all services. Check FIRST.

**1b — Deny using unsupported service-specific condition key.** Any
Deny using a condition key outside the SCP-supported set (only `aws:`
global keys) is silently dead. With `StringEquals`, the Deny never
applies (zero protection). With `StringNotEquals`, it may always apply
(over-block). The SCP does not behave as written.

**1c — Inert SCP.** Zero statements, or attached to the management
account (SCP-exempt). Wastes a quota slot, produces no effect.

### Step 2: PERMISSIVE_SCP — dangerous actions allowed (second severity)

**2a — `organizations:LeaveOrganization` not denied.** Highest priority
PERMISSIVE_SCP — leaving the org escapes ALL SCPs instantly.

**2b — Security-service disruption not denied.** If no Deny blocks
`guardduty:DeleteDetector`, `securityhub:DisableSecurityHub`,
`config:DeleteConfigurationRecorder`, `cloudtrail:DeleteTrail`, an
attacker can blind detection before exfiltrating.

**2c — Root credential actions not restricted.** If no Deny blocks
`iam:CreateAccessKey`, `iam:DeleteAccessKey`,
`iam:UpdateLoginProfile` for the root principal.

**2d — Destructive IAM in sensitive OU.** If the target is in an OU
designated production/sensitive and no Deny blocks `iam:DeleteRole`,
`iam:DeleteRolePolicy`, `iam:DetachRolePolicy`, `iam:CreateUser`.

### Step 3: MISSING_GUARDRAIL — recommended guardrails absent (third severity)

**3a — No region-restriction Deny.** Target handles regulated/sensitive
data and no SCP uses `aws:RequestedRegion` to restrict to approved
regions. Data can deploy to any region globally.

**3b — No tag-based access control.** Target manages ABAC-governed
resources and no SCP uses `aws:ResourceTag` for tag enforcement.

### Step 4: OK — all guardrails present

No CONFIG_GAP, PERMISSIVE_SCP, or MISSING_GUARDRAIL findings. Posture
is sound.

### Step 5: Aggregation — worst finding wins

```text
verdict = max(all_config_gaps, all_permissive_scps, all_missing_guardrails, OK)
```

Severity: CONFIG_GAP > PERMISSIVE_SCP > MISSING_GUARDRAIL > OK.

## Output format (per target)

```text
TARGET: <account-id or OU-id or root-id>
VERDICT: PERMISSIVE_SCP | MISSING_GUARDRAIL | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [CONFIG_GAP] <finding description (Step 1a)>
  - [PERMISSIVE_SCP] <finding description (Step 2a)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — missing LeaveOrganization deny

```text
TARGET: 111111111111 (permissive-scp-no-leave-deny-workload)
VERDICT: PERMISSIVE_SCP
REASON: No Deny SCP in the effective hierarchy blocks
organizations:LeaveOrganization — any account admin can detach from
the org and instantly escape all SCP protection (Step 2a).
FINDINGS:
  - [PERMISSIVE_SCP] organizations:LeaveOrganization not denied (Step 2a)
    — SCP kill-switch: escaping the org removes ALL SCP guardrails
  - [PERMISSIVE_SCP] Security-service disruption not denied (Step 2b)
    — guardduty:DeleteDetector, securityhub:DisableSecurityHub not blocked
  - [OK] FullAWSAccess present at root (deny-list mode active)
REMEDIATION:
  1. Attach a Deny SCP at root: aws organizations create-policy --type
     SERVICE_CONTROL_POLICY --name DenyLeaveOrg --content file://deny-leave.json
  2. Extend to block security-service disruption actions.
```

## Edge-case handling

- **Partially malformed SCP.** Classify valid SCPs normally; emit ERROR
  for the malformed one. Do NOT mark the entire target ERROR when one
  SCP is broken.

- **FullAWSAccess present at root but detached at OU.** The root's
  FullAWSAccess is inherited through the OU — detaching at OU only
  removes the local copy. Only detaching from ROOT is catastrophic.

- **Conflicting Deny and Allow within the SCP layer.** An Allow at the
  account level does NOT override a Deny at root. But a Deny using an
  unsupported condition key (Step 1b) silently never applies — so the
  Allow is effectively unchallenged. Evaluate condition-key support
  BEFORE treating the Deny as effective.

- **SCP `Resource` scoped to a specific ARN.** SCP `Resource` is
  effectively always `"*"` — a scoped `Resource` is accepted by the API
  but does not narrow the SCP's effect. Evaluate `Action`/`NotAction` +
  `Condition` only.

- **Empty effective-SCP set.** If NO SCPs are attached to a target or
  any ancestor, the target has zero effective permissions at the SCP
  layer — CONFIG_GAP (Step 1a).

## Anti-Patterns — NEVER

- NEVER treat an SCP Allow `*` as a permission grant. SCPs only filter.
  The actual grant requires an IAM identity-based Allow.

- NEVER assume a Deny at a child OU overrides an Allow at root. Denies
  are absolute across all SCP levels — an Allow at the OU does NOT
  override a Deny at root.

- NEVER assume the management account is protected by SCPs. It is
  exempt. An SCP attached to it has zero effect and wastes a quota slot.

- NEVER treat a service-specific condition key as effective in an SCP.
  `kms:ViaService`, `s3:prefix`, `ec2:ResourceTag` are dead in SCPs —
  the Deny silently never matches. Flag as CONFIG_GAP (Step 1b).

- NEVER treat `aws:RequestedRegion` as a complete region lock. It does
  not apply to global services (IAM, Organizations, Route53, CloudFront,
  WAF, Support). A region SCP MUST exclude these via `NotAction`.

- NEVER assume detaching FullAWSAccess from an OU breaks all access. If
  root still has FullAWSAccess, the root copy inherits through. Only
  detaching from ROOT is catastrophic.

- NEVER assume an SCP with `Resource` scoped to a specific ARN narrows
  effect. SCP `Resource` is effectively always `"*"`.

- NEVER leave `organizations:LeaveOrganization` un-denied. An account
  admin can leave the org and escape ALL SCPs instantly. Deny at ROOT.

- NEVER treat a Deny with `NotAction` as a narrow guardrail. `Deny` +
  `NotAction: ["s3:*"]` blocks everything except S3. Flag as CONFIG_GAP.

- NEVER rely on a wildcard Deny with a Condition as a precision tool.
  `Deny` + `Action: "*"` + `Condition` blocks every action matching the
  condition with no service narrowing. If the condition key is
  unsupported (Step 1b) or the value is wrong, the blast radius is
  every action in the account. Prefer `Action`-scoped Denies with
  conditions over `Action: "*"` + `Condition`.

- NEVER exceed 5 SCPs per target. The quota is hard and includes
  FullAWSAccess. Surface quota before recommending additive SCPs.

- NEVER evaluate only the target's directly-attached SCPs. SCPs inherit
  through the entire chain (root -> every parent OU -> account). Always
  evaluate the FULL effective chain.

- NEVER assume SCP changes are immediately effective. They are
  eventually consistent — re-audit after 5 minutes.

- NEVER edit an SCP without a backup — SCPs are NOT versioned. The
  Organizations API overwrites the policy content with no history or
  rollback. CloudTrail logs the `UpdatePolicy` API call but does not
  capture the prior content. Always `describe-policy` to a file before
  editing.

- NEVER use `NotAction` in a Deny statement as a whitelist. `Deny` +
  `NotAction` inverts the logic: every action NOT listed is denied.
  Two SCPs with `NotAction` do not compose — each blocks whatever the
  other allows. Consolidate into a single scoped `Action` Deny.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing SCP
  operation, emit: `CONFIRM: About to <action> on SCP <policy-id> for
  target <target-id>. This affects <consequence>. Proceed? (yes/no)`.
  SCP changes affect every account in the target's subtree.

- **Back up current SCP:**
  `aws organizations describe-policy --policy-id <id> --output json >
  /tmp/scp-<id>-backup-$(date +%s).json`
  SCP changes are not versioned — no undo without a backup.

- **Verify target scope.** Detaching FullAWSAccess from ROOT affects
  every account. Confirm `TargetId` matches the intended target.

- **Check SCP quota:**
  `aws organizations list-policies-for-target --target-id <id>
  --filter SERVICE_CONTROL_POLICY`
  At 5 SCPs, attach fails with `PolicyLimitExceededException`.

- **Prefer additive Deny SCPs** (create + attach) over modifying
  existing SCPs. Additive changes are reversible; policy-text edits
  are not versioned.

- **For CONFIG_GAP (FullAWSAccess detached), do NOT re-attach without
  understanding WHY.** The org may have intentionally moved to
  allow-list mode. Confirm with the org owner before reverting.

## Remediation guidance

### For CONFIG_GAP — FullAWSAccess detached (Step 1a)

1. Determine whether detachment was intentional (allow-list) or
   accidental. If accidental: `aws organizations attach-policy
  --policy-id p-FULLAWSACCESS --target-id <id>`. If intentional:
   create and attach a replacement Allow SCP.
2. Verify: `aws organizations list-policies-for-target --target-id <id>
   --filter SERVICE_CONTROL_POLICY`

### For CONFIG_GAP — unsupported condition key (Step 1b)

1. Replace the service-specific key with the SCP-supported equivalent:
   `ec2:ResourceTag/tag-key` -> `aws:ResourceTag/tag-key`. For keys
   with no SCP equivalent (`kms:ViaService`, `s3:prefix`), remove the
   condition or restructure the Deny without a condition.
2. Re-evaluate the Deny after the fix to confirm it applies.

### For PERMISSIVE_SCP — LeaveOrganization (Step 2a)

Create and attach a Deny SCP at ROOT:
```json
{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"}]}
```

### For PERMISSIVE_SCP — security-service disruption (Step 2b)

Extend the root Deny SCP to include: `guardduty:DeleteDetector`,
`securityhub:DisableSecurityHub`,
`config:DeleteConfigurationRecorder`, `cloudtrail:DeleteTrail`.

### For MISSING_GUARDRAIL — no region restriction (Step 3a)

Create a region-restriction Deny using `aws:RequestedRegion`. **MUST**
exclude global services via `NotAction`:
```json
{"Sid":"DenyNonApprovedRegions","Effect":"Deny","NotAction":["iam:*","organizations:*","route53:*","cloudfront:*","waf:*","support:*"],"Resource":"*","Condition":{"StringNotEquals":{"aws:RequestedRegion":["us-east-1","us-west-2"]}}}
```

### For OK

No remediation required. Recommend periodic re-audit after OU
restructuring or account addition.

## Condition key reference (SCP-specific)

| Condition key | Supported | Notes |
|---|---|---|
| `aws:RequestedRegion` | YES | Restricts to approved regions. Does NOT apply to global services — exclude via NotAction. |
| `aws:ResourceTag/tag-key` | YES | Tag-based filtering. `StringNotEquals` denies untagged resources; `StringEquals` does not. |
| `aws:PrincipalTag/tag-key` | YES | Tag-based filtering on the calling principal. |
| `aws:PrincipalOrgID` | YES | Matches any principal in the same org. Does not restrict to a specific OU. |
| `aws:PrincipalOrgPaths` | YES | Matches principals in a specific OU path. Tighter than PrincipalOrgID. |
| `kms:ViaService` | **NO** | Service-specific — silently never matches in SCPs. Deny is dead. |
| `ec2:ResourceTag/tag-key` | **NO** | Use `aws:ResourceTag/tag-key` instead. |
| `s3:prefix` | **NO** | Service-specific — silently never matches in SCPs. |

## SCP-AUDIT Phase 7 — Deep reference: SCP evaluation internals

### Effective permissions pipeline (SCP layer)

1. **Collect all SCPs** attached to root, every parent OU, and the
   target account. This union is the **effective SCP set**.
2. **For each action + resource pair:** If ANY SCP has a matching
   `Deny`, the request is **denied at the SCP layer** — regardless of
   Allows in other SCPs. If no Deny matches and ANY SCP has a matching
   `Allow`, the request **passes the SCP layer** (proceeds to IAM). If
   neither Allow nor Deny matches, the request is **implicitly denied**
   (allow-list default-deny).
3. **Management account bypasses** this entire pipeline.

### FullAWSAccess mechanics

`FullAWSAccess` is an Allow `*` on `*`, attached by default to root and
every OU/account. Detaching from the ROOT flips the org to allow-list
mode. Detaching from an OU does NOT flip the OU — the root's copy
inherits through. The 5-SCP quota includes FullAWSAccess.

### Quota and limits

- 5 SCPs per target (root, each OU, each account). Hard limit.
- SCP document: 5,120 characters max (serialized JSON).

## Recent AWS features (2024-2026)

- **Declarative policy type (2024-2025):** Organizations introduced a new `DECLARATIVE` policy type alongside `TAG`, `BACKUP`, and `AISERVICES_OPT_OUT` policies. Declarative policies enforce configuration baselines across accounts. Auditors should verify that declarative policies are deployed for critical configuration baselines and that they do not conflict with existing Config rules.
- **New SCP condition keys (2024-2025):** Additional condition keys available in SCPs including `aws:SourceOrgID`, `aws:SourceOrgPaths`, and region restriction keys. Auditors should verify that SCPs use the strongest available condition keys and that region-restriction SCPs cover all required services.
- **SCP evaluation improvements (2024):** Enhanced SCP evaluation engine with better conflict resolution. No new audit-surface fields, but auditors should re-test SCP effectiveness after evaluation engine updates — previously ineffective SCP conditions may now work.

## Domain

AWS CloudOps / Organizations Governance & Compliance.

## AWS documentation

- **Service documentation (AWS Organizations User Guide)** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html
- **Security** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_security.html
- **API reference** — https://docs.aws.amazon.com/organizations/latest/APIReference/
- **CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/organizations/
- **Service control policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
