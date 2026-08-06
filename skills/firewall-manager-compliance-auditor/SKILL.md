---
name: firewall-manager-compliance-auditor
description: >-
  Audits AWS Firewall Manager (FMS) policies across WAF, Shield Advanced,
  VPC Security Groups, Network Firewall, DNS Firewall, and third-party
  firewalls — evaluates policy state (READY vs NOT_READY), resource-tag
  scope coverage gaps, RemediationEnabled posture (enforce vs detect-only),
  PolicyType currency (WAFV2 vs legacy WAF), IncludeMap/ExcludeMap
  account/OU coverage, ResourceTypeLists completeness, and live
  NonCompliantResourceCount. Emits a deterministic verdict
  (NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK) per policy with
  enumerated findings and specific CLI remediation. Use when reviewing
  FMS policy coverage, checking WAF/SG/Shield policy scope, auditing
  resource-tag enforcement, validating remediation posture, or hardening
  FMS posture across an AWS Organization. Triggers: Firewall Manager,
  FMS, policy compliance, WAF policy, Shield Advanced policy, Security
  Group policy, Network Firewall policy, DNS Firewall policy,
  RemediationEnabled, PolicyState, NOT_READY, ResourceTags scope,
  IncludeMap, ExcludeMap, NonCompliantResourceCount.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex).
  No AWS CLI required for offline policy classification. Live-account
  audits use aws fms list-policies, aws fms get-policy, aws fms
  list-compliance-status, aws fms get-compliance-detail, aws fms
  get-protection-status, aws fms get-admin-scope (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - Firewall Manager
  - FMS
  - policy compliance
  - WAF policy
  - Shield Advanced
  - Security Groups policy
  - Network Firewall policy
  - DNS Firewall
  - PolicyState
  - NOT_READY
  - RemediationEnabled
  - ResourceTags
  - ResourceTypeLists
  - IncludeMap
  - ExcludeMap
  - NonCompliantResourceCount
  - NONCOMPLIANT
  - WAFV2
  - SECURITY_GROUPS_COMMON
  - SECURITY_GROUPS_CONTENT_AUDIT
  - SECURITY_GROUPS_USAGE_AUDIT
  - THIRD_PARTY_FIREWALL
  - IMPORTED_FIREWALL
tags: [aws, fms, firewall-manager, security, compliance, waf, shield, policy, audit, organizations]
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
  verdict_shape: "NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an FMS policy configuration, auditing policy scope coverage
    across an AWS Organization, validating PolicyState (READY vs NOT_READY),
    checking RemediationEnabled posture, investigating non-compliant
    resource counts, or hardening FMS posture across WAF, Shield Advanced,
    VPC Security Groups, Network Firewall, or DNS Firewall policies.
---

# Firewall Manager Compliance Auditor

## When to invoke

Invoke this skill when the operator provides an AWS Firewall Manager
(FMS) policy snapshot (from `aws fms get-policy` or `list-policies`)
and asks any of:

- "audit this FMS policy" / "check FMS compliance" / "is this FMS
  policy enforced?"
- "FMS coverage gap" / "is my FMS scope correct?"
- "why does FMS report zero violations?" (the Config-disabled dark-spot
  trap)
- "is the FMS policy NOT_READY?" / "PolicyState NOT_READY"
- "is RemediationEnabled off?" / "FMS detect-only mode"
- "does this Shield Advanced FMS policy cover all resources?"
- "is this a legacy WAF Classic FMS policy?" / "PolicyType WAF"
- "FMS IncludeMap / ExcludeMap coverage"
- "audit my FMS deployment" / "audit firewall manager"
- reviewing an FMS policy before a compliance review, production
  rollout, or org-wide deployment

Do NOT invoke for: per-WebACL rule analysis (use
`wafv2-web-acl-auditor`), per-SG rule analysis (use
`ec2-security-group-auditor`), or Shield Advanced resource-level
protection audits outside FMS (use `shield-advanced-coverage-auditor`).
This skill audits the FMS policy layer — how WAF/SG/Shield/Network
Firewall are applied and enforced across accounts — not the underlying
rule sets.

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

**Live-account pre-flight checks (skip if doing offline policy-doc
audit):**
1. Verify the caller's identity is the FMS administrator account
   (`aws fms get-admin-scope`). Member accounts can READ policies via
   `aws fms list-policies` but CANNOT remediate. Remediation commands
   emitted from a member account fail with `AccessDeniedException`.
2. Verify the AWS Organization is present and the FMS admin is a
   delegated administrator (`aws organizations
   list-delegated-administrators --service-principal
   fms.amazonaws.com`). FMS without Organizations is a hard
   misconfiguration — the service has no scope.
3. Verify AWS Config is enabled in EVERY member account and region in
   scope. FMS uses Config as its compliance data source — without Config,
   a member account is a dark spot: `NonCompliantResourceCount` reads as
   0 (no data), not "compliant." Run `aws configservice
   describe-configuration-recorders` per member per region before
   trusting the count.
4. Verify the FMS notification channel
   (`aws fms get-notification-channel`). Without SNS topic wiring,
   NONCOMPLIANT transitions produce zero operator alerting — the gap
   surfaces only when a Console operator happens to look.

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

### Step 0: Expert knowledge — non-obvious FMS behaviors that change classification

These behaviors are easy to misjudge without operational FMS experience.
Each changes a verdict if ignored:

- **PolicyState is a lifecycle enum, not a deployment timestamp.**
  `READY` means the policy is enforced; `NOT_READY` means it is not.
  `NOT_READY` is most commonly seen after a `PutPolicy` call where the
  underlying WebACL/SG baseline has not yet propagated, or after a
  PolicyType change. It is NOT an error state — but a policy in
  `NOT_READY` for >24 hours is a stuck deployment. Do NOT classify a
  NOT_READY policy as "OK because no violations" — the absence of
  violations reflects the absence of enforcement, not compliance.

- **`RemediationEnabled: false` is detect-only.** The policy classifies
  resources against the target WebACL/SG baseline, but FMS does NOT
  apply the WebACL or modify the SG — it only emits findings. This is
  the FMS analogue of a WAF rule in COUNT mode: metrics look healthy
  because nothing is being blocked. The right mental model is "this
  policy is a sensor, not a control."

- **ResourceTags scoping is a whitelist, not a filter on top of scope.**
  When a policy specifies `ResourceTags`, resources WITHOUT those tags
  are excluded from scope entirely — not just from remediation. FMS
  reports zero violations for them because they are out of scope. A
  "Shield Advanced policy with ResourceTags=[env=prod]" silently leaves
  every non-prod resource unprotected. To enforce tagging hygiene,
  layer an SCP requiring the tag — FMS itself cannot enforce tag
  presence.

- **`ResourceType` (string) vs `ResourceTypeLists` (list) is a versioned
  distinction.** Older policies use the singular `ResourceType` (one
  type per policy); newer policies use `ResourceTypeLists` (multi-type).
  A policy with both is malformed — flag as CONFIG_GAP. An empty
  `ResourceTypeLists` with non-empty `ResourceTags` is the tag-only
  scope trap above.

- **`PolicyType: WAF` is WAF Classic (legacy).** It is distinct from
  `WAFV2`. WAF Classic is in maintenance mode and AWS actively
  recommends migration. A `WAF` policy in production is a CONFIG_GAP,
  not a "different choice." The migration path is `PutPolicy` with a new
  `WAFV2` policy, then `DeletePolicy` on the legacy one.

- **`SHIELD_ADVANCED` protection is per-resource, not per-account.**
  FMS applies Shield Advanced protection to each individual resource
  (EIP, ALB, NLB, CLB, CloudFront distribution, Route 53 hosted zone).
  `ProtectedResourceCount` is the count of resources FMS has registered
  with Shield Advanced under this policy. A count of 0 on a READY policy
  means FMS is enforcing but found nothing to protect — usually a
  ResourceTypeLists or ResourceTags scope gap.

- **FMS uses AWS Config as its compliance data source.** When Config is
  disabled in a member account or region, FMS has no visibility.
  `NonCompliantResourceCount` for that account reads as 0 — which is
  NOT the same as "compliant." The absence of data is the absence of a
  signal. Always cross-reference Config recorder status before trusting
  a clean compliance count.

- **FMS WAF policy applies ONE WebACL to all resources in scope.**
  Resource-specific WebACL customization is not possible via FMS — if
  applications need different rules, they need different FMS policies
  scoped by ResourceTags or ResourceTypeLists. A single policy covers
  one WebACL only.

- **`NETWORK_FIREWALL` policy manages rules; it does NOT create
  firewalls.** A VPC without a firewall is NONCOMPLIANT if scoped, but
  FMS does not provision the firewall — the operator must. With
  `RemediationEnabled: true`, FMS will manage the firewall policy
  attached to a pre-existing firewall; without one, the resource stays
  NONCOMPLIANT indefinitely.

- **`SECURITY_GROUPS_COMMON` applies baseline SGs;
  `SECURITY_GROUPS_CONTENT_AUDIT` audits SG rules against a policy;
  `SECURITY_GROUPS_USAGE_AUDIT` finds unused SGs.** These are three
  distinct SG policies with different semantics. A COMMON policy with
  no baseline SG ARN is a CONFIG_GAP — there is nothing to apply.

- **`DNS_FIREWALL` policies manage Route 53 Resolver DNS Firewall rule
  groups per-VPC.** A VPC without a Resolver DNS Firewall attached is
  NONCOMPLIANT. FMS does not create the VPC association; it manages the
  rule group contents.

- **`THIRD_PARTY_FIREWALL` (Fortinet FortiGate Cloud, Palo Alto Cloud
  NGFW) and `IMPORTED_FIREWALL` policies delegate to external
  vendors.** A `THIRD_PARTY_FIREWALL` policy references a
  `ThirdPartyFirewallPolicy` with vendor-specific config; FMS does not
  validate the vendor firewall state. Compliance is binary:
  in-scope + registered = OK; in-scope + unregistered = NONCOMPLIANT.

- **`DeleteUnusedFMSPolicies` is an opt-in flag, not a default.** When
  `true`, FMS auto-deletes policies that no longer match any resource.
  When `false` (default), stale policies accumulate — they appear in
  `list-policies` but contribute nothing. A policy with 0
  ProtectedResourceCount and 0 NonCompliantResourceCount for >90 days
  is a candidate for deletion; flag as a CONFIG_GAP note, not a verdict
  driver.

- **FMS policy is REGIONAL for WAF/SG/Network Firewall, GLOBAL for
  Shield Advanced CloudFront.** A WAF policy in us-east-1 protects
  resources in us-east-1 only. Shield Advanced CloudFront protection
  is global because CloudFront distributions are global. Auditing a
  multi-region workload requires auditing N regional policies.

- **`IncludeMap` accepts `ACCOUNT`, `ORG_UNIT` keys.** `ExcludeMap`
  mirrors. Both are independent — an account in IncludeMap's OU and
  ExcludeMap's account list is EXCLUDED (Exclude wins, mirroring IAM
  evaluation). A dissolved OU in IncludeMap is silently ignored.

- **FMS compliance is reported per-account-per-policy.**
  `list-compliance-status` returns `PolicyComplianceStatus` entries per
  member account. A single NONCOMPLIANT member can drag the policy
  verdict — aggregate to policy level by treating any NONCOMPLIANT
  member as a policy-level NONCOMPLIANT finding.

- **FMS PolicyType-specific resource type vocabulary.** Each PolicyType
  accepts a constrained set of resource types. A `ResourceTypeLists`
  entry not in the allowed set for the PolicyType is silently ignored.
  Reference table (non-exhaustive):
  - WAFV2: `AwsWafv2WebAcl`, `AwsApiGatewayStage`, `AwsAppsyncGraphQLApi`,
    `AwsElasticLoadBalancingV2LoadBalancer`, `CloudFrontDistribution`,
    `AwsCognitoUserPool`
  - SHIELD_ADVANCED: `AwsElasticLoadBalancingV2LoadBalancer`,
    `AwsElasticLoadBalancingLoadBalancer`, `AwsEc2Eip`,
    `CloudFrontDistribution`, `AwsRoute53HostedZone`
  - SECURITY_GROUPS_*: `AwsEc2Instance`, `AwsEc2NetworkInterface`,
    `AwsElasticLoadBalancingV2LoadBalancer`,
    `AwsElasticLoadBalancingLoadBalancer`
  - NETWORK_FIREWALL: `AwsEc2Vpc`
  - DNS_FIREWALL: `AwsEc2Vpc`

- **`GetProtectionStatus` returns `ProtectedResourceCounters`, a list
  of resource-type → count.** The sum is the policy's actual footprint.
  Compare against expected scope (`ResourceTypeLists` × member accounts
  in IncludeMap). A counter at 0 for a type in scope indicates the
  target resource does not exist in member accounts OR FMS could not
  enumerate it (Config gap). Both are findings.

- **`PutPolicy` is atomic per policy but NOT per resource.** A
  remediation that updates the WebACL applies to all resources in
  scope at once — there is no staged rollout. If the new WebACL breaks
  an application, ALL applications protected by this policy break
  simultaneously. Prefer editing the WebACL via `wafv2` and letting FMS
  re-apply, rather than changing the FMS policy itself.

- **Quota: 50 FMS policies per organization (soft cap).** Remediation
  that proposes new policies may hit the cap and fail silently with
  `LimitExceededException`. Validate before `PutPolicy`.

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
non-empty AND `ResourceTypeLists` is empty, classify as
**INCOMPLETE_COVERAGE**. The policy protects only resources with the
specified tags — every untagged resource in the org is silently
unprotected. The mitigation is either (a) add the tag to all resources
that should be in scope (enforced via SCP), or (b) broaden the policy
to ResourceTypeLists and use ResourceTags as a refinement, not the
sole scope key.

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

## Edge-case handling

- **Partially malformed policy.** If the policy JSON parses but
  individual fields are missing (`PolicyType`, `PolicyId`), classify
  the valid dimensions and emit an ERROR note for each malformed field.
  Do NOT silently classify the entire policy as ERROR when only one
  field is broken.

- **Multi-policy aggregation.** When auditing an entire FMS deployment
  (`aws fms list-policies`), classify each policy independently. The
  deployment-level verdict is the worst across all policies. A single
  NONCOMPLIANT policy makes the deployment NONCOMPLIANT.

- **Cross-admin-scope policies.** With multiple FMS administrators
  (per-OU delegation, available 2024+), each admin sees only its scope.
  `list-policies` returns only policies the calling admin manages. A
  "clean" deployment from one admin's perspective may have policies
  owned by another admin — cross-reference `get-admin-scope` to map
  coverage.

- **ResourceTags with multiple values.** FMS treats multi-value
  ResourceTags as logical AND across keys, OR within values
  (`[{Key: env, Value: prod}, {Key: tier, Value: web}]` = env=prod AND
  tier=web). Multi-value tags narrow scope — flag if the intent was OR.

- **Policy with `DeleteUnusedFMSPolicies: true`.** This is a hygiene
  flag, not a security verdict driver. Note it as OK with a comment
  "auto-cleanup enabled."

- **Stale `IncludeMap` OUs.** An OU that has been dissolved (deleted
  from Organizations) but remains in `IncludeMap` is silently ignored
  by FMS. The policy applies to fewer accounts than the operator
  believes. Cross-reference `aws organizations list-ous` and flag stale
  entries as CONFIG_GAP.

- **Empty ResourceTypeLists AND non-empty ResourceType (singular).**
  Treat the singular `ResourceType` as the effective scope. Do NOT flag
  as empty — the field is the legacy form.

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

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-policy`, `delete-policy`, `associate-admin-account`), emit:
  `CONFIRM: About to <action> on policy <id> in account <admin-acct>.
  This affects <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms. FMS
  policy changes propagate to ALL member accounts in scope — there is
  no staged rollout.
- **MANDATORY QUOTA PRE-CHECK before `put-policy` creating a new
  policy.** Run `aws fms list-policies --output json | jq '.PolicyList
  | length'`. If the count is at or above 50 (the org soft cap),
  REFUSE to emit the create command and instruct the operator to
  delete unused policies first. Hitting the cap mid-remediation leaves
  the org in a partially-migrated state — `LimitExceededException` on
  `put-policy` is not recoverable without a deletion.
- **Admin scope verification.** Confirm the caller is the FMS
  administrator: `aws fms get-admin-scope --profile <p>`. Member
  accounts CANNOT remediate — `put-policy` fails with
  `AccessDeniedException`. Surface this BEFORE the operator approves.
- **Capture current policy for rollback.**
  `aws fms get-policy --policy-id <id> --output json > /tmp/<id>-backup-$(date +%s).json`
  BEFORE any modification. FMS policies are not versioned — `put-policy`
  replaces the entire policy atomically. There is no undo without a
  backup.
- **Verify ProtectedResourceCount before deletion.**
  `aws fms get-protection-status --policy-id <id>`. If the count is >0,
  deleting the policy removes protection from those resources
  immediately. Require explicit operator acknowledgement of the count.
- **Verify the WebACL exists before WAFV2 policy creation.** The
  WebACL referenced in `SecurityServicePolicyData.ManagedServiceData`
  must exist in the policy's region. A `put-policy` with a non-existent
  WebACL is accepted but the policy enters NOT_READY.
- **Detect-only staging for new policies.** Any new FMS policy should
  be created with `RemediationEnabled: false` for the first 1-2 weeks.
  Transition to `true` only after reviewing `list-compliance-status`
  output. Switching directly to enforce applies the WebACL/SG to all
  resources simultaneously — false positives break applications.
- **Prefer WebACL edits over FMS policy swaps.** When the rule set
  needs updating, edit the WebACL via `wafv2 update-web-acl` (staged,
  reversible) and let FMS re-apply. Swapping the WebACL via a new FMS
  policy is atomic — a bad WebACL breaks every protected resource at
  once.
- **Multi-region awareness.** For multi-region workloads, a remediation
  must be applied to each regional FMS policy independently. FMS does
  NOT sync policies across regions.
- **For NONCOMPLIANT findings**, treat as incident-response if
  RemediationEnabled was previously false — the violations represent
  resources that were silently unprotected during the detect-only
  window. Audit CloudTrail for relevant API activity during the gap.

## Remediation guidance

**Remediation ordering principle:** always prefer the smallest blast-
radius change first. Edit the WebACL/SG (one resource type, reversible)
BEFORE editing the FMS policy (atomic across all resources). Stage any
new FMS policy in detect-only mode before enforcing.

### For NONCOMPLIANT — live violations (Step 5)

1. Drill per-member-account:
   `aws fms get-compliance-detail --policy-id <id> --member-account <acct>`
   to enumerate violators.
2. If RemediationEnabled is true, the violations indicate Config
   discovered resources that FMS could not bring into compliance
   (typically: underlying WebACL missing, member-local override, or
   resource deletion race). Address root cause per violator.
3. If RemediationEnabled is false, re-enable after staging:
   `aws fms put-policy --policy <json-with-RemediationEnabled-true>`.
4. For SHIELD_ADVANCED policies, verify each violator resource still
   exists — Shield protection on a deleted resource is a stale finding.
5. For NETWORK_FIREWALL policies, provision the missing firewall in
   the violating VPC: `aws network-firewall create-firewall`. FMS will
   manage the policy once the firewall exists.

### For INCOMPLETE_COVERAGE — scope gaps (Step 3)

1. For ResourceTags-only scope: either add the tag to all resources
   that should be in scope (enforced via SCP), or broaden
   ResourceTypeLists and use ResourceTags as a refinement.
2. For missing critical resource types: update ResourceTypeLists via
   `aws fms put-policy` with the additional types. Verify the change
   does not exceed the 50-policy org quota.
3. For missing OUs in IncludeMap: cross-reference `aws organizations
   list-roots` and add the missing OU IDs. Stale OU IDs in IncludeMap
   must be removed — they are silently ignored today but may produce
   errors on future FMS versions.
4. After scope expansion, re-evaluate in detect-only mode
   (`RemediationEnabled: false`) for 1-2 weeks before re-enforcing.

### For CONFIG_GAP — policy misconfiguration

1. **PolicyState NOT_READY**: investigate root cause. Run
   `aws fms get-policy --policy-id <id>` and inspect
   `PolicyUpdateToken`. If the underlying WebACL/SG baseline is
   missing, recreate it. If stuck for >24h, open an AWS support case.
2. **RemediationEnabled false**: stage transition to true. Review
   `list-compliance-status` first; address any existing violations
   before flipping to enforce.
3. **PolicyType WAF (legacy)**: create a parallel WAFV2 policy with
   equivalent WebACL coverage. Verify parity via
   `get-protection-status` comparison. Then
   `aws fms delete-policy --policy-id <legacy>`.
4. **Empty ResourceTypeLists**: identify the intended scope and add
   types. If the policy is genuinely unused (>90 days, 0 protected),
   delete it.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying FMS notification channel is wired
   (`aws fms get-notification-channel`) — operators miss NONCOMPLIANT
   transitions without SNS alerts.
3. Recommend periodic re-audit (quarterly) — FMS scope drifts as
   accounts join/leave the Org and resources are created/destroyed.
4. For Shield Advanced policies, recommend annual review of protected
   resource coverage against current infra (EIPs, LBs, CloudFront).

## Practical execution reference (pagination, multi-region, error branching)

These patterns are the execution layer the classification logic above
depends on. Skipping them produces silent under-counts and false OK
verdicts.

### Pagination — drain every NextToken

Every FMS list API is paginated. Truncating after the first page silently
undercounts scope and compliance:

| API | Max per page | Required loop |
|---|---|---|
| `aws fms list-policies` | 100 (default 100) | Drain `NextToken` to completion; audit every returned policy. |
| `aws fms list-compliance-status --policy-id <id>` | 100 | Page per policy until `NextToken` is empty; aggregate `PolicyComplianceStatus` across all member accounts. |
| `aws fms list-member-accounts` | 100 | Page to enumerate the full in-scope member set; cross-reference against the Organization tree. |
| `aws fms get-protection-status --policy-id <id>` | single response | `ProtectedResourceCounters` is a complete list — no pagination, but verify it is non-empty. |

Pattern (bash, all AWS CLI v2):

```bash
TOKEN=""
while :; do
  if [ -z "$TOKEN" ]; then
    RESP=$(aws fms list-compliance-status --policy-id "$PID" --output json)
  else
    RESP=$(aws fms list-compliance-status --policy-id "$PID" --next-token "$TOKEN" --output json)
  fi
  echo "$RESP" | jq -r '.PolicyComplianceStatusList[]'
  TOKEN=$(echo "$RESP" | jq -r '.NextToken // empty')
  [ -z "$TOKEN" ] && break
done
```

**Stale pagination caveat:** AWS Config-backed resource inventories lag
by 5-15 minutes. A `list-compliance-status` response reflects the
Config snapshot, not real-time. A resource created 2 minutes ago is NOT
in the compliance count yet. Note this in the audit timestamp.

### Multi-region iteration

WAF, SG, and Network Firewall policies are regional. Auditing a single
region misses the other N-1 regional policies. The iteration:

```bash
for REGION in $(aws account list-regions --profile "$P" --output json \
  | jq -r '.Regions[] | select(.RegionOptStatus!="DISABLED") | .RegionName'); do
  aws fms list-policies --region "$REGION" --profile "$P" --output json \
    | jq -r '.PolicyList[].PolicyId'
done
```

- **Skip DISABLED regions** — FMS cannot operate there even if a policy
  exists (it will be stale).
- **Shield Advanced CloudFront policies are global** — they appear in
  every region's `list-policies`. De-duplicate by `PolicyId` to avoid
  double-counting.
- **`list-policies` returns policies MANAGED BY the calling admin
  account.** With per-OU admin delegation (2024+), each admin sees only
  its scope. Iterate `aws fms list-admin-accounts-for-organization` and
  assume each admin role to enumerate the full policy set.

### Error-code branching

| Error | Meaning | Auditor action |
|---|---|---|
| `AccessDeniedException` on `fms put-policy` | Caller is a member account, not the FMS admin. | Surface before remediation: only the delegated admin can remediate. |
| `ResourceNotFoundException` on `get-policy` | Policy was deleted between list and get (race). | Re-run `list-policies`; skip the stale id. |
| `InvalidOperationException` on `get-compliance-detail` | Policy is NOT_READY (no compliance data). | Confirm Step 1 finding; compliance count is not trustworthy. |
| `LimitExceededException` on `put-policy` | Org hit the 50-policy quota. | Delete unused policies before creating new ones; do NOT silently retry. |
| `InternalErrorException` | Transient FMS backend. | Retry with exponential backoff (max 3). |

### Malformed JSON recovery

When `get-policy` returns a policy with malformed `ManagedServiceData`
(the embedded WebACL JSON), classify the dimensions you can and emit:

```text
NOTE: ManagedServiceData JSON is malformed for policy <id> — cannot
validate the referenced WebACL/SG baseline. Re-fetch with `aws fms
get-policy --policy-id <id> --output json` and inspect
SecurityServicePolicyData.ManagedServiceData.
```

Do NOT silently mark the policy OK — the WebACL reference may be broken.

### FMS quotas (the quantitative guardrails)

- **50 FMS policies per organization** (soft cap). Remediations that
  propose new policies must validate headroom via `aws fms list-policies
  | jq 'length'` before `put-policy`. Hitting the cap mid-remediation
  leaves the org in a partially-migrated state.
- **1 FMS administrator account per org** (legacy) or multiple admins
  per OU scope (2024+). With multiple admins, each admin's
  `list-policies` is scoped — enumerate all admins via
  `aws fms list-admin-accounts-for-organization` to get the full policy
  set.
- **AWS Config recorder must be enabled** in every member account in
  every in-scope region. A member with Config disabled is a dark spot
  — `NonCompliantResourceCount` reads 0 (no data), not "compliant".
- **FMS service-linked role (`AWSServiceRoleForFMSService`)** must
  exist in every member account. FMS auto-creates it on first policy
  application; if a member deleted it, enforcement silently fails and
  the resource stays NONCOMPLIANT. Verify via
  `aws iam get-role --role-name AWSServiceRoleForFMSService` per member.
  Recovery: `aws iam create-service-linked-role --aws-service-name
  fms.amazonaws.com`.

### ExcludeMap precedence and stale-OU handling

- **Exclude wins over Include.** An account appearing in both
  `IncludeMap` and `ExcludeMap` is EXCLUDED. This mirrors IAM
  evaluation (explicit deny wins). Always cross-reference both maps —
  an ExcludeMap entry silently punches holes in coverage.
- **Stale OU IDs** in `IncludeMap` are silently ignored by FMS (the OU
  was dissolved or recreated). Cross-reference
  `aws organizations list-roots` recursively and flag any
  `IncludeMap.ORG_UNIT` entry not in the current tree as a CONFIG_GAP.
- **Account-level IncludeMap entries** do not auto-track new accounts
  joining an OU. Use OU-level scoping whenever possible — it auto-tracks
  org changes.
- **Shield Advanced CloudFront scope** is global; `IncludeMap.ACCOUNT`
  still applies (the resource owner account). Verify CloudFront
  distributions in excluded accounts are intentionally unprotected.



### Enforcement pipeline

When FMS enforces a policy on a member account, the sequence is:

1. **AWS Config** discovers resources in the member account and
   evaluates them against the FMS policy's scope (ResourceTypeLists ×
   ResourceTags × IncludeMap).
2. **FMS service-linked role** in the member account
   (`AWSServiceRoleForFMSService`) is assumed by FMS to apply the
   WebACL/SG/Shield protection. If the role is missing or modified,
   enforcement silently fails.
3. **Resource tagging check** — resources must match ResourceTags if
   specified. Resources without the tag are excluded from scope
   entirely.
4. **WebACL/SG application** — FMS calls `wafv2 associate-web-acl` /
   `ec2 modify-network-interface-attribute` / `shield create-protection`
   on each in-scope resource.
5. **Compliance reporting** — FMS writes `PolicyComplianceStatus` per
   member account, observable via `list-compliance-status`.

A break at any stage produces NONCOMPLIANT resources. The stage of
breakage is NOT reported — operators must drill via
`get-compliance-detail` to identify root cause.

### AWS Config coupling

FMS is structurally dependent on AWS Config:
- Config discovers resources; FMS uses Config's resource inventory as
  its source of truth.
- Config's `ConformancePack` and `ConfigRule` are separate from FMS —
  FMS has its own compliance dimension.
- A member account with Config disabled is a dark spot: FMS sees zero
  resources, zero violations. The absence of data is NOT the absence of
  exposure.
- Config recorder coverage gaps (e.g., recorder not recording EC2)
  produce partial FMS visibility — `NonCompliantResourceCount` may
  undercount.

### Region semantics

- WAF, SG, and Network Firewall policies are **regional** — a policy
  in us-east-1 protects resources in us-east-1 only.
- Shield Advanced CloudFront protection is **global** — CloudFront
  distributions are global resources; the policy applies regardless of
  region.
- Shield Advanced EIP/ALB/NLB/CLB protection is **regional**.
- A multi-region workload requires auditing N regional FMS policies.
  Use `aws fms list-policies --region <r>` per region.

### PolicyType migration paths

- **WAF Classic → WAFv2**: create a new WAFV2 FMS policy with an
  equivalent WAFv2 WebACL. Verify `ProtectedResourceCounter` parity.
  Then delete the legacy WAF policy. There is no in-place migration —
  the PolicyType is immutable per policy.
- **SG COMMON → CONTENT_AUDIT**: these are distinct policy types with
  distinct purposes. COMMON applies a baseline; CONTENT_AUDIT audits
  existing SG rules. Both can coexist on the same resource scope.

## Condition strength reference (FMS-specific)

| Condition | Strength | Reason |
|---|---|---|
| ResourceTags + SCP tag enforcement | STRONG | SCP requires the tag on resource creation; FMS scope tracks the tag. Coupled, they prevent bypass. |
| ResourceTags only | WEAK | Tags are mutable; operators can remove them to escape FMS scope. Without SCP enforcement, the boundary is advisory. |
| IncludeMap `ORG_UNIT` | STRONG | Org tree is the source of truth; OU membership is enforced by Organizations. |
| IncludeMap `ACCOUNT` | MODERATE | Account IDs are stable but specific — easy to miss new accounts joining the org. |
| ExcludeMap | STRONG | Exclude wins. An ExcludeMap entry is a deliberate carve-out. |
| ResourceTypeLists | STRONG | Resource type is intrinsic to the resource; not bypassable. |

## Recent AWS features (2024-2026)

- **FMS Network Firewall stateless rule group enhancements (2024):**
  FMS now manages stateless Suricata-compatible rule groups for Network
  Firewall policies. Auditors should verify that
  `FirewallPolicy` references include both stateful and stateless rule
  groups — stateless-only is a coverage gap for inspected traffic.
- **DNS Firewall FMS policy GA (2024):** FMS now manages Route 53
  Resolver DNS Firewall rule groups across accounts. Auditors should
  verify that VPCs in scope have a Resolver DNS Firewall association —
  FMS manages the rule group, not the VPC association.
- **Third-party firewall support expansion (2024-2025):** FMS manages
  Fortinet FortiGate Cloud and Palo Alto Networks Cloud NGFW via
  `THIRD_PARTY_FIREWALL` policy type. Auditors should verify vendor
  firewall registration via `aws fms list-third-party-firewall-firewall-policies`
  — FMS does not validate vendor-side state.
- **Imported Firewall policy (2024):** `IMPORTED_FIREWALL` policy type
  allows importing existing firewall policies under FMS management.
  Auditors should verify the imported policy is in sync with the
  vendor's source of truth.
- **FMS per-OU admin scope delegation (2024-2025):** Multiple FMS
  administrators can now manage distinct OU scopes. Auditors should
  enumerate all admins via `aws fms list-admin-accounts-for-organization`
  and audit each admin's scope independently — a single admin's "clean"
  view does not imply org-wide coverage.
- **DefaultApplicationReportingCriteria (2024-2025):** New reporting
  scope for unprotected applications. Auditors should review
  `GetAdminScope` response for `DefaultApplicationReportingCriteria` —
  its presence means FMS reports on apps outside explicit policy scope.
- **ResourceTypeLists multi-type scoping (2024):** Modern policies use
  `ResourceTypeLists` (list) instead of legacy `ResourceType` (string).
  Auditors should treat singular `ResourceType` as a legacy form —
  functional but not multi-type capable.

## Domain

AWS CloudOps / Firewall Manager Compliance & Organization-wide Security.

## AWS documentation

- **AWS Firewall Manager Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-chapter.html
- **AWS Firewall Manager API Reference** — https://docs.aws.amazon.com/fms/2018-01-01/APIReference/
- **AWS CLI Command Reference (FMS)** — https://docs.aws.amazon.com/cli/latest/reference/fms/
- **AWS Firewall Manager Security** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-security.html
- **AWS Firewall Manager Policies** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-policies.html
- **AWS Firewall Manager compliance status** — https://docs.aws.amazon.com/waf/latest/developerguide/fms-compliance-status.html
