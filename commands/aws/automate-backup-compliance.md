---
description: Design and implement automated AWS Backup compliance. Cover AWS Backup Audit Manager (audit frameworks, audit templates, control library with manual and automated controls), backup reporting (job summary, compliance, coverage reports; Backup Report Stream), legal hold automation (BackupLegalHold resource, Backup Vault Lock in GOVERNANCE vs LOCK_MODE, EventBridge-triggered litigation hold), cross-account and cross-region auditing via AWS Organizations delegated admin and the org-wide backup vault, AWS Backup Search for eDiscovery, Backup cost allocation tags, and EventBridge Scheduler for periodic audit runs. Enforces LOCK_MODE Vault Lock for compliance frameworks, encryption controls, legal hold test cycles, and org-wide centralization for multi-account orgs.
nl_triggers:
  - "Backup compliance automation"
  - "Backup Audit Manager"
  - "audit framework"
  - "audit template"
  - "legal hold"
  - "litigation hold"
  - "Backup Vault Lock"
  - "compliance report"
  - "job summary report"
  - "coverage report"
  - "cross-account backup audit"
  - "Backup Search"
  - "cost allocation tags backup"
  - "Backup Report Stream"
  - "EventBridge legal hold"
  - "Organizations backup vault"
  - "HIPAA backup compliance"
  - "SOC2 backup compliance"
routes_to: backup-compliance-automator
---

# /aws:automate-backup-compliance

Activate the `backup-compliance-automator` skill and produce a Backup
compliance automation playbook (or validation report).

## What it does

Reads compliance framework, resources in scope, accounts scope, retention
policy, and legal hold requirement, and either:

1. **Designs** a complete compliance playbook with: AWS Backup Audit
   Manager framework (custom or preset) with required controls mapped per
   framework spec (encryption, retention, recency, region isolation),
   scheduled report plans (compliance, job summary, coverage) landing in
   a versioned S3 bucket, legal hold automation (BackupLegalHold resource
   + EventBridge trigger from the legal team + quarterly test cycle),
   cross-account centralization (Organizations delegated admin + org-wide
   backup vault with member access policy + COPY_ACTION in member plans),
   Backup Search scoping for eDiscovery, cost allocation tags activated
   in Billing, EventBridge Scheduler for periodic audit runs, and Step
   Functions orchestrator (RunAudit -> GetFindings -> AutoRemediate |
   PageOnCall -> ExportReport -> NotifySlack).
2. **Validates** an existing Backup compliance posture against the
   mandatory safety baseline (Vault Lock in LOCK_MODE for compliance
   frameworks, encryption control present, legal hold tested within 90
   days, org-wide vault configured for orgs, restore drill within 90 days,
   cost tags active in Cost Explorer, report freshness within 24h).

Emits a deterministic block per design:

```text
FRAMEWORK:
  - [PASS|FAIL] Audit Manager framework configured
  - [PASS|FAIL] Required controls mapped (per framework spec)
  - [PASS|FAIL] Framework actively evaluating (last run within 24h)
REPORTING:
  - [PASS|FAIL] Compliance report plan scheduled
  - [PASS|FAIL] Job summary report scheduled
  - [PASS|FAIL] Coverage report scheduled
  - [PASS|FAIL] Reports land in versioned S3 bucket with retention
LEGAL_HOLD:
  - [PASS|FAIL] BackupLegalHold mechanism documented
  - [PASS|FAIL] Legal hold tested (create + release cycle)
  - [PASS|FAIL] Vault Lock in compliance mode (immutable retention)
  - [PASS|FAIL] EventBridge trigger for litigation hold (if required)
CROSS_ACCOUNT:
  - [PASS|FAIL] Organizations backup delegated admin configured (or N/A: single)
  - [PASS|FAIL] Org-wide backup vault with member access policy
  - [PASS|FAIL] Cross-account copy actions in member plans
SEARCH:
  - [PASS|FAIL] Backup Search scoped to in-scope vaults (if applicable)
  - [PASS|FAIL] eDiscovery workflow documented (search -> hold)
VERIFICATION:
  - [PASS|FAIL] Restore drill run within last 90 days
  - [PASS|FAIL] Cost allocation tags active in Cost Explorer
  - [PASS|FAIL] Report freshness verified (no stale reports)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide framework + scope + retention and ask any of:

- "build a SOC2 backup audit framework for our 30-account org"
- "automate litigation hold via EventBridge for the legal team"
- "set up cross-account backup auditing with a delegated admin"
- "configure Backup Vault Lock in compliance mode for HIPAA"
- "scope Backup Search for eDiscovery"
- "validate our existing Backup compliance posture"
- "activate Backup cost allocation tags per project"

A bare Backup / compliance / audit prompt routes here via the orchestrator.

## Inputs

- **Required:** compliance_framework (SOC2 | HIPAA | PCI | FedRAMP |
  custom:<id>), resources_in_scope (subset of EC2, RDS, DynamoDB, EFS,
  FSx, S3, VMware, Storage Gateway), accounts_scope (single | org),
  retention_policy (e.g., 35d daily, 12m monthly, immutability yes/no).
- **Recommended:** legal_hold_required (yes/no, default no), delegated_
  admin_account_id (for org scope), cost_tag_dimensions (Project,
  Environment, etc.), restore_drill_frequency_days (default 90).
- **For validation mode:** existing Audit Manager framework JSON, report
  plan configs, Vault Lock configuration, legal hold runbook, org vault
  setup.

## Outputs

- One VERDICT block per design (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete compliance playbook (Audit Manager framework, report plans,
  legal hold Lambda + EventBridge rule, cross-account vault access policy,
  EventBridge Schedule, Step Functions ASL) in FRAMEWORK/REPORTING/
  LEGAL_HOLD/CROSS_ACCOUNT/SEARCH.
- Gate pass/fail per dimension in FRAMEWORK/REPORTING/LEGAL_HOLD/
  VERIFICATION.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for backup compliance).
- `/aws:audit-backup-plan` to audit the backup plan itself (this skill
  audits compliance posture, the audit skill audits the plan).
- `/aws:operate-backup-vault` to manage backup vault operations (Vault
  Lock, recovery point management) — this skill designs, operate executes.
- `/aws:operate-rds-backup-restore` / `/aws:operate-ec2-backup` for
  restore operations (this skill does not perform restores).
- `/aws:automate-tag-governance` to enforce the tag hygiene that Audit
  Manager controls depend on (untagged resources are invisible to Audit
  Manager).
- `/aws:automate-dr-failover` to design the DR strategy that cross-region
  backup copies feed into.
