# Advanced Patterns — Backup Compliance Automator

## Mindset deep dives
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

## Backup Report Stream and reporting gotchas
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

## Cross-account member-account copy plan
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
