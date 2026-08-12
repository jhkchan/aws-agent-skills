---
description: Automate AWS Backup audit and compliance reporting with production-grade defaults (backup report plans, three report templates, CIS/NIST/SOC2 framework mapping, encryption verification, Vault Lock compliance check, retention compliance, SNS alerting, multi-account via Organizations). Emits an AUTOMATION_DEPLOYED checklist.
nl_triggers:
  - "backup audit"
  - "backup compliance"
  - "backup report plan"
  - "vault lock check"
  - "backup encryption audit"
  - "backup retention compliance"
  - "backup frequency audit"
  - "recovery point report"
  - "backup compliance report"
routes_to: backup-audit-automator
---

# /aws:automate-backup-audit

Activate the `backup-audit-automator` skill and automate AWS Backup
audit and compliance reporting with production-grade defaults.

## What it does

The skill walks the automation procedure and emits an
AUTOMATION_DEPLOYED checklist:

1. Report plan creation (daily/weekly/monthly schedule)
2. Report templates (BACKUP_JOB_REPORT, COMPLIANCE_REPORT,
   RECOVERY_POINT_REPORT)
3. S3 report destination (bucket policy for delivery)
4. Compliance framework mapping (CIS, NIST, SOC2)
5. Backup frequency audit (resources without backup plans)
6. Encryption verification (KMS key on recovery points)
7. Retention compliance (minimum retention days)
8. Vault Lock compliance check (COMPLIANCE vs GOVERNANCE)
9. Cross-region replication audit (DR readiness)
10. Automated SNS alerting and multi-account (Organizations)

## When to use

- You need to audit backup coverage across resources.
- You need backup report plans delivered to S3.
- You need to verify KMS encryption on recovery points.
- You need to check Vault Lock compliance mode for regulatory WORM.
- You need automated SNS alerts for backup failures.
- You need multi-account backup compliance via Organizations.

## When NOT to use

- **Creating backup plans** — use backup-plan skills.
- **Restoring from backups** — use backup-restore skills.
- **Backup pricing analysis** — use cost-analysis skills.
- **EBS snapshots** — use EBS snapshot skills (different from AWS Backup).

## How to invoke

### Slash command

```
/aws:automate-backup-audit
```

Then provide: report plan name, S3 bucket for delivery, compliance
frameworks (CIS/NIST/SOC2), SNS topic ARN for alerts, multi-account
scope, tags.

### Natural language

Any of these routes to the same skill:

- "set up backup compliance reports"
- "audit my backup encryption"
- "check vault lock compliance mode"
- "find resources without backup plans"
- "create multi-account backup audit"

### CLI routing

```bash
node cli/bin/cli.js route "automate backup audit"
```

## Pipeline integration

This skill operates in **Phase 2 (Automate)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
automate backup compliance auditing. The output checklist feeds into
verification pipelines and downstream governance skills.

## Example

```
You: /aws:automate-backup-audit

     Set up daily backup compliance reports. CIS framework.
     S3 delivery to s3://backup-reports-bucket. SNS alerts
     for failures.

Skill:
  BACKUP_AUDIT: daily-compliance-report
  VERDICT: AUTOMATION_DEPLOYED
  CHECKLIST:
    [✓] Report templates: BACKUP_JOB, COMPLIANCE, RECOVERY_POINT
    [✓] S3 destination: s3://backup-reports-bucket/reports/
    [✓] Framework: CIS_AWS_1.4
    [✓] Coverage: 48 covered, 3 without backup
    [✓] Vault Lock: COMPLIANCE (immutable)
    [✓] SNS alerting: backup-alerts
  VERIFICATION_COMMANDS:
    aws backup list-report-plans
```

## References

- Skill definition: `skills/backup-audit-automator/SKILL.md`
- Report templates guide: `skills/backup-audit-automator/references/report-templates-and-frameworks.md`
- Vault Lock guide: `skills/backup-audit-automator/references/vault-lock-and-encryption.md`
- Eval suite: `skills/backup-audit-automator/evals/evals.json`
