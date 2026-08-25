---
name: firewall-manager-compliance-auditor
description: 'Audits AWS Firewall Manager (FMS) policies across WAF, Shield Advanced, VPC Security Groups, Network Firewall, DNS Firewall, and third-party firewalls — evaluates policy state (READY vs NOT_READY), resource-tag scope coverage gaps, RemediationEnabled posture (enforce vs detect-only), PolicyType currency (WAFV2 vs legacy WAF), IncludeMap/ExcludeMap account/OU coverage, ResourceTypeLists completeness, and live NonCompliantResourceCount. Emits a deterministic verdict (NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK) per policy with enumerated findings and specific CLI remediation. Use when reviewing FMS policy coverage, checking WAF/SG/Shield policy scope, auditing resource-tag enforcement, validating remediation posture, or hardening FMS. Triggers: Firewall Manager, FMS, policy compliance, WAF policy, Shield Advanced policy, Security Group policy, Network Firewall policy, DNS Firewall policy, RemediationEnabled, PolicyState, NOT_READY, ResourceTags scope, IncludeMap, ExcludeMap, NonCompliantResourceCount.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex). No AWS CLI required for offline policy classification. Live-account audits use aws fms list-policies, aws fms get-policy, aws fms list-compliance-status, aws fms get-compliance-detail, aws fms get-protection-status, aws fms get-admin-scope (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  verdict_shape: NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK
  when_to_use: Reviewing an FMS policy configuration, auditing policy scope coverage across an AWS Organization, validating PolicyState (READY vs NOT_READY), checking RemediationEnabled posture, investigating non-compliant resource counts, or hardening FMS posture across WAF, Shield Advanced, VPC Security Groups, Network Firewall, or DNS Firewall policies.
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Firewall Manager, FMS, policy compliance, WAF policy, Shield Advanced, Security Groups policy, Network Firewall policy, DNS Firewall, PolicyState, NOT_READY, RemediationEnabled, ResourceTags, ResourceTypeLists, IncludeMap, ExcludeMap, NonCompliantResourceCount, NONCOMPLIANT, WAFV2, SECURITY_GROUPS_COMMON, SECURITY_GROUPS_CONTENT_AUDIT, SECURITY_GROUPS_USAGE_AUDIT, THIRD_PARTY_FIREWALL, IMPORTED_FIREWALL
  tags: aws, fms, firewall-manager, security, compliance, waf, shield, policy, audit, organizations
  dependencies: aws-orchestrator
---

# Firewall Manager Compliance Auditor

## When to invoke

Invoke-pattern catalog and do-not-invoke routing moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § When to invoke

## Mindset

**One-line takeaway:** the verdict is the **worst** finding across all
dimensions, and three FMS conditions are silent failures —
`PolicyState: NOT_READY` (policy exists but does not enforce),
`RemediationEnabled: false` (detect-only mode), and ResourceTags-only
scope (untagged resources are silently unprotected). Live
`NonCompliantResourceCount > 0` is the loudest signal — but the silent
failures are how environments drift into NONCOMPLIANT over months.

AWS Firewall Manager (FMS) is an Organization-wide enforcement layer for
WAF, Shield Advanced, VPC Security Groups, Network Firewall, DNS
Firewall, and third-party firewalls. It does NOT replace those services;
it applies and maintains their configurations across member accounts.
- `PolicyState: NOT_READY` is a **lifecycle trap**: the policy ARN exists
  but enforcement is suspended. Operators confuse "policy exists" with
  "policy enforced" — the FMS console does not surface this loudly.
- `RemediationEnabled: false` is **detect-only posture**: FMS reports
  NONCOMPLIANT resources but does not auto-apply the WebACL, baseline
  SG, or Shield protection. Violations grow unbounded until an operator
  manually intervenes.
- ResourceTags-only scope is a **silent hole**: resources that should be
  in scope but lack the tag are silently excluded — FMS reports zero
  violations because it sees zero in-scope resources for them.

## Critical rules — read first

Six rules prevent the most dangerous FMS misclassifications:

1. **NOT_READY is not OK.** A `NOT_READY` policy does not enforce —
   zero violations means zero enforcement, not zero exposure.
2. **Detect-only is a sensor, not a control.** `RemediationEnabled:
   false` reports violations but does not apply WebACLs, SGs, or
   Shield. Production detect-only >30 days is a CONFIG_GAP.
3. **Zero violations can mean blind, not clean.** FMS derives
   compliance from AWS Config. A member with Config disabled or
   `EvaluationLimitExceeded=true` reports zero — absence of data, not
   absence of violations.
4. **ResourceTags-only scope is a silent hole.** Resources without the
   tag are out of scope entirely, not just out of remediation.
5. **Deleting a READY policy strips enforcement instantly.** Always
   run `get-protection-status` and confirm `ProtectedResourceCount` is
   zero before `delete-policy`.
6. **PutPolicy is atomic, not staged.** A WebACL swap via FMS applies
   to ALL in-scope resources at once. Edit the WebACL via `wafv2` and
   let FMS re-apply — reversible, one resource at a time.

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `NonCompliantResourceCount > 0` (live violations) | **NONCOMPLIANT** | Step 6 |
| `PolicyState: NOT_READY` | **CONFIG_GAP** | Step 1 |
| `PolicyType: WAF` (legacy, not WAFV2) | **CONFIG_GAP** | Step 2 |
| `RemediationEnabled: false` (detect-only) | **CONFIG_GAP** | Step 4 |
| ResourceTags-only scope, ResourceTypeLists empty | **INCOMPLETE_COVERAGE** | Step 3a |
| IncludeMap omits active OUs/accounts in scope | **INCOMPLETE_COVERAGE** | Step 3b |
| ResourceTypeLists omit critical types for PolicyType | **INCOMPLETE_COVERAGE** | Step 3c |
| FMS administrator account not set | **CONFIG_GAP** | Pre-flight |
| Empty ResourceTypeLists AND empty ResourceTags (silent no-op) | **CONFIG_GAP** | Step 3d |
| READY + full coverage + RemediationEnabled + 0 NonCompliant | **OK** | Step 7 |

Verdict precedence on aggregation (worst finding wins):
`NONCOMPLIANT > INCOMPLETE_COVERAGE > CONFIG_GAP > OK`.

See the ordered steps below for edge cases. Deep FMS internals
(enforcement pipeline, AWS Config coupling, region semantics) are in the
[Deep reference](#deep-reference-fms-enforcement-internals) section at
the end.

## Pre-flight: FMS administrator and Organizations gate

Before evaluating any policy, classify the FMS deployment itself. FMS
cannot operate without an Organizations-managed administrator account.

Live-account pre-flight CLI checks (admin scope, Org delegation, Config recorders, notification channel) moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Live-account pre-flight checks

| Attribute | Value | Effect on audit |
|---|---|---|
| FMS admin account | not set | **CONFIG_GAP** (org-wide). FMS is unconfigured; policies are inert artifacts. Output a single org-level finding and stop — per-policy classification is meaningless without an admin. |
| FMS admin account | set, member of Org | Proceed with full audit. |
| FMS admin account | set, NOT in Org | **ERROR** — admin scope cannot be reconciled. Re-onboard via `aws organizations register-delegated-administrator`. |
| Account scope | Org root | All org accounts in scope. IncludeMap/ExcludeMap empty is NORMAL here — do not flag as coverage gap. |
| Account scope | Specific OUs | Cross-check each OU against current `aws organizations list-roots` → children. A dissolved OU in IncludeMap is a stale coverage gap. |
| Region scope | Not specified | Policy applies to ALL regions including GovCloud/China if the org spans them. Treat as a coverage note, not a finding. |

**If the policy JSON is malformed** (invalid JSON, missing `PolicyId`,
missing `PolicyType`), output:

```text
POLICY: <policy-id>
VERDICT: ERROR
REASON: FMS policy document is not valid JSON or is missing required
fields — cannot classify.
REMEDIATION: Retrieve the canonical policy with `aws fms get-policy
--policy-id <id> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious FMS behaviors

Non-obvious FMS behavior catalog (NOT_READY lifecycle, Config dark spots, silent exclusions, quota traps) moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Step 0: Expert knowledge

### Step 1: PolicyState evaluation (NOT_READY is a lifecycle trap)

If `PolicyState` is `NOT_READY`, classify as **CONFIG_GAP**. The policy
exists in the FMS artifact store but does not enforce. Continue
evaluation — the other dimensions are still meaningful for the eventual
`READY` state.

A NOT_READY policy that has been in that state for >24 hours is a stuck
deployment. Common causes: (1) the underlying WebACL/SG baseline does
not exist or has been deleted; (2) the PolicyType was changed without
re-creating the policy; (3) FMS service-linked role issues in a member
account; (4) Organizations change broke the admin scope.

Note in REMEDIATION: "PolicyState has been NOT_READY for >24h — run
`aws fms get-policy --policy-id <id>` and check
`PolicyUpdateToken`. If stuck, open an AWS support case."

### Step 2: PolicyType currency check

Classify the `PolicyType`:

- `WAFV2` — current. Proceed.
- `WAF` — **legacy WAF Classic.** Flag as **CONFIG_GAP** with a
  migration finding: "PolicyType=WAF is WAF Classic (legacy). AWS
  recommends migration to WAFV2. Create a parallel WAFV2 policy, verify
  parity, then `aws fms delete-policy --policy-id <legacy>`."
- `SHIELD_ADVANCED`, `SECURITY_GROUPS_COMMON`,
  `SECURITY_GROUPS_CONTENT_AUDIT`, `SECURITY_GROUPS_USAGE_AUDIT`,
  `NETWORK_FIREWALL`, `DNS_FIREWALL`, `THIRD_PARTY_FIREWALL`,
  `IMPORTED_FIREWALL` — current. Proceed.

A PolicyType value outside the known set is a malformed input → ERROR.

### Step 3: Resource scope coverage (the silent hole)

The scope is the union of `ResourceTypeLists` × `ResourceTags` ×
`IncludeMap` (minus `ExcludeMap`). A scope narrower than the security
objective is INCOMPLETE_COVERAGE. A scope that is empty or contradictory
is CONFIG_GAP.

**Step 3a: ResourceTags-only scope trap.** If `ResourceTags` is
NON-EMPTY (has at least one tag entry) AND `ResourceTypeLists` is
empty, classify as **INCOMPLETE_COVERAGE**. The policy protects only
resources with the specified tags — every untagged resource in the
org is silently unprotected. The mitigation is either (a) add the tag
to all resources that should be in scope (enforced via SCP), or (b)
broaden the policy to ResourceTypeLists and use ResourceTags as a
refinement, not the sole scope key.

> **Disambiguation — do NOT trigger Step 3a on empty ResourceTags.**
> An EMPTY `ResourceTags: []` (no tag entries) is NOT a finding. It
> means the policy applies to ALL resources of the specified
> `ResourceTypeLists` types — the normal broad-scope case. Only
> NON-EMPTY `ResourceTags` combined with empty `ResourceTypeLists`
> triggers this verdict.

**Step 3b: IncludeMap coverage gap.** If `IncludeMap` lists specific
OUs/accounts, cross-reference against the current Organization tree
(`aws organizations list-roots` recursively). An active OU absent from
IncludeMap is a coverage gap if the policy's stated scope is "org-wide"
(indicated by `ResourceTags` or `ResourceTypeLists` covering broad
types). Classify as **INCOMPLETE_COVERAGE** with the missing OUs listed.

If `IncludeMap` is empty AND the admin scope is Org root, the policy
applies org-wide. This is NORMAL — do not flag.

**Step 3c: ResourceTypeLists completeness per PolicyType.** Compare
`ResourceTypeLists` against the minimum expected set for the
`PolicyType`. Critical omissions are INCOMPLETE_COVERAGE:
- `WAFV2` policy missing `CloudFrontDistribution` and
  `AwsApiGatewayStage`: incomplete (edge + API unprotected).
- `SHIELD_ADVANCED` policy missing `AwsEc2Eip` AND
  `CloudFrontDistribution`: incomplete (EIPs and CloudFront
  unprotected — the two most common DDoS vectors).
- `SECURITY_GROUPS_COMMON` policy missing `AwsEc2Instance` AND
  `AwsElasticLoadBalancingV2LoadBalancer`: incomplete (no EC2/LB
  baseline).

If `ResourceTypeLists` covers at least one critical type for the
PolicyType, do NOT flag — operators may intentionally narrow scope.
Critical-type minimums:
- WAFV2: at least one of {`AwsWafv2WebAcl`,
  `AwsElasticLoadBalancingV2LoadBalancer`, `CloudFrontDistribution`,
  `AwsApiGatewayStage`}
- SHIELD_ADVANCED: at least one of {`AwsEc2Eip`,
  `AwsElasticLoadBalancingV2LoadBalancer`, `CloudFrontDistribution`}
- SECURITY_GROUPS_*: at least one of {`AwsEc2Instance`,
  `AwsEc2NetworkInterface`, `AwsElasticLoadBalancingV2LoadBalancer`}
- NETWORK_FIREWALL / DNS_FIREWALL: `AwsEc2Vpc`

**Step 3d: Empty scope.** If `ResourceTypeLists` is empty AND
`ResourceTags` is empty AND `IncludeMap` is empty (and admin scope is
NOT Org root), the policy is a silent no-op. Classify as **CONFIG_GAP**.
FMS will accept the policy but protect zero resources.

### Step 4: Remediation posture (detect-only vs enforce)

If `RemediationEnabled: false`, classify as **CONFIG_GAP**. The policy
is detect-only: FMS reports NONCOMPLIANT resources but does not apply
the WebACL, SG, Shield protection, or DNS Firewall rule group. This is
the FMS analogue of a WAF in COUNT mode — useful for staging, dangerous
in production.

Note in REMEDIATION: "RemediationEnabled is false — the policy detects
but does not remediate. To enable enforcement: `aws fms put-policy
--policy <updated-json-with-RemediationEnabled-true>`."

A detect-only policy is INTENTIONAL during onboarding (first 1-2 weeks)
but a misconfiguration in steady state. If the policy was created
>30 days ago and RemediationEnabled is still false, escalate the
finding severity.

### Step 5: Live compliance count evaluation

Extract `NonCompliantResourceCount` (aggregated from
`list-compliance-status` across all member accounts in scope):

- **NonCompliantResourceCount > 0** → **NONCOMPLIANT** (highest
  precedence). Live violations exist. The number is a lower bound — FMS
  reports based on Config data, so a Config-disabled member account
  hides its violations.

- **NonCompliantResourceCount = 0 AND PolicyState READY AND
  RemediationEnabled true AND ProtectedResourceCount > 0** → compliance
  dimension OK.

- **ProtectedResourceCount = 0** → coverage gap. Either the scope is
  empty (Step 3d) or FMS could not enumerate resources (Config gap).
  Note as INCOMPLETE_COVERAGE if scope appears non-empty.

**Per-account NONCOMPLIANT drill-down:** When the policy verdict is
NONCOMPLIANT, enumerate the violating member accounts and per-account
violator counts in FINDINGS. A single member at 90% of violations is a
different operational problem than uniform distribution — call it out.

### Step 6: Cross-cutting — PolicyType-specific coverage validation

Apply PolicyType-specific sanity checks as additive findings:

- **WAFV2**: verify the referenced WebACL exists in the policy's
  `SecurityServicePolicyData.ManagedServiceData`. A WAFV2 policy with
  an empty or malformed WebACL JSON is CONFIG_GAP — the policy has
  nothing to apply.
- **SECURITY_GROUPS_COMMON**: verify the baseline SG ID is set and
  reachable from member accounts. A baseline SG in a security account
  requires RAM share or the SG ID is unreachable.
- **NETWORK_FIREWALL**: verify the firewall policy ARN exists. A
  NETWORK_FIREWALL policy with an empty firewall policy reference is
  CONFIG_GAP.
- **SHIELD_ADVANCED**: verify `ProtectedResourceCount` > 0 if scope is
  non-empty. Shield Advanced with 0 protected resources is either an
  empty scope or a stuck protection application.

### Step 7: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
NONCOMPLIANT > INCOMPLETE_COVERAGE > CONFIG_GAP > OK:

```text
verdict = max(
  policy_state_severity,
  policy_type_severity,
  scope_severity,
  remediation_severity,
  compliance_severity,
  policytype_specific_severity
)
```

If no findings (all dimensions OK), the verdict is **OK**.

## Output format (per policy)

```text
POLICY: <policy-id>
POLICY_NAME: <name>
POLICY_TYPE: <WAFV2 | SHIELD_ADVANCED | SECURITY_GROUPS_COMMON | ...>
VERDICT: NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [NONCOMPLIANT] <finding description (Step N)>
  - [INCOMPLETE_COVERAGE] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — WAF policy with violations and detect-only mode

```text
POLICY: waf-prod-edge-protect
POLICY_NAME: prod-edge-waf
POLICY_TYPE: WAFV2
VERDICT: NONCOMPLIANT
REASON: NonCompliantResourceCount=14 across 3 member accounts (Step 5)
— live violations on CloudFront and ALB resources. RemediationEnabled
is false (Step 4), compounding the exposure: FMS reports but does not
apply the WebACL.
FINDINGS:
  - [NONCOMPLIANT] 14 resources non-compliant across 3 accounts:
    111111111111 (4), 222222222222 (8), 333333333333 (2) (Step 5)
  - [CONFIG_GAP] RemediationEnabled=false — policy is detect-only;
    WebACL is not auto-applied to non-compliant resources (Step 4)
REMEDIATION:
  1. Re-enable remediation: `aws fms put-policy --policy
     <updated-json-with-RemediationEnabled-true>`.
  2. Drill per account: `aws fms get-compliance-detail --policy-id
     <id> --member-account 222222222222`.
  3. Investigate why 222222222222 dominates (8/14 violators) — likely
     a Config recorder gap or a member-local WebACL override.
```

### Worked example — malformed ManagedServiceData (WAFV2 with broken WebACL ref)

This second worked example (malformed ManagedServiceData) moved to references.
→ [references/worked-examples.md](references/worked-examples.md) § Worked example — malformed ManagedServiceData

## Edge-case handling

Edge-case catalog (partially malformed policies, legacy fields, conflicting scopes) moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Edge-case handling

## Anti-Patterns — NEVER

- NEVER classify a `PolicyState: NOT_READY` policy as OK. NOT_READY
  means FMS is not enforcing — the absence of violations reflects the
  absence of enforcement, not compliance. This is the most common FMS
  false positive.

- NEVER treat `RemediationEnabled: false` as equivalent to `true`. The
  former is detect-only: FMS produces findings but does not apply
  WebACLs, SG baselines, or Shield protection. Treating them as
  equivalent collapses the distinction between a sensor and a control.

- NEVER assume `NonCompliantResourceCount: 0` means "compliant." FMS
  derives compliance from AWS Config. A member account with Config
  disabled reports 0 — the absence of data, not the absence of
  violations. Always cross-reference Config recorder status before
  trusting a clean count.

- NEVER classify a ResourceTags-only scope (empty ResourceTypeLists) as
  OK. Resources without the tag are silently excluded — the policy
  appears healthy while leaving the untagged population unprotected.
  This is the FMS analogue of an IAM `NotResource` — easy to miss,
  catastrophic in effect.

- NEVER treat `PolicyType: WAF` as equivalent to `WAFV2`. WAF Classic
  is legacy and in maintenance mode. A `WAF` policy in production is a
  migration gap; flag as CONFIG_GAP with the migration path.

- NEVER assume `ProtectedResourceCount: 0` on a READY policy is
  benign. It means FMS is enforcing but found nothing to protect —
  usually a scope misconfiguration (empty ResourceTypeLists, impossible
  ResourceTags combo) or a Config enumeration gap. Investigate before
  closing.

- NEVER recommend deleting an FMS policy without first verifying it is
  NOT_READY or has zero in-scope resources for >30 days. Deleting a
  READY policy that protects resources removes the WebACL/SG/Shield
  enforcement immediately. Always run `aws fms get-protection-status
  --policy-id <id>` before `delete-policy`.

- NEVER assume a policy in `IncludeMap: {ORG_UNIT: [ou-root]}` covers
  the entire org. The OU ID must match the current Organizations root.
  A dissolved/recreated OU produces a new ID; the policy silently
  protects nothing. Verify OU IDs against `aws organizations
  list-roots`.

- NEVER recommend changing the FMS policy itself as the first-line
  remediation for a WebACL rule gap. FMS applies ONE WebACL to all
  in-scope resources atomically. Edit the underlying WebACL via
  `aws wafv2 update-web-acl` and let FMS re-apply — this is reversible
  and staged. Changing the FMS policy to swap WebACLs is atomic and
  breaks all applications simultaneously if the new WebACL is wrong.

- NEVER treat `SECURITY_GROUPS_COMMON`, `SECURITY_GROUPS_CONTENT_AUDIT`,
  and `SECURITY_GROUPS_USAGE_AUDIT` as interchangeable. COMMON applies
  a baseline SG; CONTENT_AUDIT audits existing SG rules against a
  policy; USAGE_AUDIT finds unused SGs. The three are complementary,
  not redundant.

- NEVER overlook `NETWORK_FIREWALL` policies scoped to VPCs without
  firewalls. FMS does NOT create firewalls — it manages rules on
  existing ones. A VPC in scope without a firewall is NONCOMPLIANT and
  stays NONCOMPLIANT until an operator provisions the firewall.

- NEVER treat `ExcludeMap` as weaker than `IncludeMap`. Exclude wins —
  an account in both is excluded. A misconfigured ExcludeMap silently
  punches holes in coverage.

- NEVER assume FMS policies are global. WAF, SG, and Network Firewall
  policies are regional. A multi-region workload requires auditing N
  regional policies. Only Shield Advanced CloudFront protection is
  global.

- NEVER classify a `DNS_FIREWALL` policy as OK just because
  NonCompliantResourceCount is 0. Cross-reference the VPC Resolver
  DNS Firewall associations — FMS manages the rule group, but the VPC
  association is a separate operation. An unassociated VPC is silently
  unprotected.

- NEVER recommend enabling `RemediationEnabled: true` without a
  detect-only staging period for new policies. The transition from
  detect-only to enforce applies the WebACL/SG to all resources
  simultaneously. Stage in detect mode for 1-2 weeks, review the
  violations, then enable.

- NEVER ignore `LimitExceededException` on `put-policy`. The 50-policy
  org cap, when hit mid-remediation, leaves the org partially migrated
  with no rollback path. Validate headroom via
  `aws fms list-policies | jq '.PolicyList | length'` before creating
  new policies.

- NEVER assume the FMS service-linked role
  (`AWSServiceRoleForFMSService`) exists in all member accounts. If a
  member deleted it, enforcement silently fails and resources stay
  NONCOMPLIANT with no error surfaced in the FMS console. Verify via
  `aws iam get-role --role-name AWSServiceRoleForFMSService` per member;
  recovery is `aws iam create-service-linked-role --aws-service-name
  fms.amazonaws.com`.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks and confirmation gates before any remediation CLI moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Pre-flight safety checks

## Remediation guidance

Full per-verdict remediation runbooks (ordering principle + For NONCOMPLIANT / INCOMPLETE_COVERAGE / CONFIG_GAP / OK) moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md) § Remediation guidance

## Practical execution reference (pagination, multi-region, error branching)

Execution-layer patterns (pagination, multi-region, error branching, malformed JSON, quotas, ExcludeMap, enforcement pipeline, Config coupling, region semantics, migration) moved to references.
→ [references/diagnostic-commands.md](references/diagnostic-commands.md), [references/error-handling.md](references/error-handling.md), [references/advanced-patterns.md](references/advanced-patterns.md)

## Condition strength reference (FMS-specific)

Condition-strength table (STRONG/WEAK scope conditions) moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Condition strength reference

## Recent AWS features (2024-2026)

2024-2026 FMS feature notes moved to references.
→ [references/advanced-patterns.md](references/advanced-patterns.md) § Recent AWS features

## References (load on demand)

Consult these only when the corresponding topic comes up:

- [references/worked-examples.md](references/worked-examples.md) — the malformed-ManagedServiceData worked example (moved from § Worked example)
- [references/error-handling.md](references/error-handling.md) — error-code branching and malformed JSON recovery (moved from § Practical execution reference)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live pre-flight checks, pre-flight safety checks, per-verdict remediation runbooks, pagination and multi-region iteration
- [references/advanced-patterns.md](references/advanced-patterns.md) — invoke patterns, Step-0 expert knowledge, edge cases, quotas/ExcludeMap/enforcement/Config/regions/migration, condition strength, recent AWS features

## Domain

AWS CloudOps / Firewall Manager Compliance & Organization-wide Security.

## AWS documentation

- FMS Developer Guide — https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html
- FMS API Reference — https://docs.aws.amazon.com/fms/2018-01-01/APIReference/
- FMS CLI Reference — https://docs.aws.amazon.com/cli/latest/reference/fms/
- **AWS Firewall Manager compliance status** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-compliance-status.html
