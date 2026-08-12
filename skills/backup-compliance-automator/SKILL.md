---
name: backup-compliance-automator
description: >-
  Designs AWS Backup compliance automation across the four pillars: AWS
  Backup Audit Manager (audit framework, audit template, manual and
  automated controls), backup reporting (job summary report, compliance
  report, coverage report), legal hold automation (litigation hold via
  EventBridge on s3:ObjectSent to evidence locker, BackupLegalHold resource
  for immutable recovery points), cross-account / cross-region backup
  auditing via AWS Organizations backup vault, latest: AWS Backup Search
  (search across backups), Backup cost allocation tags. Includes AWS
  Backup Report Stream, Backup Audit Manager control library, and
  EventBridge Scheduler for periodic audit runs. Emits AUTOMATED with the
  compliance playbook or MANUAL_STEP_REQUIRED with the gap. Use when
  designing backup compliance, legal hold workflows, or cross-account
  backup audit.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan authoring. Live deployment
  uses aws backup audit-manager create-framework / create-report-plan,
  aws backup start-backup-job / start-restore-job,
  aws backup create-legal-hold / start-legal-hold,
  aws backup create-backup-vault (cross-account),
  aws backup-gateway list-hypervisors (VMware),
  aws backup list-tags / tag-resource (cost allocation),
  aws backup search (Backup Search),
  aws events put-rule / put-targets (legal hold triggers),
  aws organizations list-delegated-administrators
  (backup-gateway delegated admin) — AWS CLI v2, SSO or key-based,
  Organizations backup vault access role.
keywords:
  - AWS Backup
  - Backup Audit Manager
  - audit framework
  - audit template
  - compliance report
  - job summary report
  - coverage report
  - legal hold
  - litigation hold
  - immutability
  - Backup Vault Lock
  - cross-account backup
  - cross-region backup
  - AWS Organizations
  - Backup Search
  - cost allocation tags
  - backup reporting
  - Backup Report Stream
  - EventBridge Scheduler
  - control library
tags:
  - aws-backup
  - audit-manager
  - legal-hold
  - backup-vault
  - automate
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: >-
    Designing backup compliance automation, configuring AWS Backup Audit
    Manager frameworks and templates, building legal hold workflows,
    centralizing cross-account backup auditing, deploying Backup Search,
    configuring backup cost allocation tags, or automating compliance
    report generation on a schedule.
  when_not_to_use:
    - Designing the backup plan itself (use backup-plan-auditor or operate-backup-vault — this skill audits compliance, not the plan).
    - Executing a restore (use rds-backup-restore-operator / ec2-backup-operator — this skill does not perform restores).
    - General storage cost optimization (use ebs-volume-optimizer or s3-storage-lens — Backup is one input).
    - Disaster recovery failover design (use dr-failover-automator — Backup is one DR input, not the strategy).
  activation_triggers:
    - "Backup compliance automation"
    - "Backup Audit Manager"
    - "audit framework"
    - "audit template"
    - "legal hold"
    - "litigation hold"
    - "Backup Vault Lock"
    - "compliance report"
    - "job summary report"
    - "cross-account backup audit"
    - "Backup Search"
    - "cost allocation tags backup"
    - "Backup Report Stream"
    - "EventBridge legal hold"
    - "Organizations backup vault"
  invocation_schema: >-
    Input: either (a) a backup compliance requirement ("build a Backup
    Audit Manager framework for SOC2 with daily compliance reports and
    legal hold on demand"), OR (b) an existing Backup Audit Manager
    configuration / legal hold workflow / cross-account vault setup to
    audit and harden. Output: deterministic Backup compliance block per
    requirement — FRAMEWORK/REPORTING/LEGAL_HOLD/CROSS_ACCOUNT/SEARCH/
    VERIFICATION/VERDICT — where VERDICT is AUTOMATED (compliance
    playbook complete with all gates passing) or MANUAL_STEP_REQUIRED
    (specific gap cited, e.g., no legal hold tested, audit framework
    missing control, cross-account vault not configured).
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

- **Audit Manager turns "trust me, backups work" into "here is the
  evidence."** A compliance report exported by Audit Manager is the
  artifact you hand to an auditor. A backup job success in the console is
  not.
- **Legal hold and Vault Lock are different mechanisms.** Vault Lock
  enforces retention policy immutability at the vault level. Legal hold
  (BackupLegalHold resource) freezes specific recovery points (e.g., the
  state of every EBS volume the day litigation was filed). They are
  complementary, not interchangeable.
- **Cross-account centralization is the only way to audit at org scale.**
  A per-account backup plan with no central view means an auditor has to
  log into 50 accounts to see evidence. The Organizations backup vault +
  delegated admin is the canonical pattern.

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

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify AWS Backup is enabled: `aws backup list-backup-plans`.
2. Verify Audit Manager is enabled: `aws backup audit-manager list-frameworks`.
3. For org: verify backup delegated admin: `aws organizations list-delegated-administrators --service-principal backup.amazonaws.com`.
4. Verify backup vault: `aws backup list-backup-vaults`.
5. Verify Backup Search (if applicable): `aws backup search list-backup-plans` (available in supported regions).

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

**Gotchas:** Controls are evaluated against actual AWS Backup state, not
against the plan. A control `BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN`
fails if a resource is tagged for a plan but the plan never produced a
recovery point. The control library is fixed by AWS — custom controls
require Lambda-backed manual controls.

### Audit template

```bash
aws backup audit-manager create-report-plan \
  --report-plan-name soc2-monthly-compliance \
  --report-plan-description "Monthly SOC2 backup compliance report" \
  --report-setting '{"ReportTemplate":"COMPLIANCE","Frameworks":["arn:aws:backup:us-east-1:111111111111:framework:soc2-backup-compliance"]}' \
  --reportDeliveryConfig={"S3BucketName":"backup-compliance-reports","S3KeyPrefix":"soc2/2026/"} \
  --idempotencyToken "$(uuidgen)"
```

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

**Backup Report Stream (2024-2025):** Streams backup job state changes to
EventBridge in real time, enabling near-real-time compliance detection
instead of waiting for the next report run.

```bash
# EventBridge rule for Backup Report Stream
aws events put-rule --name backup-report-stream \
  --event-pattern '{"source":["aws.backup"],"detail-type":["Backup Job State Change"]}' \
  --state ENABLED
```

**Gotchas:** Reports land in S3 as JSON; downstream tooling (Lambda +
QuickSight / Athena) is needed for human-readable dashboards. Report runs
incur Audit Manager costs per evaluation.

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

```bash
# Trigger legal hold on a custom event (e.g., from the legal team)
aws events put-rule --name trigger-litigation-hold \
  --event-pattern '{"source":["custom.legal"],"detail-type":["Litigation Hold Request"]}' \
  --state ENABLED

aws events put-targets --rule trigger-litigation-hold \
  --targets '[{"Id":"HoldResponder","Arn":"arn:aws:lambda:us-east-1:111111111111:function:create-legal-hold"}]'
```

**Lambda responder (excerpt):**

```python
import boto3, os
backup = boto3.client('backup')

def lambda_handler(event, context):
    detail = event['detail']
    backup.create_legal_hold(
        Title=detail['caseName'],
        Description=detail['caseDescription'],
        LegalHoldStatus='ACTIVE',
        RecoveryPointSelection={
            'ResourceIdentifiers': detail['resourceArns'],
            'DateRange': {
                'FromDate': detail['incidentDateStart'],
                'ToDate': detail['incidentDateEnd']
            }
        }
    )
    return {'statusCode': 200, 'hold': 'created'}
```

**Gotchas:** Legal holds cannot be bypassed — even the root account
cannot delete a held recovery point. Always include the case ID in the
hold title for traceability. Test release (status -> INACTIVE) before
needing it under court deadline pressure.

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

Member accounts add a `COPY_ACTION` to their backup plan targeting the
org vault:

```bash
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName":"cross-account-daily",
  "Rules":[{
    "RuleName":"DailyToOrgVault",
    "TargetBackupVaultName":"Default",
    "ScheduleExpression":"cron(0 5 ? * * *)",
    "CopyActions":[{
      "DestinationBackupVaultArn":"arn:aws:backup:us-east-1:222222222222:backup-vault:org-compliance-vault",
      "Lifecycle":{"DeleteAfterDays":35}
    }]
  }]
}'
```

**Gotchas:** The org vault account must grant member accounts
`backup:CopyIntoBackupVault` via a vault access policy. Cross-region copy
adds to the per-job cost. The delegated admin can audit but cannot
restore from member-account recovery points without a role assumption.

## AWS Backup Search

AWS Backup Search (2024-2025) enables searching across backups without
restoring each one first — useful for eDiscovery and incident response.

```bash
# Initiate a search across all backups in scope
aws backup search start-search-job \
  --search-scope '{
    "BackupVaultNames":["production-vault","org-compliance-vault"],
    "ResourceTypes":["EBS","S3","DynamoDB"]
  }' \
  --search-term "confidential" \
  --filters '{"LastRestoreDateBefore":"2026-08-01"}'
```

**Gotchas:** Search incurs cost per GB scanned; scope searches tightly.
Search results are exported to S3 (not returned inline). Pair with legal
hold for eDiscovery workflows (search -> hold matching recovery points).

## Cost allocation tags

```bash
# Tag a backup vault for cost allocation
aws backup tag-resource \
  --resource-arn arn:aws:backup:us-east-1:111111111111:backup-vault:production-vault \
  --tags '{"Project":"acme-platform","Environment":"production","Compliance":"SOC2"}'

# Tag a backup job (cost flows to the resource)
aws backup tag-resource \
  --resource-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-xxx \
  --tags '{"Project":"acme-platform","Workload":"orders-api"}'
```

After activation in Billing, tags flow to AWS Cost Explorer for per-project
backup spend allocation.

**Gotchas:** Tags on backup jobs propagate from the source resource if
`BackupPlan` includes copy-backup-tags; otherwise tag explicitly. Vault
tags do not propagate to recovery points — tag both.

## EventBridge Scheduler for periodic audits

Schedule Audit Manager evaluations to run on a cadence (e.g., daily at
2am UTC):

```bash
aws scheduler create-schedule \
  --name backup-audit-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"Arn":"arn:aws:lambda:us-east-1:111111111111:function:run-audit-manager","RoleArn":"arn:aws:iam::111111111111:role/SchedulerInvokeRole"}'
```

**Lambda target:**

```python
import boto3
backup = boto3.client('backup')

def lambda_handler(event, context):
    # Trigger the report plan run, which also re-evaluates controls
    backup.start-report-job(report_plan_name='monthly-compliance-report')
    return {'statusCode': 200}
```

## Step Functions compliance orchestration

For multi-step compliance (e.g., daily audit -> evaluate findings ->
auto-remediate or escalate -> export report -> notify Slack):

```json
{
  "StartAt": "RunAudit",
  "States": {
    "RunAudit": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:run-audit-manager",
      "Next": "GetFindings"
    },
    "GetFindings": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {"FunctionName": "get-audit-findings"},
      "Next": "FindingsChoice"
    },
    "FindingsChoice": {
      "Type": "Choice",
      "Choices": [
        {"Variable": "$.criticalCount", "NumericGreaterThan": 0, "Next": "PageOnCall"},
        {"Variable": "$.nonCompliantCount", "NumericGreaterThan": 0, "Next": "AutoRemediate"}
      ],
      "Default": "ExportReport"
    },
    "AutoRemediate": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:auto-remediate-backup-gap",
      "Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 60, "MaxAttempts": 3}],
      "Next": "ExportReport"
    },
    "PageOnCall": {
      "Type": "Task",
      "Resource": "arn:aws:sns:<region>:<account>:backup-critical-alerts",
      "Next": "ExportReport"
    },
    "ExportReport": {
      "Type": "Task",
      "Resource": "arn:aws:states:::backup:startReportJob",
      "Next": "NotifySlack"
    },
    "NotifySlack": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<region>:<account>:function:notify-slack-backup",
      "End": true
    }
  }
}
```

**Gotchas:** Auto-remediation should be conservative — backing up a
forgotten resource is fine; deleting a stale recovery point is not. Gate
destructive actions behind a human approval (task token).

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

**Key details in this example:**

- **3 non-compliant resources** identified by resource ARN with last
  backup date for each.
- **Vault Lock GOVERNANCE vs LOCK_MODE** is the critical finding — NIST
  requires immutability that GOVERNANCE mode does not provide.
- **Restore drill overdue** by 28 days (118 days since last drill vs
  90-day policy). This is a separate finding from the stale backups.
- **FINDINGS severity** drives remediation priority: CRITICAL before
  HIGH, with specific CLI commands for each.

### Worked example — AUTOMATED (all gates passing)

```text
VAULT: soc2-production-vault (us-east-1)
VERDICT: AUTOMATED
CHECKLIST:
  [PASS] Compliance framework: SOC2 — 5 controls mapped, last evaluation 2026-08-11 02:00 UTC
  [PASS] Backup frequency audit: all 62 resources have last backup age <= 24h
  [PASS] Encryption verification: 62/62 recovery points encrypted
  [PASS] Retention compliance: Vault Lock LOCK_MODE, min 7d max 365d
  [PASS] Cross-region replication: configured, destination us-west-2
  [PASS] Legal hold: tested 2026-07-15 (create + release cycle documented)
  [PASS] Restore drill: last 2026-07-20, RTO 35min for EBS 1TB (within 90-day window)
  [PASS] Reporting: compliance report 2026-08-11 (within 24h SLA), coverage + job summary weekly
  [PASS] Cost allocation tags: active (Project, Environment, Compliance)
FINDINGS:
  - [INFO] Cross-region copy adds ~12% to per-job cost
  - [WARN] One member account (333333333333) missing cost tag: Project
REMEDIATION:
  1. Add Project tag to backup jobs in account 333333333333
```

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

- **Vault Lock GOVERNANCE vs COMPLIANCE is the most-confused distinction.**
  GOVERNANCE mode lets root override (with `s3:PutBucketObjectLock`
  privileges). COMPLIANCE mode (LOCK_MODE) blocks everyone, including
  root. For regulated workloads, LOCK_MODE is the only acceptable answer.
- **Audit Manager controls are read-only against actual state.** A control
  does not modify the backup plan — it reports whether the plan is in
  compliance. Remediation is a separate step (Lambda or human).
- **Cross-account backup requires `backup:CopyIntoBackupVault` on the
  destination vault.** Member accounts cannot copy into the org vault
  without it. The vault access policy is the linchpin.
- **Backup Report Stream events are best-effort.** For compliance evidence,
  rely on the scheduled Audit Manager report; the stream is for real-time
  alerting, not for audit-grade evidence.
- **Legal hold release does not delete the recovery point.** Setting
  `LegalHoldStatus=INACTIVE` frees the recovery point to age out per the
  vault retention — it does not immediately delete. Test this to avoid
  confusion during litigation.
- **Cost allocation tags need activation in Billing.** Tagging a vault is
  not enough — the tag must be activated as a cost allocation tag in the
  Billing console before it appears in Cost Explorer.
- **Backup Search cost is per GB scanned.** A broad search across years of
  backups can be expensive. Scope tightly (vault, resource type, date
  range).
- **The `BACKUP_REPORT_LAST_RESTORE_AGE` control validates restore drills.**
  It checks that a restore was actually performed within the configured
  window. A backup plan that never tested restores fails this control.
- **Org vault account is region-specific.** A vault in us-east-1 does not
  cover member resources in eu-west-1 unless member plans add a
  cross-region copy action.
- **Audit Manager has a per-evaluation cost.** Daily evaluations across
  hundreds of resources add up. Balance cadence against cost; daily for
  critical, weekly for the rest.

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

- **GOVERNANCE to LOCK_MODE migration.** Switch from governance to
  compliance mode during a maintenance window — once LOCK_MODE passes the
  `changeable-for-days` cool-down, retention is forever. Test with a
  non-production vault first.
- **Control gap for resource types not in the library.** AWS does not
  provide a control for every resource type (e.g., custom applications on
  EC2). Use a Lambda-backed manual control to fill the gap.
- **Report freshness drift.** A scheduled report may silently fail if the
  S3 bucket policy changes. Alarm on report job failure.
- **Member account drift.** A member account's backup plan may be modified
  out-of-band. Use Audit Manager controls to detect drift; do not assume
  the plan is current.
- **Legal hold conflict with lifecycle.** A held recovery point does not
  age out per the vault lifecycle. Holds override retention; release
  explicitly when litigation closes.
- **Backup Search region availability.** Search is not available in all
  regions; verify before scoping eDiscovery workflows.

## Recent AWS features (2024-2026)

- **AWS Backup Search (2024-2025):** Search across backups without
  restoring each one. Pairs with legal hold for eDiscovery.
- **Backup cost allocation tags (2024-2025):** Tag vaults and jobs for per-project cost allocation in Cost Explorer.
- **Backup Report Stream (2024-2025):** Real-time job state changes via
  EventBridge; enables near-real-time compliance detection.
- **Backup Audit Manager control library expansion (2024-2025):** New
  controls for cross-region isolation, restore drill age, and encryption.
- **Cross-account backup with AWS Organizations (2024-2025):** Delegated
  administrator pattern centralizes backup auditing across all member
  accounts.
- **Legal hold improvements (2024-2025):** Programmatic create / release
  via API + EventBridge; case-ID field in the hold title.
- **EventBridge Scheduler integration (2024-2025):** Serverless cron for periodic Audit Manager evaluations.
- **Backup continuous backup (Point-in-Time Recovery) (2024-2025):** PITR for supported resources; the `BACKUP_REPORT_LAST_BACKUP_AGE` control validates PITR freshness.

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
