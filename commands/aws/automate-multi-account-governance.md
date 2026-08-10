---
description: Design and implement automated AWS multi-account governance. Build OU hierarchies, root-level SCP guardrails (deny-leave-org, deny-root-actions, deny-disable-guardduty), Control Tower landing zone with Account Factory, delegated administration (GuardDuty/Security Hub/Config to audit account), CloudTrail organization trail to log-archive, Config multi-account aggregator (org source), IAM Identity Center permission sets with break-glass path, Resource Explorer cross-account index, and RAM cross-account resource sharing. Enforces SCP inheritance review, org-scoped bucket policies (aws:PrincipalOrgID), and delegation coverage checks.
nl_triggers:
  - "multi-account governance"
  - "OU hierarchy design"
  - "SCP baseline guardrail"
  - "Control Tower landing zone"
  - "Account Factory vending"
  - "Config aggregator cross-account"
  - "Security Hub delegated admin"
  - "CloudTrail organization trail"
  - "IAM Identity Center permission set"
  - "Resource Explorer cross-account index"
  - "RAM resource share cross-account"
  - "deny leave organization SCP"
  - "audit account delegated admin"
  - "break-glass Identity Center"
routes_to: multi-account-governance-automator
---

# /aws:automate-multi-account-governance

Activate the `multi-account-governance-automator` skill and produce a
multi-account governance design (or validation report).

## What it does

Reads an org design intent (new, migrate, harden), account count target,
and compliance framework, and either:

1. **Designs** a complete governance baseline with: OU hierarchy (Security,
   Infrastructure, Workloads-Prod/NonProd, Sandbox, Suspended), root-level
   guardrail SCPs (deny-leave-org, deny-root-actions, deny-disable-
   guardduty, deny-delete-cloudtrail), region throttle and deny-list SCPs
   at workload OUs, Control Tower Landing Zone v2 with Account Factory,
   delegated administration (GuardDuty + Security Hub + Config aggregator
   + Access Analyzer in audit account), CloudTrail org trail to log-archive
   with org-scoped bucket and KMS policies, IAM Identity Center permission
   sets with break-glass path, Resource Explorer aggregator, and RAM
   cross-account shares scoped to org.
2. **Validates** an existing org governance posture against the mandatory
   baseline (root-level SCPs attached, delegation to audit not management,
   Config aggregator coverage across all members, Identity Center with
   break-glass, SCP inheritance reviewed).

Emits a deterministic block per design:

```text
STRUCTURE:
  Org status: <all-features | consolidated-billing-only>
  OU depth: <integer>
  Foundational accounts: audit=<id>, log-archive=<id>
  Management account MFA: <yes/no>
CONTROLS:
  - [PASS|FAIL] Root-level guardrail SCP attached
  - [PASS|FAIL] SCP denies organizations:LeaveOrganization
  - [PASS|FAIL] SCP denies root-account actions except IAM MFA setup
  - [PASS|FAIL] Region-throttle SCP attached at workload OU
  - [PASS|FAIL] SCP inheritance reviewed (Deny wins over Allow)
DELEGATION:
  - [PASS|FAIL] GuardDuty delegated to audit account <id>
  - [PASS|FAIL] Security Hub delegated to audit account <id>
  - [PASS|FAIL] Config aggregator in audit account (org source, AllRegions)
  - [PASS|FAIL] CloudTrail org trail to log-archive account
SHARING:
  - [PASS|FAIL] IAM Identity Center with permission sets
  - [PASS|FAIL] Break-glass path documented + tested
  - [PASS|FAIL] Resource Explorer aggregator index
  - [PASS|FAIL] RAM shares scoped to org (allow-external-principals=false)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  <numbered steps for fixing any FAIL findings>
```

## When to invoke

Provide an org design intent + account count and ask any of:

- "stand up a 50-account org with audit + log-archive, PCI compliance"
- "design SCP guardrails that block root account actions"
- "deploy a Control Tower landing zone with GuardDuty delegated to audit"
- "validate our existing org governance posture"
- "set up IAM Identity Center with a break-glass path"
- "configure a Config aggregator across all member accounts"

A bare org intent + account count + "govern" routes here via the
orchestrator.

## Inputs

- **Required:** org_design_intent (new | migrate | harden),
  account_count_target (integer).
- **Recommended:** compliance_framework (PCI | SOC | HIPAA | FedRAMP),
  audit_account_id, log_archive_account_id, landing_surface
  (control-tower | raw-organizations).
- **For validation mode:** existing org configuration (OU tree JSON,
  SCP policies JSON, delegation status, Config aggregator config).

## Outputs

- One VERDICT block per design (AUTOMATED or MANUAL_STEP_REQUIRED).
- The complete governance design (OU tree, SCP JSON, delegation commands,
  Identity Center permission sets, CloudTrail org trail config) in
  STRUCTURE/CONTROLS/DELEGATION/SHARING.
- Layer gate pass/fail per dimension in CONTROLS/DELEGATION/SHARING.
- Specific remediation steps for any failing gate in REMEDIATION.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Automate specialist for multi-account governance).
- `/aws:audit-organizations-scp` for auditing existing SCP posture
  (this skill designs automation; audit is interactive).
- `/aws:audit-cloudtrail-org-trail` for verifying the org trail config.
- `/aws:audit-config-recorder-coverage` for verifying Config aggregator
  coverage.
- `/aws:automate-tag-governance` for tag policy automation (complementary
  to this skill's SCP governance).
- `/aws:automate-iac-template` to generate the CloudFormation template
  that deploys the governance baseline.
