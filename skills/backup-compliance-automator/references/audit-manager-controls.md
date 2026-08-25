# Backup Audit Manager Control Library — Reference

This reference catalogs the Backup Audit Manager control library by
category, with parameter schema, evaluation cadence, and remediation
guidance per control. Use alongside the Backup Compliance Automator
SKILL.md.

## Control categories

| Category | Controls |
|---|---|
| Plan existence | BACKUP_PLAN_EXISTENCE, BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN |
| Recovery point integrity | BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED, BACKUP_RECOVERY_POINT_MINIMUM_RETENTION, BACKUP_RECOVERY_POINT_ENCRYPTED |
| Recency | BACKUP_REPORT_LAST_BACKUP_AGE, BACKUP_REPORT_LAST_RESTORE_AGE |
| Region isolation | BACKUP_VARIANT_WITH_REGION_ISOLATION |
| Resource coverage | BACKUP_RECOVERY_POINT_NOT_EXPIRED, BACKUP_PLAN_FREQUENCY |

## Control detail

### BACKUP_PLAN_EXISTENCE
- **Checks:** At least one backup plan exists per resource type in scope.
- **Parameters:** `ResourceType` (optional — defaults to all types in the
  framework scope).
- **Passes when:** A backup plan exists for the resource type.
- **Fails when:** No plan covers the resource type.
- **Remediation:** Create a backup plan for the missing resource type.

### BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN
- **Checks:** All resources matching the framework tag scope are
  associated with a backup plan that has produced at least one recovery
  point.
- **Parameters:** `TagKey`, `TagValue`.
- **Passes when:** Every tagged resource has at least one recovery point
  in the last evaluation window.
- **Fails when:** A tagged resource has no recovery point (never backed
  up) or the plan exists but never ran.
- **Remediation:** Tag the resource to a plan; verify the plan's schedule
  has fired at least once.

### BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED
- **Checks:** Vault Lock is configured on the vault(s) holding in-scope
  recovery points.
- **Parameters:** `ResourceType` (optional).
- **Passes when:** The vault has Vault Lock in COMPLIANCE or GOVERNANCE
  mode.
- **Fails when:** No Vault Lock configured (recovery points can be
  manually deleted).
- **Remediation:** Configure Vault Lock on the vault. Use COMPLIANCE mode
  for regulated workloads.

### BACKUP_RECOVERY_POINT_MINIMUM_RETENTION
- **Checks:** Recovery points meet or exceed the minimum retention.
- **Parameters:** `MinRetentionDays`.
- **Passes when:** Recovery point's lifecycle `DeleteAfterDays` >=
  `MinRetentionDays`.
- **Fails when:** Recovery point would be deleted before the minimum.
- **Remediation:** Update the backup plan lifecycle to meet the minimum.

### BACKUP_RECOVERY_POINT_ENCRYPTED
- **Checks:** Recovery points are encrypted with a customer-managed KMS
  key.
- **Parameters:** `ResourceType` (optional).
- **Passes when:** Recovery point's encryption key is a CMK (not AWS
  managed default).
- **Fails when:** Recovery point uses the default AWS-managed key or is
  unencrypted.
- **Remediation:** Configure the backup vault with a CMK; re-encrypt
  existing recovery points via restore + re-backup.

### BACKUP_REPORT_LAST_BACKUP_AGE
- **Checks:** Most recent recovery point is within `maxAgeInDays`.
- **Parameters:** `maxAgeInDays`.
- **Passes when:** At least one recovery point exists within the window.
- **Fails when:** Newest recovery point is older than `maxAgeInDays`.
- **Remediation:** Investigate why the plan did not run (schedule, IAM,
  throttling).

### BACKUP_REPORT_LAST_RESTORE_AGE
- **Checks:** Most recent restore was performed within `maxAgeInDays`.
- **Parameters:** `maxAgeInDays`.
- **Passes when:** At least one restore was performed within the window.
- **Fails when:** No restore in the window (restore drill missing).
- **Remediation:** Run a restore drill on a tier-1 resource; document RTO.

### BACKUP_VARIANT_WITH_REGION_ISOLATION
- **Checks:** At least one cross-region copy exists for in-scope recovery
  points.
- **Parameters:** `PrimaryRegion`, `SecondaryRegion`.
- **Passes when:** Recovery point has a copy in the secondary region.
- **Fails when:** No cross-region copy (single-region only).
- **Remediation:** Add a `COPY_ACTION` to the backup plan targeting the
  secondary region vault.

## Framework presets

AWS provides managed framework templates aligned to common compliance
standards. Use as a starting point; add custom controls as needed.

| Preset | Controls included | Notes |
|---|---|---|
| `NIST_800_53` | Plan existence, encryption, retention | Moderate baseline |
| `PCI_DSS` | Encryption, manual-deletion-disabled, min-retention | Cardholder data scope |
| `HIPAA` | Encryption (CMK), LOCK_MODE vault, restore drill | PHI scope |
| `CIS_AWS_1_4` | Plan existence, manual-deletion-disabled | Foundational |

## Manual controls (Lambda-backed)

For checks not covered by the control library (e.g., "every EC2 instance
with tag `compliance=hipaa` must have a recovery point no older than 6
hours"), build a manual control:

```python
import boto3, datetime
backup = boto3.client('backup')

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    # Find all hipaa-tagged instances
    instances = ec2.describe_instances(Filters=[
        {'Name':'tag:compliance','Values':['hipaa']}
    ])
    instance_ids = []
    for r in instances['Reservations']:
        for i in r['Instances']:
            instance_ids.append(i['InstanceId'])
    # Check each has a recovery point <= 6h old
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)
    non_compliant = []
    for iid in instance_ids:
        rps = backup.list_recovery_points_by_resource(
            ResourceArn=f"arn:aws:ec2:us-east-1::{iid}"
        )
        recent = [
            rp for rp in rps['RecoveryPoints']
            if rp['CreationDate'].replace(tzinfo=datetime.timezone.utc) > cutoff
        ]
        if not recent:
            non_compliant.append(iid)
    return {
        'compliant': len(instance_ids) - len(non_compliant),
        'non_compliant': len(non_compliant),
        'non_compliant_ids': non_compliant
    }
```

## Evaluation cadence best practice

| Criticality | Cadence | Controls evaluated |
|---|---|---|
| Tier 0 | Daily | All controls |
| Tier 1 | Weekly | Encryption, retention, recency |
| Tier 2 | Monthly | Plan existence, coverage |

Cadence is configured per framework via EventBridge Scheduler triggering
the report plan (which forces evaluation). Daily evaluation of large
frameworks (hundreds of resources) adds cost — balance against freshness.

## Common pitfalls

- **Controls do not modify state.** A failing control does not fix the
  problem — it reports. Build separate remediation (Lambda or human).
- **Vault Lock check passes even in GOVERNANCE mode.** For HIPAA / SOC2,
  add a manual control verifying LOCK_MODE specifically.
- **Cross-region isolation requires the copy to actually exist, not just
  be configured.** If the copy job never ran, the control fails.
- **Restore drill control requires an actual restore job, not just a
  plan to restore.** Run the drill; document the RTO.
- **The framework scope is tag-based.** Untagged resources are invisible
  to Audit Manager — pair with a tagging-governance skill.

## Audit Manager gotchas — controls evaluate actual state
**Gotchas:** Controls are evaluated against actual AWS Backup state, not
against the plan. A control `BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN`
fails if a resource is tagged for a plan but the plan never produced a
recovery point. The control library is fixed by AWS — custom controls
require Lambda-backed manual controls.

## Audit template report plan CLI

```bash
aws backup audit-manager create-report-plan \
  --report-plan-name soc2-monthly-compliance \
  --report-plan-description "Monthly SOC2 backup compliance report" \
  --report-setting '{"ReportTemplate":"COMPLIANCE","Frameworks":["arn:aws:backup:us-east-1:111111111111:framework:soc2-backup-compliance"]}' \
  --reportDeliveryConfig={"S3BucketName":"backup-compliance-reports","S3KeyPrefix":"soc2/2026/"} \
  --idempotencyToken "$(uuidgen)"
```
