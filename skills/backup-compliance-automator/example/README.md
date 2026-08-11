# Example usage: backup-compliance-automator

A walkthrough showing the skill designing a Backup compliance automation
playbook for a 30-account org aligned to SOC2. Includes Audit Manager
framework, scheduled reports, legal hold automation, cross-account
centralization, and Backup Search scoping. The skill emits an AUTOMATED
verdict.

## Input (user prompt)

> Design AWS Backup compliance automation for our 30-account org aligned
> to SOC2. Cover Audit Manager framework, daily compliance reports,
> legal hold automation via EventBridge (litigation hold on demand),
> cross-account centralization via a delegated admin, Backup Search for
> eDiscovery, and cost allocation tags per project. Vault Lock in
> LOCK_MODE.

## Skill output

```text
FRAMEWORK:
  - [PASS] Framework: soc2-backup-compliance (4 controls)
  - [PASS] Controls: PLAN_EXISTENCE, RESOURCES_PROTECTED,
    MANUAL_DELETION_DISABLED, LAST_BACKUP_AGE 1d
  - [PASS] Last evaluation: 2026-08-10 02:00 UTC (EventBridge Scheduler)
REPORTING:
  - [PASS] Compliance report: monthly, lands in s3://backup-compliance-reports/soc2/
  - [PASS] Job summary report: weekly
  - [PASS] Coverage report: weekly
  - [PASS] S3 bucket: versioning + Object Lock mode GOVERNANCE, 7-year retention
LEGAL_HOLD:
  - [PASS] BackupLegalHold mechanism documented
  - [PASS] Test hold: 2026-07-15, created + released successfully
  - [PASS] Vault Lock: production-vault, LOCK_MODE, 7-365d (compliance mode)
  - [PASS] EventBridge trigger: custom.legal -> create-legal-hold Lambda
CROSS_ACCOUNT:
  - [PASS] Delegated admin: 222222222222 (audit account, us-east-1)
  - [PASS] Org vault: org-compliance-vault with member access policy
  - [PASS] All 30 member plans have COPY_ACTION to org vault
SEARCH:
  - [PASS] Backup Search scoped to production + org-compliance vaults
  - [PASS] eDiscovery: search -> create-legal-hold workflow documented
VERIFICATION:
  - [PASS] Restore drill: 2026-07-20, RTO 35min for EBS 1TB
  - [PASS] Cost allocation tags active in Cost Explorer (Project, Env, Compliance)
  - [PASS] Latest report: 2026-08-10, within 24h SLA
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] Cross-account copy adds ~12% to per-job cost across 30 accounts
  - [INFO] Backup Search scoped — broad searches blocked by policy
  - [WARN] One member account (333333333333) missing Project cost tag
REMEDIATION:
  1. Add Project tag to backup jobs in account 333333333333
  2. Document the case-ID convention for legal holds in the runbook
```

## What the skill caught that a generic assistant misses

1. **Vault Lock mode matters.** A generic assistant may say "enable Vault
   Lock." The skill requires LOCK_MODE (compliance mode) for SOC2 —
   GOVERNANCE mode allows root override, which fails the audit.

2. **Encryption control is required.** A generic assistant may omit
   BACKUP_RECOVERY_POINT_ENCRYPTED. The skill requires it — unencrypted
   recovery points are a SOC2 finding.

3. **Legal hold test is mandatory.** A generic assistant may say "set up
   legal hold." The skill requires a create + release test cycle — the
   team's first hold cannot be under court deadline pressure.

4. **Cross-account centralization via delegated admin.** A generic
   assistant may suggest per-account StackSets. The skill recommends the
   Organizations delegated admin + org vault pattern — single central
   view for the auditor.

5. **Cost allocation tags need activation.** A generic assistant may say
   "tag the vaults." The skill requires activation in Billing before tags
   appear in Cost Explorer.

6. **Backup Search scope.** A generic assistant may say "use Backup
   Search." The skill requires tight scoping (vault, resource type, date
   range) — broad searches are expensive per GB scanned.

7. **Report freshness alarm.** A generic assistant may schedule reports
   and assume they run. The skill requires alarming on report job failure
   — a silent failure means stale evidence for the auditor.

8. **Restore drill control.** A generic assistant may focus on backup
   success. The skill includes BACKUP_REPORT_LAST_RESTORE_AGE — a backup
   plan with no tested restores is not compliance-grade.

## Slash-command invocation

```
/aws:automate-backup-compliance
```

Or via the orchestrator:

```
/aws:pipeline
You: "build a SOC2 backup audit framework for our 30-account org with legal hold and cross-account audit"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the compliance playbook, validate the posture:

```bash
# Verify Audit Manager framework exists and last evaluated
aws backup audit-manager list-frameworks \
  --query 'frameworks[*].[frameworkName,frameworkArn]' --profile default

# Verify the report plan exists
aws backup audit-manager list-report-plans --profile default

# Verify Vault Lock is in LOCK_MODE
aws backup describe-backup-vault \
  --backup-vault-name production-vault \
  --query 'lockDate' --profile default  # null if not locked

# Verify legal holds (should be empty unless active)
aws backup list-legal-holds --profile default

# Verify cross-account backup delegated admin
aws organizations list-delegated-administrators \
  --service-principal backup.amazonaws.com \
  --profile management-profile

# Verify cost allocation tags are active in Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2026-08-01,End=2026-08-10 \
  --granularity DAILY --metrics "BlendedCost" \
  --group-by Type=DIMENSION,Key=Project \
  --profile default

# Verify Backup Search is available in region
aws backup search list-search-jobs --profile default
```
