---
description: Show all AWS CloudOps commands, their natural-language triggers, and the pipeline phases.
nl_triggers:
  - "help"
  - "what commands are available"
  - "what can you audit"
  - "show me the skills"
  - "list commands"
routes_to: (no skill — meta command)
---

# /aws:help

## Slash Commands

| Command | Phase | Purpose | NL example |
|---|---|---|---|
| `/aws:pipeline` | All | Enter the full CloudOps pipeline orchestrator | "full security audit" |
| `/aws:status` | — | One-line phase + routing summary | "where are we in the audit" |
| `/aws:audit-s3-public-access` | 2 Audit | Audit S3 bucket configs for public exposure | "is this bucket public?" |
| `/aws:help` | — | This list | "help" |
| `/aws:audit-ec2-security-groups` | 2 Audit | Audit EC2 SGs for exposed ports + CIS/PCI-DSS violations | "is this security group open?" |

## Specialist Skills

| Skill | Service | Verdict Shape | Phase |
|---|---|---|---|
| `s3-public-access-auditor` | S3 | PUBLIC / SAFE / AMBIGUOUS | 2 Audit |
| `iam-least-privilege-advisor` | IAM | OVERPERMISSIVE / LEAST_PRIVILEGE / AMBIGUOUS | 2 Audit |
| `ec2-security-group-auditor` | EC2 (Security Groups) | OPEN / PUBLIC_NONCRITICAL / RESTRICTED | 2 Audit |

## Pipeline Phases

**Assess -> Audit -> Prioritize -> Remediate**

1. **Assess** — inventory resources, enumerate coverage gaps, baseline state
2. **Audit** — detective auditors read AWS config, emit deterministic VERDICT
3. **Prioritize** — rank findings by severity, cost-impact, compliance-mandate
4. **Remediate** — generate remediation CLI commands, IaC patches, runbook steps

**Router:** `aws-orchestrator` diagnoses the phase and routes to specialist(s)
— it never duplicates specialist content. Every substantive response carries a
phase indicator like `[Phase: Audit | Skills routed: s3-public-access-auditor]`.

Every slash command has an NL equivalent. The orchestrator triages either form
identically.
