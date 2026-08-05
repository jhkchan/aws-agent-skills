---
description: Audit Organizations Service Control Policies (SCPs) for effective permission boundaries across the OU hierarchy — FullAWSAccess inheritance, deny-list guardrails, unsupported condition keys, and account-level overrides.
nl_triggers:
  - "audit these SCPs"
  - "check SCP guardrails"
  - "effective permissions for this OU"
  - "is LeaveOrganization denied"
  - "FullAWSAccess strategy"
  - "SCP deny-list review"
  - "OU hierarchy security"
  - "organization guardrail audit"
  - "SCP condition key supported"
  - "management account SCP"
  - "aws:RequestedRegion SCP"
  - "organizations security posture"
  - "SCP inheritance check"
  - "permissive SCP"
routes_to: organizations-scp-auditor
---

# /aws:audit-organizations-scp

Activate the `organizations-scp-auditor` skill and audit one or more
Organizations SCP configurations (effective-SCP chain + policy documents)
for security exposure.

## What it does

Reads an SCP policy document plus OU hierarchy context (root -> OU ->
account chain with attached SCPs at each level) and applies the ordered
classification logic:

1. Pre-flight organizational context gate — short-circuit if SCPs are
   not enabled or the target is the management account (SCP-exempt).
2. CONFIG_GAP — FullAWSAccess detached with no Allow replacement,
   Deny using unsupported service-specific condition keys, inert SCPs.
3. PERMISSIVE_SCP — LeaveOrganization not denied, security-service
   disruption not denied, root credential actions not restricted,
   destructive IAM in sensitive OUs.
4. MISSING_GUARDRAIL — no region restriction, no tag-based access
   control.
5. OK — all guardrails present.
6. Aggregation — worst finding wins (CONFIG_GAP > PERMISSIVE_SCP >
   MISSING_GUARDRAIL > OK).

Emits a deterministic VERDICT per target:

```text
TARGET: <account-id or OU-id or root-id>
VERDICT: PERMISSIVE_SCP | MISSING_GUARDRAIL | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [CONFIG_GAP] <finding description (Step 1a)>
  - [PERMISSIVE_SCP] <finding description (Step 2a)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an SCP policy document and OU hierarchy context and ask any of:

- "audit these SCPs"
- "check effective permissions for this OU"
- "is LeaveOrganization denied?"
- "is FullAWSAccess configured correctly?"
- "does this SCP condition key work?"
- "are my guardrails covering the right accounts?"

A root/OU/account ID plus any audit verb also routes here via the
orchestrator.

## Inputs

- An SCP policy document (JSON), pasted inline or referenced by file
  path.
- OU hierarchy context: the root -> OU -> account chain with SCPs
  attached at each level. This drives the effective-SCP evaluation.
- Target type: root, OU, or member account. The management account is
  SCP-exempt and should not be audited as a target.
- For live-account audits: `aws organizations list-policies-for-target`
  output per target in the chain.

## Outputs

- One VERDICT block per target (multiple findings aggregate to the
  worst severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: re-attach FullAWSAccess, add Deny SCPs for
  LeaveOrganization / security services, fix unsupported condition
  keys, add region-restriction guardrails.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Audit specialist for Organizations Governance).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles
  operating within the SCP boundary.
