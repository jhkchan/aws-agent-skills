---
description: Audit an AWS Backup plan for coverage gaps, vault risks (no lock, governance-mode lock, AWS-managed key), impossible lifecycle configs, and compliance violations (sub-daily frequency, short retention).
nl_triggers:
  - "audit this backup plan"
  - "check backup coverage"
  - "is my backup vault locked"
  - "backup lifecycle invalid"
  - "backup compliance check"
  - "cold storage transition"
  - "vault lock governance vs compliance"
  - "backup retention too short"
  - "ransomware protection backup"
  - "backup vault lock"
  - "MoveToColdStorageAfterDays"
  - "backup plan selection empty"
  - "AWS Backup audit"
routes_to: backup-plan-auditor
---

# /aws:audit-backup-plan

Activate the `backup-plan-auditor` skill and audit one or more AWS Backup
plan configurations for coverage gaps, vault risks, lifecycle issues, and
compliance violations.

## What it does

Reads a backup plan configuration (rules, selections, vault metadata) and
applies the ordered classification logic:

1. CONFIG_GAP — impossible lifecycle (cold storage at/after deletion),
   retention below vault-lock floor, missing target vault.
2. COVERAGE_GAP — empty resource selection (Resources: [] with no
   tags/conditions), or no selections defined.
3. VAULT_RISK — no vault lock, governance-mode lock (ChangeableForDays >
   0), or AWS-managed encryption key (aws/backup).
4. NONCOMPLIANT — sub-daily schedule (weekly/monthly cron) or retention
   below 30 days.
5. OK — all dimensions pass.

Emits a deterministic VERDICT per plan:

```text
PLAN: <plan-name>
VERDICT: COVERAGE_GAP | VAULT_RISK | NONCOMPLIANT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and finding>
FINDINGS:
  - <finding description (Step Na)>
  - <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a backup plan configuration and ask any of:

- "audit this backup plan"
- "check backup coverage"
- "is my backup vault locked?"
- "is this backup compliant?"
- "what's wrong with this backup lifecycle?"

A bare plan ARN + any audit verb also routes here via the orchestrator.

## Inputs

- A backup plan configuration including: rules (schedule, lifecycle, target
  vault, copy actions), selections (resources, tags, conditions), and vault
  metadata (lock mode, encryption key).
- For live-account audits: a plan-id/ARN — the skill emits the AWS CLI
  commands to retrieve the full configuration.

## Outputs

- One VERDICT block per plan (first matching step determines the verdict).
- Enumerated FINDINGS list with step citations.
- Specific remediation: fix lifecycle, add resources, enable vault lock,
  update schedule, increase retention — all with CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for backup and recovery).
- `/aws:audit-kms-key-policy` for auditing the KMS key used by the backup
  vault for encryption.
