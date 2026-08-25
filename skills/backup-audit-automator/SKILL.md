---
name: backup-audit-automator
description: 'Automates AWS Backup audit and compliance reporting with production defaults: backup report plan creation (daily/weekly compliance reports), report templates (BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT), report destination (S3 bucket delivery), compliance framework mapping (CIS, NIST, SOC2), backup frequency audit (identify resources without backup plans), encryption verification (KMS key on all recovery points), retention compliance (minimum retention days enforcement), cross-region replication audit, Vault Lock compliance check (compliance mode is immutable, governance mode is not), automated alerting for non-compliance (SNS), and multi-account via AWS Organizations. Emits an AUTOMATION_DEPLOYED checklist. Use when auditing backup compliance, creating backup report plans, checking encryption on recovery. Triggers: backup audit, backup compliance report, backup report plan, vault lock check, backup encryption audit, backup retention compliance, backup frequency audit, recovery point report.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with backup and s3 access. Works with Terraform aws_backup_report_plan, aws_backup_vault, and aws_cloudwatch_event_rule resources and CloudFormation AWS::Backup::BackupPlan templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, backup, audit, cloudops, automate, storage, compliance, vault-lock, reporting, sns
  dependencies: aws-orchestrator
  keywords: aws, backup, audit, compliance, report plan, vault lock, encryption audit, retention compliance, backup frequency, recovery point, cloudops, automate, sns alerting
  when_to_use: Invoke when the user wants to automate AWS Backup auditing and compliance — creating backup report plans, checking encryption on recovery points, verifying Vault Lock status, identifying resources without backup coverage, setting up automated compliance alerts via SNS, or mapping to compliance frameworks (CIS, NIST, SOC2). Do NOT invoke for creating backup plans themselves (use backup-plan skills), restoring from backups (use backup-restore skills), or AWS Backup pricing analysis.
---

# Backup Audit Automator

An AWS CloudOps agent skill that automates AWS Backup audit and
compliance reporting with correct defaults. The skill walks the
operator through backup report plan creation, report template
selection, compliance framework mapping, encryption verification,
retention compliance, Vault Lock status checking, cross-region
replication auditing, and automated non-compliance alerting via SNS,
captures audit scope and compliance requirements, explains why each
default matters, and emits an AUTOMATION_DEPLOYED checklist with copy-
pasteable verification commands.

## Activation keywords

backup audit, backup compliance report, backup report plan, vault lock
check, backup encryption audit, backup retention compliance, backup
frequency audit, recovery point report.

## STRICT output contract

When this skill is invoked with a backup audit/automation request
(create a report plan, check compliance, set up alerting, verify
encryption, check Vault Lock, or a partial configuration), the agent
MUST respond with the AUTOMATION_DEPLOYED checklist defined in the
"Output format" section using the literal all-caps labels
`BACKUP_AUDIT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
automation pipelines rely on; deviating from the literal labels breaks
automation silently.

If any review is required before deployment, the verdict is
`REVIEW_REQUIRED` with a specific gap citation in the checklist
(marked `[x]`), and `AUTOMATION_DEPLOYED` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before automating |
| Step 1 — Report plan creation | Core automation |
| Step 2 — Report templates (3 types) | Template selection |
| Step 3 — S3 report destination | Delivery config |
| Step 4 — Compliance framework mapping | CIS/NIST/SOC2 |
| Step 5 — Backup frequency audit | Coverage gaps |
| Step 6 — Encryption verification | KMS on recovery points |
| Step 7 — Retention compliance | Minimum retention days |
| Step 8 — Vault Lock compliance check | Immutable vs governance |
| Step 9 — Cross-region replication audit | DR readiness |
| Step 10 — Automated SNS alerting and multi-account | Alerting |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/report-templates-and-frameworks.md | Template detail |
| references/vault-lock-and-encryption.md | Vault Lock + encryption detail |

## Mindset

**One-line takeaway:** AWS Backup report plans deliver compliance
reports (CSV/JSON) to S3 on a schedule. Backup compliance reports
identify resources WITHOUT backup coverage. Vault Lock compliance mode
is immutable (cannot be deleted or changed); governance mode is NOT
immutable (can be overridden by privileged users). Every recovery
point should have KMS encryption verified.

Deep-dive misconceptions moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when explaining coverage gaps, Vault Lock modes, or encryption defaults.

## Configuration dependency graph (novel heuristic)

Backup audit configurations are NOT independent. The S3 destination
must exist before report plans can deliver. Report plans must be
created before they produce reports. Vault Lock status must be verified
before claiming compliance. Use this graph to sequence automation.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| S3 destination bucket | Bucket exists; bucket policy allows backup service write | reports delivered as CSV/JSON to S3 prefix | report delivery |
| Report plan | S3 destination exists; report template selected | report plan creates reports on schedule (daily/weekly/monthly) | compliance reports |
| Report template | Report plan exists | 3 types: BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT | report content |
| Compliance framework mapping | Report plan exists; framework identified | mapping is advisory (does not enforce); identifies which controls map to CIS/NIST/SOC2 | framework alignment |
| Encryption audit | Backup vaults exist; recovery points exist | audit checks if KMS key is present on each recovery point | encryption compliance |
| Retention compliance | Backup plans exist | audit checks if retention period meets minimum threshold | retention policy |
| Vault Lock check | Backup vault exists | compliance mode = immutable; governance mode = overridable | regulatory compliance |
| SNS alerting | SNS topic exists; subscription confirmed | alerts fire on non-compliance detection | automated notification |

**The Vault Lock mode distinction row is the one a baseline model
misses.** Compliance mode and governance mode look similar in the API
but have fundamentally different immutability properties. The procedure
below forces an explicit check of the Vault Lock mode.

Cross-dependency gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when report delivery or SNS alerting fails silently.

## Expert heuristic: report plan types and when to use each
Full heuristic moved to [references/report-templates-and-frameworks.md](references/report-templates-and-frameworks.md).
Load it when choosing among the three report templates.

## Expert heuristic: Vault Lock compliance vs governance
Full heuristic moved to [references/vault-lock-and-encryption.md](references/vault-lock-and-encryption.md).
Load it before claiming Vault Lock compliance.

## Expert heuristic: encryption audit checks KMS key presence
Full heuristic moved to [references/vault-lock-and-encryption.md](references/vault-lock-and-encryption.md).
Load it when auditing recovery-point encryption.

## Prerequisites (verify before automating)

Before emitting automation commands, verify these prerequisites. If
any are missing, the verdict is **REVIEW_REQUIRED**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Backup vaults exist | Audits target specific vaults | `aws backup list-backup-vaults` |
| S3 bucket for report delivery exists | Reports deliver to S3 | `aws s3 ls s3://backup-reports-bucket` |
| S3 bucket policy allows backup service write | Without it, reports not delivered | Verify `backup.amazonaws.com` write permission |
| SNS topic exists (for alerting) | Alerts publish to SNS | `aws sns list-topics` |
| Backup plans exist | Audit checks coverage against plans | `aws backup list-backup-plans` |
| KMS keys identified (for encryption audit) | Verify recovery point encryption | `aws kms list-keys` |
| Compliance framework identified | Determines which controls to map | Confirm CIS/NIST/SOC2/etc. |
| AWS Organizations setup (for multi-account) | Multi-account audit requires Orgs | `aws organizations describe-organization` |

If any prerequisite is missing, output
`VERDICT: REVIEW_REQUIRED` and cite the specific gap.

## Step 1 — Report plan creation

Create a backup report plan that delivers reports to S3 on a schedule.

```bash
aws backup create-report-plan \
  --report-plan-name "daily-compliance-report" \
  --report-template-body '{"ReportTemplate":{"Type":"COMPLIANCE_REPORT","Format":"CSV","ReportName":"daily-compliance"}}' \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/compliance/"}' \
  --report-setting "{\"ReportTemplate":"COMPLIANCE_REPORT","Frameworks":["CIS_AWS_1.4","NIST_800_53"]}" \
  --start-report-creation
```

**S3 bucket policy for backup report delivery:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "backup.amazonaws.com" },
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::backup-reports-bucket/reports/*"
    }
  ]
}
```

## Step 2 — Report templates (3 types)

| Template | Content | Use case |
|---|---|---|
| BACKUP_JOB_REPORT | Job status, duration, resource type, vault | Operational health of backup jobs |
| COMPLIANCE_REPORT | Resources with/without coverage, plan mapping | Compliance gap analysis |
| RECOVERY_POINT_REPORT | Recovery point ARN, encryption, vault, dates | Recovery point audit |

**Create all three report plans:**

```bash
for TEMPLATE in BACKUP_JOB_REPORT COMPLIANCE_REPORT RECOVERY_POINT_REPORT; do
  aws backup create-report-plan \
    --report-plan-name "daily-${TEMPLATE,,}-report" \
    --report-setting "{\"ReportTemplate\":\"$TEMPLATE\",\"Frameworks\":[]}" \
    --report-delivery-channel "{\"S3BucketName\":\"backup-reports-bucket\",\"S3KeyPrefix\":\"reports/${TEMPLATE,,}/\"}"
done
```

## Step 3 — S3 report destination

Reports deliver to S3 as CSV or JSON files. The destination bucket
must have the correct policy.

```bash
# Verify S3 bucket
aws s3api get-bucket-policy --bucket backup-reports-bucket

# Check recent reports
aws s3 ls s3://backup-reports-bucket/reports/compliance/ --recursive | tail -5
```

## Step 4 — Compliance framework mapping

Map backup audit controls to compliance frameworks:

| Framework | Relevant Backup Controls |
|---|---|
| CIS AWS 1.4 | 3.5 (ensure S3 buckets have backup), 3.7 (ensure EBS volumes have backup) |
| NIST 800-53 | CP-9 (system backup), CP-10 (system recovery), SC-28 (protection at rest) |
| SOC 2 | CC9.1 (availability), CC6.1 (security), A1.2 (environmental protections) |

```bash
# Create report plan with framework mapping
aws backup create-report-plan \
  --report-plan-name "cis-compliance-report" \
  --report-setting "{\"ReportTemplate\":\"COMPLIANCE_REPORT\",\"Frameworks\":[\"CIS_AWS_1.4\"]}" \
  --report-delivery-channel '{"S3BucketName":"backup-reports-bucket","S3KeyPrefix":"reports/cis/"}'
```

## Step 5 — Backup frequency audit

Identify resources NOT covered by any backup plan.

```bash
# List all backup plans
aws backup list-backup-plans --query 'BackupPlansList[*].BackupPlanName' --output table

# List resources covered by backup plans (via backup selections)
aws backup list-backup-selections \
  --backup-plan-id <plan-id> \
  --query 'BackupSelectionsList[*].SelectionName'

# Use COMPLIANCE_REPORT to identify uncovered resources
aws backup start-report-job --report-plan-name "daily-compliance-report"
```

**The compliance report lists resources WITHOUT coverage.** These are
the audit findings that need remediation.

## Step 6 — Encryption verification

Verify that all recovery points have KMS encryption.

```bash
# List recovery points without KMS encryption
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name "default" \
  --query 'RecoveryPoints[?EncryptionKeyArn==`null`].{ARN:RecoveryPointArn,Resource:ResourceType}' \
  --output table

# List recovery points WITH KMS encryption
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name "default" \
  --query 'RecoveryPoints[?EncryptionKeyArn!=`null`].{ARN:RecoveryPointArn,Key:EncryptionKeyArn}' \
  --output table
```

**Any recovery point without an EncryptionKeyArn is a finding.**

## Step 7 — Retention compliance

Check that backup retention periods meet the minimum required days.

```bash
# List backup plan rules with retention
aws backup get-backup-plan \
  --backup-plan-id <plan-id> \
  --query 'BackupPlan.Rules[*].{Rule:RuleName,Lifecycle:Lifecycle.DeleteAfterDays}' \
  --output table

# Compare retention days against minimum threshold
# Example: minimum 35 days for daily backups
```

## Step 8 — Vault Lock compliance check

Verify Vault Lock mode (compliance vs governance).

```bash
# Check Vault Lock configuration
aws backup describe-backup-vault \
  --backup-vault-name "compliant-vault" \
  --query '{VaultName:BackupVaultName,Lock:LockedDate,Type:VaultType}'

# Check if Vault Lock is in compliance mode
aws backup describe-backup-vault \
  --backup-vault-name "compliant-vault" \
  --query 'VaultType'
# "COMPLIANCE" = immutable (cannot be changed)
# "GOVERNANCE" = overridable by privileged users
```

**Critical:** compliance mode Vault Lock is PERMANENT. It cannot be
reversed. Verify the retention period is correct before locking.

## Step 9 — Cross-region replication audit

Verify that backup vaults have cross-region copy rules for DR.

```bash
# Check if backup plans have cross-region copy rules
aws backup get-backup-plan \
  --backup-plan-id <plan-id> \
  --query 'BackupPlan.Rules[*].CopyActions'
# Empty CopyActions = no cross-region replication
# Non-empty CopyActions = cross-region copy configured
```

## Step 10 — Automated SNS alerting and multi-account

### SNS alerting for non-compliance

```bash
# Create EventBridge rule for backup job failures
aws events put-rule \
  --name "backup-job-failed" \
  --event-pattern '{"source":["aws.backup"],"detail-type":["Backup Job State Change"],"detail":{"state":["FAILED","ABORTED"]}}'

# Add SNS target
aws events put-targets \
  --rule "backup-job-failed" \
  --targets '{"Id":"1","Arn":"arn:aws:sns:us-east-1:123456789012:backup-alerts"}'
```

### Multi-account via Organizations

```bash
# Enable AWS Backup in management account
aws backup create-backup-vault \
  --backup-vault-name "org-compliance-vault"

# Create organization-wide report plan
aws backup create-report-plan \
  --report-plan-name "org-compliance-report" \
  --report-setting '{"ReportTemplate":"COMPLIANCE_REPORT","Frameworks":["CIS_AWS_1.4"],"Accounts":["ALL_ACCOUNTS_IN_ORG"],"Regions":["ALL_REGIONS"]}' \
  --report-delivery-channel '{"S3BucketName":"org-backup-reports","S3KeyPrefix":"org-compliance/"}'
```

## NEVER do these things

1. **NEVER assume backup plans cover all resources.** Run a
   COMPLIANCE_REPORT to identify uncovered resources. Coverage gaps
   are the #1 audit finding.

2. **NEVER confuse Vault Lock governance mode with compliance mode.**
   Compliance mode is immutable (regulatory). Governance mode is
   overridable (operational). Only compliance mode satisfies WORM
   requirements for SEC/FINRA/HIPAA.

3. **NEVER deliver reports to an S3 bucket without a bucket policy.**
   The backup service needs write permission. Without the policy,
   reports are silently not delivered.

4. **NEVER assume recovery points are encrypted.** Verify KMS key
   presence on each recovery point. Unencrypted recovery points are a
   compliance finding.

5. **NEVER enable Vault Lock compliance mode without verifying the
   retention period.** Once compliance mode is set, it CANNOT be
   changed. An incorrect retention period is permanent.

6. **NEVER skip cross-region replication audit.** Backups in a single
   region are vulnerable to regional outages. Verify CopyActions in
   backup plan rules.

7. **NEVER create report plans without testing report delivery.**
   After creating a report plan, trigger a report job and verify the
   report appears in S3. Misconfigured delivery channels fail silently.

8. **NEVER map compliance frameworks without verifying control IDs.**
   CIS, NIST, and SOC2 have versioned controls. Verify the correct
   framework version (e.g., CIS AWS 1.4, not 1.3).

9. **NEVER forget SNS subscription confirmation.** SNS topics require
   email/HTTPS subscription confirmation. Unconfirmed subscriptions do
   not receive alerts.

10. **NEVER assume multi-account backup is automatic.** Multi-account
    requires AWS Organizations integration and backup policies
    deployed to member accounts. Verify coverage across all accounts.

## Output format

```text
BACKUP_AUDIT: <report-plan-name> (<region>)
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] Report plan: <plan-name> (schedule: daily|weekly)
  [✓|✗] Report templates: BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT
  [✓|✗] S3 destination: s3://<bucket>/<prefix> (policy: configured)
  [✓|✗] Compliance framework: CIS_AWS_1.4 | NIST_800_53 | SOC2 | <custom>
  [✓|✗] Coverage audit: <N> resources covered, <M> resources without backup (gap)
  [✓|✗] Encryption audit: <N> recovery points encrypted, <M> unencrypted (finding)
  [✓|✗] Retention compliance: minimum <days> days — PASS | FAIL (<details>)
  [✓|✗] Vault Lock: <vault-name> — COMPLIANCE (immutable) | GOVERNANCE (overridable) | Not locked
  [✓|✗] Cross-region replication: <configured | not configured>
  [✓|✗] SNS alerting: <topic-arn> (backup job failures, non-compliance)
  [✓|✗] Multi-account: <ALL_ACCOUNTS_IN_ORG | single account>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws backup list-report-plans
  aws backup describe-backup-vault --backup-vault-name <vault>
  aws s3 ls s3://<bucket>/<prefix>/
```

### Worked example — daily compliance audit with SNS alerting

```text
BACKUP_AUDIT: daily-compliance-report (us-east-1)
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [✓] Report plan: daily-compliance-report (schedule: daily)
  [✓] Report templates: BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT
  [✓] S3 destination: s3://backup-reports-bucket/reports/ (policy: configured)
  [✓] Compliance framework: CIS_AWS_1.4, NIST_800_53
  [✓] Coverage audit: 48 resources covered, 3 resources without backup (gap identified)
  [✓] Encryption audit: 52 recovery points encrypted, 0 unencrypted
  [✓] Retention compliance: minimum 35 days — PASS
  [✓] Vault Lock: compliant-vault — COMPLIANCE (immutable)
  [✓] Cross-region replication: configured (us-east-1 → us-west-2)
  [✓] SNS alerting: arn:aws:sns:us-east-1:123456789012:backup-alerts (failures + non-compliance)
  [✓] Multi-account: ALL_ACCOUNTS_IN_ORG (5 accounts)
  [✓] Tags: Environment=production, Compliance=CIS
VERIFICATION_COMMANDS:
  aws backup list-report-plans
  aws backup describe-backup-vault --backup-vault-name compliant-vault
  aws s3 ls s3://backup-reports-bucket/reports/compliance/
```

## Error handling
Full error-handling deep dives moved to [references/error-handling.md](references/error-handling.md).
Load it when reports are not delivered, alerts are missing, or findings appear.

## References (load on demand)

- [Report templates and frameworks](references/report-templates-and-frameworks.md) — report-plan types deep dive: which template answers which compliance question
- [Vault lock and encryption](references/vault-lock-and-encryption.md) — Vault Lock compliance vs governance modes; encryption-audit heuristic (KMS key presence)
- [Error handling](references/error-handling.md) — undelivered reports, permanent Vault Lock, coverage gaps, unencrypted recovery points, unconfirmed SNS subscriptions
- [Advanced patterns](references/advanced-patterns.md) — audit misconceptions and cross-dependency gotchas

## Domain

AWS CloudOps / AWS Backup Audit Automation & Compliance Reporting.

## AWS documentation

- **AWS Backup audit** — https://docs.aws.amazon.com/aws-backup/latest/devguide/monitor-audit.html
- **Backup report plans** — https://docs.aws.amazon.com/aws-backup/latest/devguide/create-report-plan.html
- **Backup report templates** — https://docs.aws.amazon.com/aws-backup/latest/devguide/backup-reports.html
- **Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html
- **Backup compliance** — https://docs.aws.amazon.com/aws-backup/latest/devguide/compliance.html
- **Backup CLI** — https://docs.aws.amazon.com/cli/latest/reference/backup/

