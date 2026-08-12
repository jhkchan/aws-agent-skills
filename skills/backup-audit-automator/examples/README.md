# End-to-End Example: Backup Audit Automation

A walkthrough showing how to use the `backup-audit-automator` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are setting up a daily backup compliance audit with all three
report templates, CIS/NIST framework mapping, SNS alerting for backup
failures, and encryption/retention compliance checks. The setup needs:

- Account: 123456789012, Region: us-east-1
- Report templates: BACKUP_JOB_REPORT, COMPLIANCE_REPORT,
  RECOVERY_POINT_REPORT
- S3 destination: s3://backup-reports-bucket/reports/
- Frameworks: CIS_AWS_1.4, NIST_800_53
- SNS alerts: arn:aws:sns:us-east-1:123456789012:backup-alerts
- Tags: Environment=production, Compliance=CIS

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:automate-backup-audit
```

Then paste the requirements.

### Option B: Natural language

```
You: "Set up daily backup compliance reports. I need all three
      report types. CIS and NIST frameworks. SNS alerts for
      failures. Deliver to s3://backup-reports-bucket."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "automate backup audit"
```

---

## Step 2 — Skill produces the AUTOMATION_DEPLOYED checklist

```text
BACKUP_AUDIT: daily-compliance-report (us-east-1)
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [✓] Report plan: daily-compliance-report (schedule: daily)
  [✓] Report templates: BACKUP_JOB_REPORT, COMPLIANCE_REPORT, RECOVERY_POINT_REPORT
  [✓] S3 destination: s3://backup-reports-bucket/reports/ (policy: configured)
  [✓] Compliance framework: CIS_AWS_1.4, NIST_800_53
  [✓] Coverage audit: 48 resources covered, 3 resources without backup
  [✓] Encryption audit: 52 recovery points encrypted, 0 unencrypted
  [✓] Retention compliance: minimum 35 days — PASS
  [✓] Vault Lock: compliant-vault — COMPLIANCE (immutable)
  [✓] Cross-region replication: configured (us-east-1 to us-west-2)
  [✓] SNS alerting: arn:aws:sns:us-east-1:123456789012:backup-alerts
  [✓] Tags: Environment=production, Compliance=CIS
VERIFICATION_COMMANDS:
  aws backup list-report-plans
  aws backup describe-backup-vault --backup-vault-name compliant-vault
  aws s3 ls s3://backup-reports-bucket/reports/compliance/
```

---

## Step 3 — Automation commands

```bash
# Step 1: Create report plans for all three templates
for TEMPLATE in BACKUP_JOB_REPORT COMPLIANCE_REPORT RECOVERY_POINT_REPORT; do
  aws backup create-report-plan \
    --report-plan-name "daily-${TEMPLATE,,}" \
    --report-setting "{\"ReportTemplate\":\"$TEMPLATE\",\"Frameworks\":[\"CIS_AWS_1.4\",\"NIST_800_53\"]}" \
    --report-delivery-channel "{\"S3BucketName\":\"backup-reports-bucket\",\"S3KeyPrefix\":\"reports/${TEMPLATE,,}/\"}"
done

# Step 2: Verify S3 bucket policy allows backup service
aws s3api put-bucket-policy \
  --bucket backup-reports-bucket \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"backup.amazonaws.com"},"Action":["s3:PutObject"],"Resource":"arn:aws:s3:::backup-reports-bucket/reports/*"}]}'

# Step 3: Create EventBridge rule for backup failures
aws events put-rule \
  --name "backup-job-failed" \
  --event-pattern '{"source":["aws.backup"],"detail-type":["Backup Job State Change"],"detail":{"state":["FAILED","ABORTED"]}}'

# Step 4: Add SNS target for failure alerts
aws events put-targets \
  --rule "backup-job-failed" \
  --targets '{"Id":"1","Arn":"arn:aws:sns:us-east-1:123456789012:backup-alerts"}'

# Step 5: Trigger first report job
aws backup start-report-job --report-plan-name "daily-compliance_report"
```

---

## Step 4 — Post-automation verification

```bash
# Verify report plans
aws backup list-report-plans --output table

# Verify report delivery
aws s3 ls s3://backup-reports-bucket/reports/ --recursive

# Verify Vault Lock status
aws backup describe-backup-vault --backup-vault-name compliant-vault

# Check encryption coverage
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name compliant-vault \
  --query 'RecoveryPoints[?EncryptionKeyArn==`null`]' \
  --output table
```

---

## What the skill catches that a naive automation misses

| Configuration | Naive automation | Skill output | Why the skill is right |
|---|---|---|---|
| Report templates | Single generic report | All three templates (job, compliance, recovery point) | Each template answers a different compliance question |
| S3 bucket policy | Not configured | backup.amazonaws.com write permission | Without policy, reports are silently not delivered |
| Vault Lock mode | "Locked" without mode | COMPLIANCE vs GOVERNANCE distinction | Only compliance mode is immutable for regulatory requirements |
| Encryption audit | Assumes encrypted | KMS key presence check on each recovery point | Recovery points may lack KMS encryption if plan omits key |
| Coverage gap | Not identified | COMPLIANCE_REPORT lists uncovered resources | Resources without backup plans are the #1 audit finding |

---

## Related artifacts

- **Skill definition:** `skills/backup-audit-automator/SKILL.md`
- **Report templates guide:** `skills/backup-audit-automator/references/report-templates-and-frameworks.md`
- **Vault Lock guide:** `skills/backup-audit-automator/references/vault-lock-and-encryption.md`
- **Slash command:** `commands/aws/automate-backup-audit.md`
- **Eval suite:** `skills/backup-audit-automator/evals/evals.json`
- **Legacy test cases:** `skills/backup-audit-automator/eval/test-cases.yaml`
