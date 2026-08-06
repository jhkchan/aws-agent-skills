---
description: Audit AWS Firewall Manager (FMS) policies for PolicyState (NOT_READY lifecycle trap), ResourceTags-only scope coverage gaps, RemediationEnabled detect-only posture, PolicyType currency (WAFV2 vs legacy WAF), ResourceTypeLists completeness, and live NonCompliantResourceCount across WAF, Shield Advanced, VPC Security Groups, Network Firewall, DNS Firewall, and third-party firewalls.
nl_triggers:
  - "audit FMS policy"
  - "Firewall Manager compliance"
  - "FMS policy not ready"
  - "PolicyState NOT_READY"
  - "FMS WAF policy scope"
  - "FMS Shield Advanced coverage"
  - "FMS Security Group policy"
  - "FMS Network Firewall policy"
  - "FMS DNS Firewall policy"
  - "RemediationEnabled false"
  - "FMS detect only"
  - "FMS non-compliant resources"
  - "NonCompliantResourceCount"
  - "ResourceTags scope FMS"
  - "FMS coverage gap"
  - "FMS IncludeMap"
  - "FMS ExcludeMap"
  - "legacy WAF FMS policy"
  - "WAF Classic FMS"
  - "FMS policy audit"
  - "audit firewall manager"
  - "FMS organization scope"
  - "FMS admin scope"
routes_to: firewall-manager-compliance-auditor
---

# /aws:audit-firewall-manager-compliance

Activate the `firewall-manager-compliance-auditor` skill and audit one or
more AWS Firewall Manager (FMS) policies for compliance, coverage, and
configuration posture across WAF, Shield Advanced, VPC Security Groups,
Network Firewall, DNS Firewall, and third-party firewalls.

## What it does

Reads an FMS policy document plus protection-status metadata
(PolicyState, RemediationEnabled, ResourceTypeLists, ResourceTags,
IncludeMap, ExcludeMap, NonCompliantResourceCount,
ProtectedResourceCount) and applies the ordered classification logic:

1. Pre-flight FMS administrator and Organizations gate — short-circuit
   deployments with no delegated FMS administrator or no AWS Organization.
2. PolicyState evaluation — NOT_READY is a silent lifecycle trap
   (CONFIG_GAP).
3. PolicyType currency check — `WAF` (legacy WAF Classic) is a migration
   gap (CONFIG_GAP); `WAFV2` is current.
4. Resource scope coverage — ResourceTags-only scope (silent untagged
   hole), missing critical ResourceTypeLists, stale IncludeMap OUs
   (INCOMPLETE_COVERAGE).
5. Remediation posture — RemediationEnabled=false is detect-only mode
   (CONFIG_GAP).
6. Live compliance count — NonCompliantResourceCount > 0 is
   NONCOMPLIANT (highest precedence).
7. PolicyType-specific sanity — WAFV2 WebACL reference, SG_COMMON
   baseline, NETWORK_FIREWALL policy ARN, SHIELD_ADVANCED protected
   count.
8. Aggregation — worst finding wins
   (NONCOMPLIANT > INCOMPLETE_COVERAGE > CONFIG_GAP > OK).

Emits a deterministic VERDICT per policy:

```text
POLICY: <policy-id>
POLICY_NAME: <name>
POLICY_TYPE: <WAFV2 | SHIELD_ADVANCED | SECURITY_GROUPS_COMMON | ...>
VERDICT: NONCOMPLIANT | INCOMPLETE_COVERAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [NONCOMPLIANT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an FMS policy snapshot and ask any of:

- "audit this Firewall Manager policy"
- "is this FMS policy enforced?"
- "FMS coverage gap check"
- "why does FMS report zero violations?"
- "is the FMS policy in NOT_READY?"
- "is RemediationEnabled off on this FMS policy?"
- "does this Shield Advanced policy cover all resources?"
- "is this a legacy WAF Classic FMS policy?"
- "audit my FMS deployment"

A bare policy id or PolicyName + any audit verb ("audit FMS policy",
"check FMS scope") also routes here via the orchestrator.

## Inputs

- An FMS policy snapshot, pasted inline or referenced by file path.
  Required fields: PolicyId, PolicyName, PolicyType, PolicyState,
  RemediationEnabled, ResourceTypeLists, ResourceTags, IncludeMap,
  ExcludeMap.
- Protection status: ProtectedResourceCount,
  NonCompliantResourceCount, optional PerAccountViolators map for
  drill-down.
- Context: FMS admin scope (Org root / OU / account), AWS Config
  recorder status per member account, notification channel wiring.
  These attributes drive the pre-flight gate and the silent-failure
  detection dimensions.

## Outputs

- One VERDICT block per policy (multiple findings aggregate to the
  worst severity by precedence NONCOMPLIANT > INCOMPLETE_COVERAGE >
  CONFIG_GAP > OK).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: re-enable remediation, broaden ResourceTypeLists,
  add SCP tag enforcement, migrate WAF Classic to WAFv2, drill per
  member account via `aws fms get-compliance-detail`, provision missing
  Network Firewall firewalls.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Firewall Manager organization-wide
  posture).
- `/aws:audit-wafv2-web-acl` for per-WebACL rule analysis (FMS applies
  one WebACL to many resources; the WebACL itself is audited by
  wafv2-web-acl-auditor).
- `/aws:audit-ec2-security-groups` for per-SG rule analysis (FMS applies
  baseline SGs; the SG rules themselves are audited by
  ec2-security-group-auditor).
- `/aws:audit-organizations-scp` for the SCP layer that should enforce
  the tags FMS ResourceTags policies depend on (without an SCP, tag
  scope is advisory).
