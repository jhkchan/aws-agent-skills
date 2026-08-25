# Advanced Patterns — Backup Vault Compliance

Load-on-demand deep dives for the Backup Vault Compliance Automator skill: non-obvious
AWS Backup behaviors, cross-account vault policy, report automation, multi-account
rollout, Config/cost reference, and recent features.

## Step 0: Expert knowledge — non-obvious AWS Backup behaviors

These behaviors change the compliance design if ignored:

- **Vault Lock cool-off period is mandatory.** When creating a
  compliance-mode lock, AWS enforces a minimum 3-day cool-off
  (`ChangeableForDays`). During cool-off the lock is removable; after
  expiry it is permanent and irreversible. Compliance mode is NOT
  immediately immutable.

- **A backup vault policy is NOT a vault lock.** The policy controls
  IAM access (who can write/read/delete). The lock controls
  immutability (whether deletion is possible at all). Both are needed
  for full compliance.

- **Backup Framework (2024) provides native compliance reporting.**
  Declarative controls (encryption, frequency, retention) with
  automated evaluation. Reduces need for custom Config rules for
  common checks.

- **Cross-account backup requires destination vault policy to allow
  the source account.** A missing `aws:PrincipalAccount` condition
  is the most common cause of cross-account backup failures.

- **`StartBackupJob` does NOT validate the target vault's encryption
  policy at submission.** The job may be accepted but fail at
  completion. Always poll `describe-backup-job` for final status.

- **Recovery point deletion respects Vault Lock retention.** Calling
  `delete-recovery-point` on a locked recovery point fails with
  `InvalidParameterValueException`. The lock overrides IAM.

- **Tag-based backup selections are dynamic; explicit-ID selections
  are static.** A selection targeting `BackupPlan=prod` auto-includes
  new tagged resources. Explicit resource IDs do NOT auto-include
  new resources.

- **AWS Backup audit evaluates compliance daily, not real-time.** For
  immediate alerting, use EventBridge on `Backup Job State Change`.

## Cross-account backup vault policy statement

For cross-account backup vaults, add a statement allowing the source
account:

```json
{
  "Sid": "AllowCrossAccountBackup",
  "Effect": "Allow",
  "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
  "Action": ["backup:CopyIntoBackupVault", "backup:DescribeRecoveryPoint"],
  "Resource": "*"
}
```

## Step 9: Automate backup compliance reports

```bash
aws backup create-report-plan \
  --report-plan-name daily-compliance-summary \
  --report-setting '{"ReportTemplates":["BACKUP_JOB_REPORT","BACKUP_POLICY_REPORT"]}' \
  --report-delivery-config '{"S3BucketName":"com-company-backup-reports","Formats":["CSV","JSON"]}' \
  --region us-east-1
```

Reports are generated daily and delivered to S3. Set up Athena tables
on the S3 output for queryable compliance dashboards.

## Step 10: Multi-account backup compliance via Organizations

1. **Delegated administrator:**
   `aws backup register-delegated-administrator --account-id 111111111111`
2. **Org-level backup policy:** Use AWS Organizations backup policies
   (tag-based) to enforce plans across member accounts.
   `aws organizations create-policy --type BACKUP_POLICY --content file://policy.json`
3. **Config aggregation:** Management account aggregates compliance:
   `aws configservice put-configuration-aggregator --organization-aggregator-source '{"RoleArn":"...","AllAwsRegions":true}'`


## Appendix B — Config rules and cost reference

Managed rules: `backup-plan-frequency`, `backup-recovery-point-encrypted`,
`backup-recovery-point-manual-deletion-disabled`, `backup-vaults-are-encrypted`.
Custom rules: coverage audit, min-retention, cross-region copy. See
**references/backup-config-rules.md** for implementations.

Cost summary: warm storage $0.05/GB-mo, cold $0.0125/GB-mo, cross-region
$0.02/GB, backup job $0.025/GB, restore $0.025/GB. See
**references/vault-lock-modes.md** for the full cost model.

## Recent AWS features (2024-2026)

- **AWS Backup Framework (2024):** Declarative compliance controls
  with automated evaluation. Reduces need for custom Config rules for
  common checks (encryption, frequency, retention). Framework reports
  integrate with AWS Audit Manager.

- **Cross-account backup (2024-2025):** Native support for backing
  up resources from one account to a vault in another account without
  custom IAM roles. Simplifies centralized backup architectures.

- **Backup Vault Lock compliance mode enhancements (2024):** Added
  `MaxRetentionDays` parameter to lock configuration. Previously only
  minimum retention was enforceable — now both bounds are locked.

- **CloudWatch Events for backup state changes (2024-2025):**
  EventBridge events for `Backup Job State Change` and `Copy Job
  State Change`. Enables real-time compliance alerting without waiting
  for daily audit evaluation.

- **AWS Backup for Amazon EBS multi-volume consistent snapshots
  (2025):** Application-consistent backups across multiple EBS volumes
  attached to a single EC2 instance. Improves recovery integrity for
  multi-volume databases.

- **Organizations backup policies (2025-2026):** Tag-based backup
  policy enforcement at the organization level. Member accounts inherit
  backup plans based on resource tags without individual account
  configuration.

- **Backup continuous verification (2025-2026):** Automated restore
  testing — periodically restores recovery points and validates data
  integrity. Catches silent backup corruption that standard job-status
  monitoring misses.


## Expert heuristic: the silent coverage gap

The most dangerous backup compliance failure is a resource that has
NEVER been backed up because no one tagged it for a backup plan.

**The rule (non-negotiable):**

> EVERY production resource MUST be covered by a backup plan. The ONLY
> guarantee against coverage gaps is a Config rule that flags
> resources without backup as NON_COMPLIANT.

**Why:** AWS Backup does not natively alert when a new resource is
created without coverage. An engineer creates a new RDS instance,
forgets to tag it, and it runs without backups for months — typically
discovered during an incident when recovery is needed and impossible.

**Detection:** Custom Config rule on EC2/RDS/DynamoDB evaluating tag
presence; AWS Backup Framework coverage control; EventBridge on
`RunInstances`/`CreateDBInstance` for real-time tag check.

**Surface in output:** include `COVERAGE_GAP: <count>` and
`UNENCRYPTED_RECOVERY_POINTS: <count>`. If either is > 0, do NOT
mark the deployment as complete.
