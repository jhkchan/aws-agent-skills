---
description: Audit SSM managed instances for coverage (SSM Agent reachable + IAM profile attached), association compliance, patch baseline adherence, Session Manager vs SSH exposure, inventory collection, and Run Command posture — emits UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK per instance (routes to ssm-managed-instance-auditor).
nl_triggers:
  - "audit my SSM managed instances"
  - "SSM agent not running"
  - "is Session Manager enabled"
  - "patch compliance status"
  - "SSM NON_COMPLIANT"
  - "ConnectionLost instance"
  - "is inventory collection enabled"
  - "AWS-ApplyPatchBaseline failed"
  - "open SSH instead of Session Manager"
  - "audit hybrid activation"
  - "mi- instance coverage"
  - "SSM fleet health"
  - "AmazonSSMManagedInstanceCore"
  - "AWS-UpdateSSMAgent missing"
  - "VPC endpoints for SSM"
routes_to: ssm-managed-instance-auditor
---

# /aws:audit-ssm-managed-instance

Activate the `ssm-managed-instance-auditor` skill and audit one or more
SSM managed instances across coverage, association compliance, patch
baseline adherence, Session Manager vs SSH, inventory collection, and
Run Command posture.

## What it does

Reads an SSM instance-info document (describe-instance-information
output) plus association, patch, session, and inventory snapshots, then
applies the ordered classification logic:

1. Pre-flight instance metadata gate — short-circuit dedicated hosts,
   stopped instances, and freshly-launched (< 5 min) instances.
2. Coverage check — EC2 IAM profile with AmazonSSMManagedInstanceCore
   (or legacy equivalent); PingStatus Active + LastPingDateTime fresh;
   hybrid activation role correct. Unreachable = UNMANAGED (stop here).
3. Association compliance — Failed associations drive NONCOMPLIANT at
   the association's declared ComplianceSeverity.
4. Patch baseline adherence — NON_COMPLIANT + CRITICAL missing patches
   drive NONCOMPLIANT. No Patch Group tag = CONFIG_GAP.
5. Session Manager vs SSH — broad-CIDR inbound on TCP/22 with no recent
   session drives NO_SESSION_MANAGER.
6. Inventory collection — missing AWS-GatherSoftwareInventory or stale
   runs drive CONFIG_GAP.
7. Aggregation — worst finding wins, in order:
   UNMANAGED > NONCOMPLIANT > NO_SESSION_MANAGER > CONFIG_GAP > OK.

Emits a deterministic VERDICT per instance:

```text
INSTANCE: <instance-id>
VERDICT: UNMANAGED | NONCOMPLIANT | NO_SESSION_MANAGER | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and rule number>
FINDINGS:
  - [UNMANAGED] <finding description (Rule C-x)>
  - [NONCOMPLIANT] <finding description (Rule P-x / A-x)>
  - [CONFIG_GAP] <finding description (Rule V-x / I-x)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an SSM instance configuration (describe-instance-information +
association + patch + session + inventory snapshots) and ask any of:

- "audit my SSM managed instances"
- "why is this instance ConnectionLost?"
- "is Session Manager enabled?"
- "patch compliance status"
- "is inventory collection enabled?"
- "audit hybrid activation instances"
- "is the SSM agent running?"

A bare instance-id + any audit verb ("audit i-xxx", "check SSM
coverage") also routes here via the orchestrator.

## Inputs

- An SSM instance-info document (describe-instance-information output),
  paired with association status (describe-instance-associations-status),
  patch state (list-compliance-items / describe-patch-states), session
  history (describe-sessions), and inventory (get-inventory).
- For EC2: also include the IAM instance profile (ec2 describe-instances)
  and the security group rules (ec2 describe-security-groups).
- For hybrid (`mi-*`) instances: include the activation role ARN.

## Outputs

- One VERDICT block per instance (multiple findings aggregate to the
  worst severity, in order).
- Enumerated FINDINGS list with per-finding severity and rule citation.
- Specific remediation: attach IAM profile, run patch Install, restrict
  SSH CIDR, create inventory association, deploy VPC endpoints.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Systems Manager operational posture).
- `/aws:audit-ec2-security-groups` for deeper SG analysis when this
  audit surfaces a NO_SESSION_MANAGER finding.
- `/aws:audit-iam-least-privilege` for analysis of the
  AmazonSSMManagedInstanceCore role's identity-based policy boundaries.
