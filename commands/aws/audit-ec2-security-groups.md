---
description: Audit EC2 security groups for publicly exposed ports, compliance violations (CIS/PCI-DSS/NIST), and attack-surface risks.
nl_triggers:
  - "is this security group open"
  - "check for 0.0.0.0/0 rules"
  - "security group audit"
  - "audit my security groups"
  - "port exposure"
  - "open ports"
  - "SSH open to internet"
  - "RDP exposed"
  - "database port exposed"
  - "check SG rules"
  - "CIS benchmark security groups"
  - "PCI-DSS network controls"
  - "firewall rule audit"
  - "attack surface check"
routes_to: ec2-security-group-auditor
---

# /aws:audit-ec2-security-groups

Activate the `ec2-security-group-auditor` skill to audit EC2 security group
inbound rules. The skill will:

1. **Classify each inbound rule** independently — evaluating the source CIDR,
   SG reference, or prefix list against the public/restricted/conditional
   matrix, then evaluating the port/protocol against the high-risk registry.
2. **Aggregate to a worst-case verdict** per security group:
   `OPEN > PUBLIC_NONCRITICAL > RESTRICTED`.
3. **Emit a structured report** with VERDICT, SEVERITY (CVSS-style), CIS/PCI-DSS/
   NIST control IDs, REASON, and specific REMEDIATION guidance.
4. **Flag anti-patterns** — all-ports rules, split-horizon CIDRs, ICMP ALL,
   amplification vectors (UDP DNS/NTP/SNMP), customer-managed prefix lists
   requiring re-validation.

## When to use

- Reviewing a security group before production deployment.
- Periodic compliance audit against CIS AWS Foundations Benchmark, PCI-DSS, or
  NIST SP 800-53.
- Incident response involving suspected network exposure.
- Onboarding a new VPC or account for security baseline validation.

## Input format

Provide the security group name and its inbound rules:

```
Security Group: <name>
Inbound rules:
  - Port: <port or range>
    Protocol: <TCP|UDP|ICMP|-1>
    Source: <CIDR|sg-xxx|pl-xxx>
```

## Output format

```
SECURITY_GROUP: <name>
VERDICT: OPEN | PUBLIC_NONCRITICAL | RESTRICTED
SEVERITY: Critical | High | Medium | Low | None
CIS_CONTROLS: <e.g., "5.1" or "N/A">
REASON: <specific rules and per-rule verdicts>
REMEDIATION: <specific action, or "None required">
```

## Pipeline integration

This skill operates in **Phase 2 (Audit)** of the CloudOps pipeline. The
orchestrator routes security-group audit prompts here. Findings feed into
Phase 3 (Prioritize) for severity ranking and Phase 4 (Remediate) for
actionable fix steps.

## CLI equivalent

```bash
node cli/bin/cli.js route "audit my security groups for open ports"
```
