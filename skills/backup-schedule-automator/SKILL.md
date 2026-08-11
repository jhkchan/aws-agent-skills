---
name: backup-schedule-automator
description: >-
  Designs and implements automated AWS Backup scheduling workflows using backup
  plans, tag-based resource assignment, cross-account backup via Organizations
  backup policies, on-demand backup triggering via EventBridge and Lambda, backup
  vault notifications (SNS), restore testing automation, lifecycle policy
  automation (warm storage tiering to cold storage), curated backup reports,
  audit trail via CloudTrail, compliance reporting, and multi-region backup
  orchestration. Wires backup vault lock for WORM compliance, backup plan
  templates for common patterns (daily-7d, weekly-30d, monthly-1yr), and
  EventBridge-driven on-demand backups triggered by application deployment
  events. Emits AUTOMATION_DEPLOYED with a deployment-ready backup plan and
  policy template or REVIEW_REQUIRED with the specific gap. Use when building
  AWS Backup automation, designing tag-based backup schedules, configuring
  cross-account or cross-region backup, implementing lifecycle tiering, or
  setting up restore testing for RTO/RPO validation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workflow design. Live deployment
  uses aws backup create-backup-plan, start-backup-job, create-backup-vault,
  put-backup-vault-access-policy, create-framework, start-restore-job,
  describe-backup-job, describe-restore-job, aws events put-rule, put-targets,
  aws lambda create-function, aws organizations put-backup-policy, and
  aws cloudformation deploy — AWS CLI v2, SSO or key-based credentials.
keywords:
  - AWS Backup
  - backup plan
  - backup vault
  - tag-based assignment
  - cross-account backup
  - backup policy
  - Organizations backup
  - vault lock
  - WORM compliance
  - lifecycle policy
  - cold storage tiering
  - restore testing
  - RTO RPO validation
  - backup report
  - EventBridge on-demand backup
  - backup vault notification
  - SNS backup alert
  - multi-region backup
  - CloudTrail audit
  - backup framework
tags: [aws-backup, backup-plan, backup-vault, lifecycle-policy, cross-account, restore-testing, automate]
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
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Designing automated AWS Backup schedules, building tag-based resource
    assignment at scale, configuring cross-account backup via Organizations
    policies, implementing lifecycle tiering (warm to cold storage), setting
    up restore testing automation for RTO/RPO validation, wiring EventBridge
    on-demand backup triggers, enabling backup vault lock for WORM compliance,
    deploying curated backup reports, or orchestrating multi-region backup.
  activation_triggers:
    - "automate AWS Backup schedule"
    - "backup plan from template"
    - "tag-based backup assignment"
    - "cross-account backup Organizations"
    - "backup vault lock WORM"
    - "lifecycle cold storage tiering"
    - "restore testing automation"
    - "RTO RPO validation"
    - "on-demand backup EventBridge"
    - "backup report automation"
    - "backup policy inheritance"
    - "multi-region backup orchestration"
  invocation_schema: >-
    Input: either (a) a resource scope (tag-based selection, resource type
    list) plus backup requirements (frequency, retention, lifecycle), OR (b)
    a compliance requirement ("daily backups with 1-year retention and WORM
    lock", "cross-account backup to DR account"). Output: deterministic
    BACKUP block — PLAN/VAULT/LIFECYCLE/TRIGGER/RESTORE_TEST/VERDICT — where
    VERDICT is AUTOMATION_DEPLOYED (deployment-ready template) or
    REVIEW_REQUIRED (specific gap cited).
---

# Backup Schedule Automator

## Mindset

**One-line takeaway:** every AWS Backup automation is a six-stage pipeline —
**select** (tag-based resource assignment) → **schedule** (backup plan with
frequency and retention) → **store** (backup vault with access policy and
optional lock) → **tier** (lifecycle policy moving cold backups to cold
storage) → **test** (restore testing for RTO/RPO validation) → **audit**
(CloudTrail + backup reports + framework compliance). A gap in ANY stage
produces either data loss (backup never runs), cost waste (backups never
expire), or false confidence (backups exist but restores fail).

- **Selection** without **tag governance** is unscalable: manually adding
  resource ARNs to a backup plan works for 10 resources but fails at 1,000.
  Tag-based assignment (`Condition: StringEquals` on `aws:ResourceTag`) is
  the only pattern that scales.
- **Scheduling** without **lifecycle tiering** is expensive: hot storage
  for a 365-day retention plan costs 5-10x what a tiered plan (30 days hot
  then cold) costs. Always design lifecycle transitions.
- **Backups** without **restore testing** are wishful thinking. An untested
  backup is a Schrodinger backup — you do not know if it works until you
  try, and the worst time to find out is during an incident.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick a backup plan template for a common pattern | Step 2 + Appendix A |
| Scale resource assignment with tags | Step 3 (tag-based matrix) |
| Configure cross-account backup via Organizations | Step 4 |
| Wire on-demand backup via EventBridge + Lambda | Step 5 |
| Set up backup vault lock (WORM) for compliance | Step 6 |
| Design lifecycle policy for cold storage tiering | Step 7 |
| Automate restore testing for RTO/RPO validation | Step 8 |
| Configure backup vault notifications (SNS) | Step 9 |
| Deploy curated backup reports | Step 10 |
| Audit backup compliance with frameworks | Step 11 |
| Orchestrate multi-region backup | Step 12 |
| Avoid common backup pitfalls | Anti-Patterns |
| Recent features (vault lock, restore testing, frameworks) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Tag-based resource assignment is the ONLY scalable pattern.**
   Hardcoding resource ARNs in a backup plan works for small fleets but
   breaks when resources are created or destroyed. Tag-based selection
   (`aws:ResourceTag/backup-plan = daily-prod`) automatically includes
   new resources. A resource created without the tag is NOT backed up —
   always alert on untagged critical resources.

2. **Backup vault lock is IRREVERSIBLE.** Once vault lock is in
   `LOCKED` state, you cannot remove it or shorten the retention period.
   You can only extend it. A vault locked with a 365-day retention means
   every backup in that vault is retained for 365 days, no exceptions,
   even if the backup was created in error. Always test in
   `GOVERNANCE` mode first (admin can override) before switching to
   `COMPLIANCE` mode (no override).

3. **Cross-account backup requires a backup vault in the DESTINATION
   account and a backup role that the SOURCE account assumes.** The
   source account performs the backup but writes to the destination
   vault. The destination vault's access policy MUST grant the source
   account's backup role `backup:CopyIntoBackupVault`. Without this,
   cross-account copy silently fails.

4. **Lifecycle transitions are one-way.** Moving a recovery point from
   hot to cold storage is irreversible. A recovery point in cold storage
   takes hours to restore (thaw) vs minutes from hot. Always design the
   transition window based on restore frequency needs, not just cost.

5. **Restore testing is NOT the same as restore verification.** Checking
   that a recovery point EXISTS is verification. Actually restoring it
   and verifying the application starts is testing. Without testing,
   you have no RTO/RPO data for your DR plan.

## STRICT output contract

Every backup automation design MUST produce exactly one BACKUP block,
following this format:

```text
BACKUP: <reference>
PLAN: <backup plan name + rule structure>
VAULT: <vault name + lock mode + access policy summary>
LIFECYCLE: <hot-to-cold transition schedule>
TRIGGER: SCHEDULED | ON_DEMAND | SCHEDULED_AND_ON_DEMAND
RESTORE_TEST: <frequency + RTO target + last test date>
TAG_SCOPE: <tag key=value used for resource assignment>
CROSS_ACCOUNT: <NONE | destination account + vault>
CROSS_REGION: <NONE | destination region>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the backup plan + vault + policy>
```

## NEVER section

- **NEVER** deploy a backup plan without verifying that the target
  resources carry the required tags. A plan scoped to
  `aws:ResourceTag/backup = daily` that matches zero resources produces
  no backups and no alerts. The backup service does not warn on empty
  selection — it simply does nothing.

- **NEVER** enable vault lock in COMPLIANCE mode without first testing
  in GOVERNANCE mode. COMPLIANCE mode is irreversible — you cannot
  delete the vault or shorten retention until the lock expires. A typo
  in the retention period (e.g., 3650 days instead of 365) is a
  decade-long commitment.

- **NEVER** configure a lifecycle transition to cold storage without
  documenting the restore thaw time. Cold storage restores take hours,
  not minutes. If the application RTO is 1 hour, cold storage at day 31
  breaks the SLA. Always map the transition to the RTO curve.

- **NEVER** assume cross-account backup works without the destination
  vault access policy. The source account needs `backup:CopyIntoBackupVault`
  permission on the destination vault. Without it, the copy job fails
  silently (the backup appears successful in the source but never lands
  in the destination).

- **NEVER** skip restore testing. An untested backup is a liability,
  not an asset. A backup that cannot be restored is worse than no
  backup because it creates false confidence. Schedule restore tests at
  a frequency tied to the RTO (weekly for Tier 1 apps, monthly for
  Tier 2, quarterly for Tier 3).

- **NEVER** use the default backup vault for production workloads. The
  default vault has no access policy, no lock, and no notifications.
  Always create named vaults per environment and apply least-privilege
  access policies.

- **NEVER** configure on-demand backup via EventBridge without a DLQ.
  EventBridge delivers events asynchronously. A Lambda failure drops
  the trigger silently. Configure an SQS DLQ so missed on-demand
  backups are visible.

- **NEVER** rely solely on AWS Backup reports for compliance evidence.
  Reports show backup job status but not restore-test results. Always
  pair backup reports with restore-test logs for audit completeness.

## Expert heuristic

**Tag-based resource assignment scaling + vault lock for compliance (WORM) +
restore testing frequency vs RTO/RPO validation.**

The highest-leverage Backup automation pattern combines three design
decisions:

1. **Tag-based assignment at scale:** Resources are tagged
   `backup-plan=<plan-name>` and `backup-env=<env>`. The backup plan's
   `Selection` uses `Conditions: StringEquals` on these tags. When a new
   resource is created with the tag, it is automatically included in the
   next backup window. A CloudWatch alarm on `NumberOfResourcesAssigned`
   dropping to zero catches tag drift.

2. **Vault lock for WORM compliance:** For regulated workloads (financial,
   healthcare, legal), the backup vault is locked in COMPLIANCE mode with
   a retention period matching the regulatory requirement (e.g., 7 years
   for SOX, 6 years for HIPAA). This prevents even the root account from
   deleting backups before the retention period expires.

3. **Restore testing frequency mapped to RTO:**

| Application tier | RTO target | Restore test frequency | Acceptable |
|---|---|---|---|
| Tier 1 (production critical) | < 1 hour | Weekly | Restore + app health check |
| Tier 2 (production standard) | < 4 hours | Monthly | Restore + data integrity check |
| Tier 3 (internal/dev) | < 24 hours | Quarterly | Restore only |

**Tag-based scaling pattern:**

```yaml
# Backup selection using tag-based conditions
BackupSelection:
  SelectionName: "daily-prod-selection"
  IamRoleArn: "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole"
  ListOfTags:
    - ConditionType: "STRINGEQUALS"
      ConditionKey: "backup-plan"
      ConditionValue: "daily-prod"
  Conditions:
    StringEquals:
      - ConditionKey: "aws:ResourceTag/environment"
        ConditionValue: "prod"
  NotResources:
    - "arn:aws:dynamodb:us-east-1:111111111111:table/temp-*"
```

**Vault lock compliance pattern:**

```bash
# Step 1: Create vault
aws backup create-backup-vault \
  --backup-vault-name "prod-compliance-vault" \
  --encryption-key-arn "arn:aws:kms:us-east-1:111111111111:key/abc123"

# Step 2: Lock in GOVERNANCE mode first (test)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 2555 \
  --mode GOVERNANCE

# Step 3: After validation, switch to COMPLIANCE (irreversible)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --min-retention-days 365 \
  --max-retention-days 2555 \
  --mode COMPLIANCE
```

## Configuration dependency graph

```
Backup vault created (create-backup-vault)
  +-- Access policy (put-backup-vault-access-policy)
  |    +-- Source account granted backup:CopyIntoBackupVault (for cross-account)
  +-- Vault lock (put-backup-vault-lock-configuration)
  |    +-- GOVERNANCE mode (test) -> COMPLIANCE mode (production WORM)
  +-- Notifications (backup-vault-notifications -> SNS topic)
  +-- Backup plan created (create-backup-plan)
  |    +-- Rule: schedule + lifecycle (hot -> cold transition)
  |    +-- Rule: copy to destination region/account
  |    +-- Selection: tag-based resource assignment
  |         +-- IAM role: AWSBackupDefaultServiceRole
  |         +-- Tag conditions: backup-plan=X, environment=prod
  +-- Organizations backup policy (for multi-account)
  |    +-- Policy applied at root/OU level
  |    +-- Member accounts inherit plan + vault assignment
  +-- EventBridge on-demand trigger (optional)
  |    +-- Lambda: start-backup-job on deployment event
  |    +-- SQS DLQ for failed triggers
  +-- Restore testing (start-restore-job on schedule)
  |    +-- Lambda: restore + verify + report
  +-- Backup framework (create-framework)
  |    +-- Compliance controls + reporting
  +-- Backup report plan (create-report-plan)
       +-- Curated report delivered to S3
```

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Existing backup plans | `list-backup-plans` | Avoid duplicate plans |
| Existing backup vaults | `list-backup-vaults` | Reuse or identify gaps |
| Tag inventory | `tag:get-resources` with backup tags | Verify tag coverage |
| Backup jobs history | `list-backup-jobs` | Success rate baseline |
| Restore jobs history | `list-restore-jobs` | Restore test history |
| Vault lock status | `describe-backup-vault` | Existing lock configuration |
| Organizations policy | `organizations describe-policy` | Existing backup policy |
| Framework status | `describe-framework` | Compliance control status |

**If the input is malformed**, emit:

```text
BACKUP: <reference>
PLAN: UNKNOWN
VERDICT: ERROR
REASON: Cannot design backup plan — resource scope and retention requirements are required.
GAP: Re-supply resource tag inventory and backup frequency/retention targets.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Backup behaviors

- **Backup plan rules are evaluated independently.** If a plan has two
  rules (daily-7d and weekly-30d), a resource matching both rules gets
  TWO backups on the weekly schedule day. Use `CopyActions` within a
  single rule to avoid duplicate backups.

- **Tag-based selection is evaluated at backup time, not at plan creation.**
  Resources tagged after the plan is created are automatically included
  in the next backup window. Resources with the tag removed are
  excluded. No plan update is needed.

- **The default backup vault (`Default`) has NO access policy.** Any
  principal with `backup:StartBackupJob` can write to it. Always create
  named vaults with explicit access policies for production workloads.

- **Cross-account backup uses the DESTINATION vault's KMS key.** The
  source account cannot use its own KMS key for a backup written to a
  destination account's vault. The destination KMS key policy must grant
  the source account `kms:Decrypt` and `kms:GenerateDataKey`.

- **Lifecycle `DeleteAfterDays` is measured from the backup creation
  date.** A recovery point created on Jan 1 with `DeleteAfterDays=30`
  is eligible for deletion on Jan 31. `MoveToColdStorageAfterDays` works
  the same way.

- **`start-restore-job` is asynchronous.** The API returns a `RestoreJobId`
  immediately. The actual restore takes minutes to hours depending on
  data size and storage tier. Poll `describe-restore-job` for completion.

- **Organizations backup policies override account-level plans.** If a
  policy at the OU level specifies a backup plan, member accounts cannot
  create conflicting plans. The policy merges with any account-level
  plans, and the more restrictive retention wins.

- **Backup reports are delivered to S3 with a delay.** A daily report
  plan delivers the previous day's data. Real-time job status requires
  CloudWatch Events (`Backup Job State Change`).

- **Vault lock `ChangeableForDays` only applies to GOVERNANCE mode.**
  During this window, an admin can modify or remove the lock. After the
  window expires, the lock becomes immutable (functionally identical to
  COMPLIANCE mode).

### Step 1: Verify existing backup posture

```bash
aws backup list-backup-plans --output json
aws backup list-backup-vaults --output json
aws backup list-backup-jobs --by-state COMPLETED --max-results 5
```

### Step 2: Select or build a backup plan template

| Template | Frequency | Retention | Lifecycle | Use case |
|---|---|---|---|---|
| daily-7d | Daily | 7 days hot | None | Dev/test environments |
| daily-30d-weekly-90d | Daily + Weekly | 7d hot + 30d hot + 90d cold | 30d hot -> cold | Standard production |
| daily-30d-monthly-1yr | Daily + Monthly | 7d hot + 30d cold + 365d cold | 7d hot -> cold | Compliance workloads |
| continuous-35d | Continuous (PITR) | 35 days | None | RDS/DynamoDB continuous |

### Step 3: Configure tag-based resource assignment

```bash
aws backup create-backup-selection \
  --backup-plan-id "daily-prod-plan" \
  --backup-selection '{
    "SelectionName": "prod-tagged-resources",
    "IamRoleArn": "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{"ConditionType":"STRINGEQUALS","ConditionKey":"backup-plan","ConditionValue":"daily-prod"}],
    "Conditions": {"StringEquals": [{"ConditionKey":"aws:ResourceTag/environment","ConditionValue":"prod"}]}
  }'
```

### Step 4: Configure cross-account backup via Organizations

```bash
# Create backup policy at the OU level
aws organizations create-policy \
  --type BACKUP_POLICY \
  --name "org-backup-policy-prod" \
  --content file://backup-policy.json \
  --target-ids "ou-prod-xxxxx"
```

Policy JSON (simplified):

```json
{
  "plans": {
    "daily-backup-plan": {
      "regions": {"us-east-1": {"region": "us-east-1"}},
      "rules": {
        "daily-rule": {
          "schedule_expression": "cron(0 5 ? * * *)",
          "target_backup_vault_name": "Default",
          "lifecycle": {"delete_after_days": 30}
        },
        "cross-region-copy-rule": {
          "target_backup_vault_name": "dr-vault",
          "target_region": "us-west-2",
          "lifecycle": {"delete_after_days": 90}
        }
      },
      "selections": {
        "tags": {
          "backup-daily": {"assignment_tag": {"key": "backup-plan", "value": "daily"}}
        }
      }
    }
  }
}
```

### Step 5: Wire on-demand backup via EventBridge + Lambda

```bash
aws events put-rule \
  --name on-demand-backup-on-deploy \
  --event-pattern '{
    "source": ["aws.codepipeline"],
    "detail-type": ["CodePipeline Pipeline Execution State Change"],
    "detail": {"state": ["SUCCEEDED"]}
  }'

aws events put-targets \
  --rule on-demand-backup-on-deploy \
  --targets '[{
    "Id": "on-demand-backup-lambda",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:on-demand-backup",
    "DeadLetterConfig": {"Arn": "arn:aws:sqs:us-east-1:111111111111:backup-trigger-dlq"}
  }]'
```

Lambda handler:

```python
import boto3
backup = boto3.client('backup')

def lambda_handler(event, context):
    resp = backup.start_backup_job(
        BackupVaultName='on-demand-vault',
        ResourceArn='arn:aws:dynamodb:us-east-1:111111111111:table/prod-table',
        IamRoleArn='arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole',
        IdempotencyToken=f"ondemand-{event['time']}",
        Lifecycle={'DeleteAfterDays': 7}
    )
    return {'backupJobId': resp['BackupJobId']}
```

### Step 6: Configure backup vault lock (WORM)

```bash
# GOVERNANCE mode first (test)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --mode GOVERNANCE

# After validation: COMPLIANCE mode (irreversible)
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --min-retention-days 365 \
  --max-retention-days 2555 \
  --mode COMPLIANCE
```

### Step 7: Design lifecycle policy for cold storage tiering

```bash
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName": "tiered-retention-plan",
  "Rules": [{
    "RuleName": "daily-tiered",
    "TargetBackupVaultName": "prod-vault",
    "ScheduleExpression": "cron(0 5 ? * * *)",
    "StartWindowMinutes": 480,
    "CompletionWindowMinutes": 10080,
    "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365},
    "CopyActions": [{
      "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault",
      "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365}
    }]
  }]
}'
```

### Step 8: Automate restore testing

```python
import boto3, json
backup = boto3.client('backup')
sns = boto3.client('sns')

def lambda_handler(event, context):
    # List recent completed backups
    jobs = backup.list_backup_jobs(
        ByState='COMPLETED', ByBackupVaultName='prod-vault', MaxResults=1
    )
    if not jobs['BackupJobs']:
        return {'status': 'no_backups_to_test'}

    job = jobs['BackupJobs'][0]
    # Start restore to a test VPC/subnet
    resp = backup.start_restore_job(
        RecoveryPointArn=job['RecoveryPointArn'],
        Metadata={
            'VpcId': 'vpc-testrestore',
            'SubnetId': 'subnet-testrestore',
            'InstanceType': 't3.medium'
        },
        IamRoleArn='arn:aws:iam::111111111111:role/BackupRestoreRole'
    )

    # Notify
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:111111111111:backup-alerts',
        Message=f'Restore test started: {resp["RestoreJobId"]} for {job["RecoveryPointArn"]}'
    )
    return {'restoreJobId': resp['RestoreJobId']}
```

### Step 9: Configure backup vault notifications

```bash
aws backup put-backup-vault-notifications \
  --backup-vault-name "prod-vault" \
  --sns-topic-arn "arn:aws:sns:us-east-1:111111111111:backup-alerts" \
  --backup-vault-events ["BACKUP_JOB_COMPLETED","BACKUP_JOB_FAILED","RESTORE_JOB_COMPLETED","RESTORE_JOB_FAILED"]
```

### Step 10: Deploy curated backup reports

```bash
aws backup create-report-plan \
  --report-plan-name "daily-backup-compliance-report" \
  --report-delivery-channel '{"S3BucketName":"backup-reports-111111111111","Formats":["CSV","JSON"]}' \
  --report-setting '{"ReportTemplate":"BACKUP_JOB_REPORT","NumberOfFrameworks":0}'
```

### Step 11: Audit with backup frameworks

```bash
aws backup create-framework \
  --framework-name "backup-compliance-framework" \
  --framework-controls '[{
    "ControlName": "BACKUP_RECOVERY_POINT_MINIMUM_RETENTION_CHECK",
    "ControlInputParameters": [{"ParameterName":"requiredRetentionDays","ParameterValue":"7"}],
    "ControlScope":{"ComplianceResourceTypes":["DynamoDB","EBS"]}
  }]' \
  --framework-description "Minimum retention and frequency compliance"
```

### Step 12: Orchestrate multi-region backup

Use `CopyActions` in the backup plan rule to copy to a DR region:

```bash
# In the plan rule (Step 7), CopyActions already includes cross-region copy
# Verify cross-region copy jobs are succeeding:
aws backup list-copy-jobs --by-state COMPLETED --region us-east-1
```

## Output format

### Worked example — AUTOMATION_DEPLOYED, tiered production backup

```text
BACKUP: prod-backup-automation-baseline
PLAN: tiered-retention-plan (daily, 30d hot + 335d cold, cross-region copy to us-west-2)
VAULT: prod-vault (GOVERNANCE lock, min 7d, max 365d)
LIFECYCLE: MoveToColdStorageAfterDays=30, DeleteAfterDays=365
TRIGGER: SCHEDULED (cron(0 5 ? * * *))
RESTORE_TEST: Monthly, RTO target 4 hours, last test 2026-07-15
TAG_SCOPE: backup-plan=tiered-prod, environment=prod
CROSS_ACCOUNT: NONE
CROSS_REGION: us-west-2 (dr-vault, 90d retention)
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws backup create-backup-plan --backup-plan '{"BackupPlanName":"tiered-retention-plan","Rules":[{"RuleName":"daily-tiered","TargetBackupVaultName":"prod-vault","ScheduleExpression":"cron(0 5 ? * * *)","Lifecycle":{"MoveToColdStorageAfterDays":30,"DeleteAfterDays":365},"CopyActions":[{"DestinationBackupVaultArn":"arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault","Lifecycle":{"DeleteAfterDays":90}}]}]}'
```

### Worked example — REVIEW_REQUIRED, missing vault lock

```text
BACKUP: compliance-backup-gaps
PLAN: daily-7d (exists but no lifecycle tiering)
VAULT: Default (NO access policy, NO vault lock)
LIFECYCLE: NONE — all backups in hot storage indefinitely
TRIGGER: SCHEDULED
RESTORE_TEST: NONE — no restore testing configured
TAG_SCOPE: backup-plan=daily (but 0 resources match)
CROSS_ACCOUNT: NONE
CROSS_REGION: NONE
VERDICT: REVIEW_REQUIRED
GAP: Three critical gaps: (1) Default vault has no access policy or lock — move to named vault with GOVERNANCE lock for compliance; (2) No lifecycle tiering — hot storage cost for 365-day retention is 5x a tiered plan; (3) Zero resources match the tag scope — verify tag inventory or the plan backs up nothing. Additionally, no restore testing exists, so RTO/RPO is unvalidated.
TEMPLATE: (see Steps 2, 3, 6, 7, 8 for remediation)
```

## Anti-Patterns — NEVER do these things

- NEVER deploy a backup plan without verifying that tagged resources
  exist. The backup service does not warn on empty selection. A plan
  matching zero resources silently backs up nothing.

- NEVER enable vault lock in COMPLIANCE mode without GOVERNANCE testing.
  COMPLIANCE mode is irreversible. A retention typo commits you to
  decades of storage costs.

- NEVER configure cold storage transition without documenting thaw time.
  Cold storage restores take hours. If the RTO is 1 hour, cold storage
  at day 31 breaks the SLA.

- NEVER assume cross-account backup works without the destination KMS
  key policy. The source account needs `kms:Decrypt` and
  `kms:GenerateDataKey` on the destination key.

- NEVER skip restore testing. An untested backup is a liability. Schedule
  restore tests at a frequency mapped to the application RTO.

- NEVER use the Default backup vault for production. Create named vaults
  with explicit access policies and notifications.

- NEVER configure on-demand backup without a DLQ. EventBridge delivers
  asynchronously; failed triggers are silently dropped.

- NEVER rely solely on backup reports for compliance. Pair reports with
  restore-test logs for audit completeness.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before vault lock, plan creation, or
  lifecycle changes, emit: `CONFIRM: About to <action> for vault <vault>
  in account <account>. This affects <consequence>. Proceed? (yes/no)`

- **Before enabling vault lock in COMPLIANCE mode**, test in GOVERNANCE
  mode for at least 3 days.

- **Before deploying a lifecycle transition**, verify the RTO requirement
  against cold storage thaw time.

## Appendix A — Backup plan templates

| Template | Rule | Hot retention | Cold retention | Cross-region | Vault lock |
|---|---|---|---|---|---|
| dev-minimal | Daily | 7d | None | No | No |
| prod-standard | Daily + Weekly | 7d + 30d | 90d | Yes | GOVERNANCE |
| compliance-strict | Daily + Monthly | 7d | 365d-2555d | Yes | COMPLIANCE |
| pitr-continuous | Continuous | 35d | None | Optional | Optional |

## Appendix B — Decision tree

```
Is compliance (WORM) required?
+-- Yes -> Vault lock COMPLIANCE mode + lifecycle to cold + restore testing
|         AUTOMATION_DEPLOYED if vault + plan + testing all configured
+-- No  -> Is this a production workload?
          +-- Yes -> Named vault + GOVERNANCE lock + lifecycle tiering
          |         + cross-region copy + restore testing
          |         AUTOMATION_DEPLOYED if all present
          +-- No  -> Default vault OK + simple daily plan
                    AUTOMATION_DEPLOYED if tag scope non-empty
```

## Recent AWS features (2024-2026)

- **Backup vault lock GA (2024):** WORM compliance for backup vaults.
  GOVERNANCE mode for testing; COMPLIANCE mode for production.
- **Restore testing automation (2024-2025):** Scheduled Lambda-driven
  restore testing with CloudWatch metrics for RTO/RPO tracking.
- **Organizations backup policies (2024):** Centralized backup plan
  management across all member accounts with policy inheritance.
- **Backup frameworks (2025):** Compliance controls for backup frequency,
  retention, and encryption, with automated reporting.
- **Cross-account backup via KMS grants (2025-2026):** Simplified KMS key
  sharing for cross-account backup without manual key policy management.

## Expert heuristic: blast radius of vault lock

> ALWAYS test vault lock in GOVERNANCE mode for at least 3 days before
> switching to COMPLIANCE mode. A COMPLIANCE lock with a mistyped
> retention period is an irreversible commitment that can cost thousands
> in unnecessary storage.

**Pre-production validation protocol:**

1. Create vault. Enable GOVERNANCE lock with `ChangeableForDays=3`.
2. Run backup + restore cycle. Verify both succeed.
3. Test lock enforcement: attempt early deletion (should fail).
4. After 3 days, if all checks pass, switch to COMPLIANCE mode.
5. Verify with `describe-backup-vault` that mode is COMPLIANCE and
   retention values are correct.

## Domain

AWS CloudOps / Storage Automation — Backup-driven data protection.

## AWS documentation

- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vault-lock.html
- **Backup Plans** — https://docs.aws.amazon.com/aws-backup/latest/devguide/about-backup-plans.html
- **Cross-Account Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-account-backup.html
- **Organizations Backup Policies** — https://docs.aws.amazon.com/aws-backup/latest/devguide/orgs-assign-backup-policies.html
- **AWS Backup Restore** — https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-data.html
- **AWS Backup Frameworks** — https://docs.aws.amazon.com/aws-backup/latest/devguide/frameworks.html
