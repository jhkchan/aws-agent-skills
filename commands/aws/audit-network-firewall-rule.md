---
description: Audit an AWS Network Firewall configuration for permissive stateful/stateless rules, missing TLS inspection, firewall-subnet routing gaps, rule-group evaluation-order shadowing, and logging blind spots.
nl_triggers:
  - "audit this network firewall"
  - "check firewall rules"
  - "permissive firewall policy"
  - "is TLS inspection enabled"
  - "firewall routing gap"
  - "rule group evaluation order"
  - "stateless default actions"
  - "fragment bypass firewall"
  - "shadowed Suricata rules"
  - "HOME_NET misconfiguration"
  - "network firewall audit"
  - "firewall rule review"
  - "TLS inspection check"
  - "firewall route table audit"
  - "Suricata rule audit"
routes_to: network-firewall-rule-auditor
---

# /aws:audit-network-firewall-rule

Activate the `network-firewall-rule-auditor` skill and audit one or more AWS
Network Firewall configurations (policy + route tables + TLS config) for
security exposure.

## What it does

Reads a Network Firewall policy document plus route-table data and TLS
status, then applies the ordered classification logic:

1. Routing topology — verify workload subnet route tables point through
   firewall ENIs (ROUTING_GAP if bypassed).
2. Stateless default actions — `aws:forward_to_sfe` is correct; `aws:pass`
   disables the stateful engine (PERMISSIVE_RULE).
3. Stateful default actions — `drop_strict` enforces; `alert_strict` is
   IDS-only (PERMISSIVE_RULE for enforcement postures).
4. Permissive rule detection — wildcard Suricata `pass ip any any`,
   all-wildcard stateless pass rules (PERMISSIVE_RULE).
5. Rule-group evaluation order — `STRICT_ORDER` pass-before-drop shadows
   the drop (PERMISSIVE_RULE).
6. TLS inspection — absent TLS config + payload/content rules = blind to
   HTTPS (NO_TLS_INSPECTION).
7. Logging and observability — no logging config (CONFIG_GAP).
8. Aggregation — worst finding wins by priority (PERMISSIVE_RULE >
   ROUTING_GAP > NO_TLS_INSPECTION > CONFIG_GAP > OK).

Emits a deterministic VERDICT per firewall:

```text
FIREWALL: <name>
VERDICT: PERMISSIVE_RULE | NO_TLS_INSPECTION | ROUTING_GAP | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [PERMISSIVE_RULE] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Network Firewall policy and route-table data and ask any of:

- "audit this network firewall"
- "check for permissive firewall rules"
- "is traffic bypassing the firewall?"
- "is TLS inspection enabled on this firewall?"
- "are my Suricata rules shadowed?"
- "check firewall route tables"

A bare firewall name or ARN + any audit verb ("audit this firewall", "check
firewall policy") also routes here via the orchestrator.

## Inputs

- A Network Firewall policy document (JSON), pasted inline or referenced by
  file path.
- Route table data for workload subnets and the firewall subnet (to detect
  ROUTING_GAP).
- TLS inspection config status (`TLSInspectionConfigurationArn` on the
  policy or `describe-tls-inspection-config` output).
- Logging configuration (`describe-logging-configuration` output).
- For live-account audits: a firewall name or ARN — the skill will direct
  the operator to run the relevant `aws network-firewall describe-*` and
  `aws ec2 describe-route-tables` commands.

## Outputs

- One VERDICT block per firewall (multiple findings aggregate to the worst
  verdict by priority).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: fix route tables, change default actions, remove
  wildcard pass rules, enable TLS inspection, enable logging, reorder rules.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Network Firewall security).
- `/aws:audit-ec2-security-groups` for EC2 security group exposure analysis
  of the workloads behind the firewall.
