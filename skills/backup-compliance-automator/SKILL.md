---
name: backup-compliance-automator
description: 'Designs AWS Backup compliance automation across the four pillars: AWS Backup Audit Manager (audit framework, audit template, manual and automated controls), backup reporting (job summary report, compliance report, coverage report), legal hold automation (litigation hold via EventBridge on s3:ObjectSent to evidence locker, BackupLegalHold resource for immutable recovery points), cross-account / cross-region backup auditing via AWS Organizations backup vault, latest: AWS Backup Search (search across backups), Backup cost allocation tags. Includes AWS Backup Report Stream, Backup Audit Manager control library, and EventBridge Scheduler for periodic audit runs. Emits AUTOMATED with the compliance playbook or MANUAL_STEP_REQUIRED with the gap. Use when designing backup compliance, legal hold workflows, or cross-account backup audit.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws backup audit-manager create-framework / create-report-plan, aws backup start-backup-job / start-restore-job, aws backup create-legal-hold / start-legal-hold, aws backup create-backup-vault (cross-account), aws backup-gateway list-hypervisors (VMware), aws backup list-tags / tag-resource (cost allocation), aws backup search (Backup Search)...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Designing backup compliance automation, configuring AWS Backup Audit Manager frameworks and templates, building legal hold workflows, centralizing cross-account backup auditing, deploying Backup Search, configuring backup cost allocation tags, or automating compliance report generation on a schedule.
  when_not_to_use: Designing the backup plan itself (use backup-plan-auditor or operate-backup-vault — this skill audits compliance, not the plan)., Executing a restore (use rds-backup-restore-operator / ec2-backup-operator — this skill does not perform restores)., General storage cost optimization (use ebs-volume-optimizer or s3-storage-lens — Backup is one input)., Disaster recovery failover design (use dr-failover-automator — Backup is one DR input, not the strategy).
  activation_triggers: Backup compliance automation, Backup Audit Manager, audit framework, audit template, legal hold, litigation hold, Backup Vault Lock, compliance report, job summary report, cross-account backup audit, Backup Search, cost allocation tags backup, Backup Report Stream, EventBridge legal hold, Organizations backup vault
  invocation_schema: 'Input: either (a) a backup compliance requirement ("build a Backup Audit Manager framework for SOC2 with daily compliance reports and legal hold on demand"), OR (b) an existing Backup Audit Manager configuration / legal hold workflow / cross-account vault setup to audit and harden. Output: deterministic Backup compliance block per requirement — FRAMEWORK/REPORTING/LEGAL_HOLD/CROSS_ACCOUNT/SEARCH/ VERIFICATION/VERDICT — where VERDICT is AUTOMATED (compliance playbook complete with all gates passing) or MANUAL_STEP_REQUIRED (specific gap cited, e.g., no legal hold tested, audit framework missing control, cross-account vault not configured).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Backup, Backup Audit Manager, audit framework, audit template, compliance report, job summary report, coverage report, legal hold, litigation hold, immutability, Backup Vault Lock, cross-account backup, cross-region backup, AWS Organizations, Backup Search, cost allocation tags, backup reporting, Backup Report Stream, EventBridge Scheduler, control library
  tags: aws-backup, audit-manager, legal-hold, backup-vault, automate
---

# Backup Compliance Automator

## What this skill does

Designs automated AWS Backup compliance across the four pillars —
**Backup Audit Manager** (audit frameworks, audit templates, control
library with manual and automated controls), **backup reporting** (job
summary report, compliance report, coverage report, Backup Report Stream),
**legal hold automation** (BackupLegalHold resource for immutable recovery
points, EventBridge-triggered litigation hold), and **cross-account /
cross-region backup auditing** (AWS Organizations backup vault, delegated
administrator) — and the latest features: **AWS Backup Search** (search
across backups without restoring) and **Backup cost allocation tags**
(allocated spend per resource / vault / job).

The verdict is binary: **AUTOMATED** when the playbook covers a chosen
compliance framework with mapped controls, scheduled reporting, legal hold
tested (if applicable), cross-account centralization (for orgs), and
verification step; **MANUAL_STEP_REQUIRED** when any component is missing
(e.g., audit framework missing a control, no scheduled compliance report,
legal hold never tested, single-account-only vault in an org).

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-backup-compliance-spec-gate) | Starting any design — blocks unsafe specs |
| 2 | [Pillars overview](#backup-compliance-pillars) | The four pillars at a glance |
| 3 | [Backup Audit Manager](#backup-audit-manager-frameworks) | Framework, template, controls |
| 4 | [Backup reporting](#backup-reporting) | Job summary, compliance, coverage, Report Stream |
| 5 | [Legal hold](#legal-hold-automation) | BackupLegalHold, Vault Lock, EventBridge trigger |
| 6 | [Cross-account audit](#cross-account--cross-region-audit) | Organizations backup vault, delegated admin |
| 7 | [Backup Search](#aws-backup-search) | Search across backups without restore |
| 8 | [Cost allocation tags](#cost-allocation-tags) | Allocate spend per resource / vault |
| 9 | [EventBridge Scheduler](#eventbridge-scheduler-for-periodic-audits) | Periodic audit / report runs |
| 10 | [Step Functions orchestrator](#step-functions-compliance-orchestration) | Multi-step compliance state machine |
| 11 | [STRICT output contract](#output-format-strict-output-contract) | The exact Backup compliance block |
| 12 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of Backup taboos |
| 13 | [Expert heuristic](#expert-heuristic-callouts) | Non-obvious behaviors that change the design |
| 14 | [Recent AWS features](#recent-aws-features-2024-2026) | Backup Search, cost tags, Report Stream |
| 15 | [Edge cases](#edge-case-handling) | Vault Lock, control gaps, report freshness |

## Mindset

**One-line takeaway:** backup compliance is **auditable evidence that the
backup plan actually ran, the recovery points are immutable for the
required retention, and the legal hold chain of custody is intact**. A
backup plan that runs but produces no auditable evidence is, for
compliance purposes, no backup at all.

Mindset deep dives (Audit Manager evidence, legal hold vs Vault Lock, cross-account centralization) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when designing the compliance evidence chain.

## Pre-flight: Backup compliance spec gate (run before generation)

| Attribute | Required | Effect on plan |
|---|---|---|
| `compliance_framework` | YES | SOC2 / HIPAA / PCI / FedRAMP / custom — drives control selection |
| `resources_in_scope` | YES | Resource types (EC2, RDS, DynamoDB, EFS, S3, VMware, etc.) |
| `accounts_scope` | YES | Single-account OR organizational (delegated admin) |
| `retention_policy` | YES | Days/weeks/months/years, immutability requirement |
| `legal_hold_required` | Recommended | Yes / No — drives BackupLegalHold design |
| `existing_workflow` | For audit mode | When provided, run the layer gates |

**If the spec is incomplete**, output:

```text
FRAMEWORK: <unknown>
REPORTING: <unknown>
LEGAL_HOLD: <unknown>
CROSS_ACCOUNT: <unknown>
SEARCH: <unknown>
VERIFICATION: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - compliance_framework (SOC2 | HIPAA | PCI | FedRAMP | custom:<id>)
  - resources_in_scope (subset of [EC2, RDS, DynamoDB, EFS, FSx, S3, VMware, Storage Gateway])
  - accounts_scope (single | org)
  - retention_policy (e.g., 35d daily, 12m monthly, immutability yes/no)
REMEDIATION: Provide all required fields. Example: "build a SOC2 backup
audit framework for EC2 and RDS in our 30-account org with 35-day daily
retention and legal hold on demand" maps to compliance_framework=SOC2,
resources_in_scope=[EC2, RDS], accounts_scope=org, retention_policy=35d
daily immutable, legal_hold_required=yes.
```

Live-account pre-flight command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run these before generating any compliance playbook.

## Backup compliance pillars

| Pillar | Purpose | Primary mechanism |
|---|---|---|
| Backup Audit Manager | Continuous control evaluation against a framework | Audit framework + controls + audit template |
| Backup reporting | Periodic evidence export for auditors | Report plan (job summary, compliance, coverage) |
| Legal hold | Litigation-driven recovery point freeze | BackupLegalHold resource, Vault Lock |
| Cross-account / cross-region | Org-wide centralization | Organizations backup vault + delegated admin |

## Backup Audit Manager frameworks

```bash
# Use a managed framework as a starting point
aws backup audit-manager list-frameworks --query 'frameworks[*].[frameworkName,frameworkArn]'

# Create a custom framework
aws backup audit-manager create-framework \
  --framework-name soc2-backup-compliance \
  --framework-controls '[
    {"ControlName":"BACKUP_PLAN_EXISTENCE","ControlInputParameters":[]},
    {"ControlName":"BACKUP_REPORT_LAST_BACKUP_AGE","ControlInputParameters":[{"Name":"maxAgeInDays","Value":"1"}]},
    {"ControlName":"BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED","ControlInputParameters":[]},
    {"ControlName":"BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN","ControlInputParameters":[]}
  ]' \
  --framework-description "SOC2-aligned backup controls"
```

**Control categories (subset of the control library):**
| Control | What it checks |
|---|---|
| `BACKUP_PLAN_EXISTENCE` | Every resource type in scope has a backup plan |
| `BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN` | All resources in scope are tagged to a plan |
| `BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED` | Vault Lock prevents manual deletes |
| `BACKUP_RECOVERY_POINT_MINIMUM_RETENTION` | Retention meets the policy minimum |
| `BACKUP_REPORT_LAST_BACKUP_AGE` | Most recent recovery point is within maxAgeInDays |
| `BACKUP_REPORT_LAST_RESTORE_AGE` | Most recent restore is within maxAgeInDays (restore drill) |
| `BACKUP_RECOVERY_POINT_ENCRYPTED` | Recovery points are encrypted |
| `BACKUP_VARIANT_WITH_REGION_ISOLATION` | Cross-region copy exists for DR |

Gotcha detail (controls evaluate actual state; fixed control library) moved to [references/audit-manager-controls.md](references/audit-manager-controls.md).
Load it when a control fails despite a configured plan.

### Audit template
Audit template report-plan CLI moved to [references/audit-manager-controls.md](references/audit-manager-controls.md).
Load it when scheduling the framework compliance report.

## Backup reporting

| Report type | Report template | Purpose |
|---|---|---|
| Job summary | `JOB_SUMMARY` | Backup job success/failure counts over the period |
| Compliance | `COMPLIANCE` | Control evaluation results against a framework |
| Coverage | `COVERAGE` | Resources protected vs unprotected |

```bash
# Schedule a monthly compliance report
aws backup audit-manager create-report-plan \
  --report-plan-name monthly-compliance-report \
  --report-setting '{"ReportTemplate":"COMPLIANCE","Frameworks":["arn:aws:backup:us-east-1:111111111111:framework:soc2-backup-compliance"]}' \
  --reportDeliveryConfig={"S3BucketName":"backup-reports"} \
  --idempotencyToken "$(uuidgen)"
```

Backup Report Stream detail and reporting gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when near-real-time compliance detection is required.

## Legal hold automation

### BackupLegalHold resource (freezes specific recovery points)

```bash
aws backup create-legal-hold \
  --title "Acme v. Example - 2026-08-05" \
  --description "Litigation hold on EBS volumes for case #2026-CV-1234" \
  --legal-hold-status ACTIVE \
  --recovery-point-selection '{
    "ResourceIdentifiers":["arn:aws:ec2:us-east-1::volume/vol-0abc"],
    "DateRange":{"FromDate":"2026-08-01","ToDate":"2026-08-05"}
  }'
```

### Vault Lock (vault-wide retention immutability)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-vault \
  --min-retention-days 7 \
  --max-retention-days 365 \
  --changeable-for-days 3 \
  --mode LOCK_MODE
```

**Difference:** Vault Lock applies to ALL recovery points in the vault
forever (governance or compliance mode). Legal hold applies to specific
recovery points for the duration of the hold. Use Vault Lock for policy
immutability; use Legal Hold for litigation-driven freezes.

### EventBridge-triggered litigation hold
EventBridge rule + Lambda responder moved to [references/legal-hold-and-vault-lock.md](references/legal-hold-and-vault-lock.md).
Load it when automating litigation hold from a legal-team event.

## Cross-account / cross-region audit

For AWS Organizations, enable cross-account backup so a delegated
administrator account sees backups across all member accounts:

```bash
# In the management account: enable cross-account backup
aws organizations enable-aws-service-access \
  --service-principal backup.amazonaws.com

aws backup update-global-settings \
  --global-settings isCrossAccountBackupEnabled=true \
  --profile management-profile

# Delegate admin to a central audit account
aws organizations register-delegated-administrator \
  --account-id 222222222222 \
  --service-principal backup.amazonaws.com \
  --profile management-profile

# In the delegated admin: create the org-wide backup vault
aws backup create-backup-vault \
  --backup-vault-name org-compliance-vault \
  --profile delegated-admin-profile
```

Member-account COPY_ACTION plan moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when wiring member accounts to the org vault.

**Gotchas:** The org vault account must grant member accounts
`backup:CopyIntoBackupVault` via a vault access policy. Cross-region copy
adds to the per-job cost. The delegated admin can audit but cannot
restore from member-account recovery points without a role assumption.

## AWS Backup Search
Backup Search CLI and gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it for eDiscovery or incident-response search.

## Cost allocation tags
Cost-tag CLI and gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when allocating backup spend per project.

## EventBridge Scheduler for periodic audits
Scheduler + Lambda CLI moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when scheduling periodic Audit Manager runs.

## Step Functions compliance orchestration
Full Step Functions state machine moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when orchestrating multi-step compliance automation.

## Output format (STRICT output contract)

When this skill concludes a compliance design or audit, the agent MUST
respond with the block below using the literal all-caps labels `VAULT:`,
`VERDICT:`, `CHECKLIST:`, `FINDINGS:`, and `REMEDIATION:`. Do NOT
preface with prose, headings, or disclaimers — emit the block as the
first lines of the response. This contract is what assertion-based evals
and downstream compliance pipelines rely on; deviating from the literal
labels breaks automation silently.

### Decision tree — backup compliance evaluation

```text
Backup compliance request?
├── Designing a new compliance framework?
│     ├── Choose framework: CIS | NIST | SOC2 | HIPAA | PCI | FedRAMP | custom
│     ├── Map required controls from framework spec
│     ├── Configure Audit Manager framework with controls
│     ├── Set up reporting (compliance, job summary, coverage)
│     ├── Legal hold? → YES: BackupLegalHold + Vault Lock (LOCK_MODE)
│     ├── Cross-account? → YES: Organizations delegated admin + org vault
│     └── Verify: restore drill, cost tags, report freshness
├── Auditing existing backup compliance?
│     ├── Check framework exists and controls mapped
│     ├── Check backup frequency meets policy (last backup age)
│     ├── Check encryption on all recovery points
│     ├── Check retention meets minimum (Vault Lock)
│     ├── Check cross-region replication (DR requirement)
│     ├── Check legal hold tested (create + release cycle)
│     └── Check restore drill within required window
└── Gap found?
      ├── Missing control? → Add control to framework
      ├── Unencrypted recovery point? → CRITICAL — enable encryption
      ├── Vault Lock in GOVERNANCE mode? → Promote to LOCK_MODE
      ├── No restore drill? → Run drill, document RTO
      └── Stale report? → Re-run report plan, alarm on failures
```

### Output template

```text
VAULT: <vault-name> (<region>)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
CHECKLIST:
  [PASS|FAIL|N/A] Compliance framework: <CIS|NIST|SOC2|HIPAA|PCI|FedRAMP|custom> — <n> controls mapped, last evaluation <date>
  [PASS|FAIL|N/A] Backup frequency audit: last backup age <Xd>, max allowed <Xd> (<compliant|non-compliant>)
  [PASS|FAIL|N/A] Encryption verification: <n>/<n> recovery points encrypted
  [PASS|FAIL|N/A] Retention compliance: Vault Lock <LOCK_MODE|GOVERNANCE|none>, min <d>d max <d>d
  [PASS|FAIL|N/A] Cross-region replication: <configured|not configured>, destination <region>
  [PASS|FAIL|N/A] Legal hold: <tested|untested>, Vault Lock <mode>
  [PASS|FAIL|N/A] Restore drill: last <date>, RTO <duration> (within <required> window)
  [PASS|FAIL|N/A] Reporting: compliance report <freshness>, coverage report <configured|missing>
  [PASS|FAIL|N/A] Cost allocation tags: <active|inactive> in Cost Explorer
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  1. <step 1>
  2. <step 2>
```

### FORBIDDEN NEVER patterns (output contract)

1. **NEVER emit `VERDICT: AUTOMATED` when any `[FAIL]` is present in the
   checklist.** A single `[FAIL]` on any compliance pillar means the
   playbook has a gap. The verdict MUST be `MANUAL_STEP_REQUIRED` with
   the specific gap cited in FINDINGS and REMEDIATION.

2. **NEVER mark Encryption as `[PASS]` without confirming
   `BACKUP_RECOVERY_POINT_ENCRYPTED` control is in the framework AND all
   recovery points are encrypted.** An unencrypted recovery point is a
   compliance failure even if the backup ran successfully.

3. **NEVER mark Retention compliance as `[PASS]` when Vault Lock is in
   `GOVERNANCE` mode for a framework that requires immutability (HIPAA,
   NIST, PCI, FedRAMP).** GOVERNANCE mode allows root to override
   retention — only `LOCK_MODE` (compliance mode) satisfies immutability
   requirements.

4. **NEVER mark Restore drill as `[PASS]` without a documented restore
   within the required window (typically 90 days for NIST, 365 days for
   HIPAA).** A backup plan that never tested restores is unverified
   recovery capability.

5. **NEVER omit the FINDINGS section.** Even when
   `VERDICT: AUTOMATED`, informational findings (e.g., cost observations,
   minor warnings) MUST appear. An empty FINDINGS section implies the
   audit was not thorough.

6. **NEVER mark Legal hold as `[PASS]` if the create + release cycle has
   not been tested.** The team's first legal hold operation should not
   be under court deadline pressure. An untested legal hold is `[FAIL]`.

7. **NEVER list remediation steps without a corresponding FINDING.**
   Every REMEDIATION item MUST trace to a specific finding. Orphan
   remediation steps create confusion about what was actually broken.

### Perfect worked example — NIST compliance report with 3 non-compliant resources

```text
VAULT: nist-production-vault (us-east-1)
VERDICT: MANUAL_STEP_REQUIRED
CHECKLIST:
  [PASS] Compliance framework: NIST — 6 controls mapped (PLAN_EXISTENCE, RESOURCES_PROTECTED, MANUAL_DELETION_DISABLED, LAST_BACKUP_AGE 1d, RECOVERY_POINT_ENCRYPTED, VARIANT_WITH_REGION_ISOLATION), last evaluation 2026-08-11 02:00 UTC
  [FAIL] Backup frequency audit: 3 of 47 resources have last backup age > 24h (max allowed 1d) — non-compliant
  [PASS] Encryption verification: 47/47 recovery points encrypted (KMS key arn:aws:kms:us-east-1:123456789012:key/abc-123)
  [FAIL] Retention compliance: Vault Lock in GOVERNANCE mode — NIST requires LOCK_MODE (compliance mode) for immutability; min 7d max 365d
  [PASS] Cross-region replication: configured, destination us-west-2 (CopyAction in all backup plan rules)
  [PASS] Legal hold: tested 2026-07-22 (create + release on non-production recovery point, documented in runbook)
  [FAIL] Restore drill: last restore 2026-04-15 (> 90-day NIST window) — RTO unverified for current infrastructure
  [PASS] Reporting: compliance report 2026-08-11 (within 24h SLA), coverage report weekly, job summary weekly
  [PASS] Cost allocation tags: active in Cost Explorer (Project, Environment, Compliance, Workload)
FINDINGS:
  - [CRITICAL] Vault Lock in GOVERNANCE mode: root account can override retention.
    NIST SP 800-34 requires compliance mode (LOCK_MODE) where even root cannot
    bypass the lock. Affected: all 47 recovery points in nist-production-vault.
  - [HIGH] 3 resources have stale backups (> 24h since last recovery point):
    - i-0abc123def456 (EC2 instance, orders-api-prod-1): last backup 2026-08-09
    - db-def456ghi789 (RDS instance, payments-db): last backup 2026-08-10
    - vol-ghi789abc012 (EBS volume, cache-volume-prod): last backup 2026-08-08
    These resources are tagged for the backup plan but the plan has not produced
    a recovery point within the NIST-required daily window.
  - [HIGH] Restore drill overdue: last drill was 2026-04-15 (118 days ago).
    NIST SP 800-34 requires annual testing; internal policy requires 90-day
    cadence. RTO for current infrastructure is unverified.
REMEDIATION:
  1. Promote Vault Lock from GOVERNANCE to LOCK_MODE (irreversible — test on
     non-production vault first):
     aws backup put-backup-vault-lock-configuration \
       --backup-vault-name nist-production-vault \
       --min-retention-days 7 --max-retention-days 365 \
       --mode LOCK_MODE --changeable-for-days 3
  2. Investigate the 3 stale backup resources:
     aws backup list-recovery-points-by-resource --resource-arn arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456
     aws backup list-recovery-points-by-resource --resource-arn arn:aws:rds:us-east-1:123456789012:db:payments-db
     Verify the backup plan is active and on-demand backup job succeeds:
     aws backup start-backup-job --backup-vault-name nist-production-vault \
       --resource-arn arn:aws:ec2:us-east-1:123456789012:instance/i-0abc123def456 \
       --iam-role-arn arn:aws:iam::123456789012:role/AWSBackupDefaultServiceRole \
       --start-window-minutes 60 --complete-window-minutes 1440
  3. Run a restore drill on a tier-1 resource (e.g., payments-db) to a
     non-production VPC; document RTO and RPO. Target completion: 2026-08-19.
  4. Re-run the compliance report after remediation:
     aws backup start-report-job --report-plan-name nist-monthly-compliance
```

Key-details annotation moved to [references/worked-examples.md](references/worked-examples.md).
Load it to see why each NIST finding maps to its remediation.

### Worked example — AUTOMATED (all gates passing)
Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when all gates pass and the verdict is AUTOMATED.

**Self-check before emit:**
- [ ] VAULT name and region present?
- [ ] All 9 checklist rows present with [PASS|FAIL|N/A]?
- [ ] Any [FAIL] → VERDICT is MANUAL_STEP_REQUIRED (never AUTOMATED)?
- [ ] Every [FAIL] has a corresponding finding with severity?
- [ ] Every finding traces to a remediation step with CLI command?
- [ ] Encryption and Retention rows cite the specific control/mode?
- [ ] FINDINGS section is non-empty (at least one INFO)?

## NEVER (these things)

- NEVER run Vault Lock in GOVERNANCE mode when a compliance framework
  requires immutability. GOVERNANCE mode allows the root account to
  override retention — that defeats the purpose. Compliance frameworks
  (HIPAA, SOC2, PCI) require LOCK_MODE (compliance mode) where even root
  cannot bypass the lock.

- NEVER ship an Audit Manager framework without encryption controls. An
  unencrypted recovery point is a compliance failure even if the backup
  ran successfully. Always include
  `BACKUP_RECOVERY_POINT_ENCRYPTED` for any framework touching regulated
  data.

- NEVER skip the legal hold test. The team's first legal hold should not
  be under court deadline pressure. Run a create + release cycle on a
  non-production recovery point quarterly; document the runbook with the
  case-ID convention.

- NEVER assume per-account backup plans satisfy an org-wide compliance
  requirement. Without cross-account centralization, the auditor has no
  single view; member-account drift (stale recovery points, missing tags)
  goes undetected. The Organizations delegated admin + org vault is the
  canonical centralization pattern.

- NEVER auto-remediate by deleting recovery points. A "stale" recovery
  point may be subject to a legal hold the auto-remediation logic does not
  know about. Auto-remediation should be additive (back up the forgotten
  resource) — destructive actions need human approval.

## Expert heuristic callouts
All ten expert-heuristic callouts moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it for the non-obvious behaviors that change a design.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing legal hold
  operation (`create-legal-hold`, `delete-legal-hold`,
  `put-backup-vault-lock-configuration` in LOCK_MODE), emit: `CONFIRM:
  About to <action> for <case / vault>. LOCK_MODE is irreversible.
  Proceed? (yes/no)` and wait for explicit `yes`.
- **LOCK_MODE is irreversible.** Once Vault Lock is in LOCK_MODE past the
  `changeable-for-days` window, it cannot be removed. Test in GOVERNANCE
  mode first, then promote.
- **Verify the legal hold case-ID convention.** Every hold title must
  include the case ID for traceability.
- **Verify cross-account vault access policy.** Member accounts must have
  `backup:CopyIntoBackupVault` before their plans can copy.
- **Verify cost tag activation.** `aws ce get-cost-and-usage` should show
  the tag as a dimension.

## Edge-case handling
Edge-case catalog moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it on GOVERNANCE-to-LOCK_MODE migration, control gaps, or report drift.

## Recent AWS features (2024-2026)
Feature detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when scoping Backup Search, cost tags, or Report Stream.

## References (load on demand)

- [Audit Manager controls](references/audit-manager-controls.md) — control library detail, audit-template report-plan CLI, controls-evaluate-actual-state gotcha
- [Legal hold and Vault Lock](references/legal-hold-and-vault-lock.md) — BackupLegalHold lifecycle, LOCK_MODE configuration, end-to-end litigation hold incl. EventBridge rule + Lambda responder
- [Worked examples](references/worked-examples.md) — AUTOMATED (all gates passing) example + key-details annotation of the NIST example
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight checks
- [Advanced patterns](references/advanced-patterns.md) — mindset deep dives, Report Stream, member-account copy plan, Backup Search, cost tags, EventBridge Scheduler, Step Functions orchestration, expert heuristics, edge cases, recent AWS features

## Domain

AWS CloudOps / Backup Compliance Automation.

## AWS documentation

- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/
- **AWS Backup Audit Manager** — https://docs.aws.amazon.com/aws-backup/latest/devguide/audit-manager.html
- **AWS Backup legal hold** — https://docs.aws.amazon.com/aws-backup/latest/devguide/legal-holds.html
- **AWS Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **AWS Backup cross-account / cross-region** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-account-backup.html
- **AWS Backup Search** — https://docs.aws.amazon.com/aws-backup/latest/devguide/search.html
- **AWS Backup reporting** — https://docs.aws.amazon.com/aws-backup/latest/devguide/backup-reporting.html
- **AWS Organizations delegated administrator** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_integrate_services.html
- **AWS Backup cost allocation tags** — https://docs.aws.amazon.com/aws-backup/latest/devguide/tagging.html

