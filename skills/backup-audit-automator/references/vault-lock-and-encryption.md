# Vault Lock and Encryption — Backup Audit Automator

Deep reference on AWS Backup Vault Lock modes (compliance vs
governance, immutability semantics, retention enforcement), KMS
encryption on recovery points (key presence audit, default vs
customer-managed keys), and cross-region replication auditing. Loaded
on demand by the skill.

## Vault Lock modes

### Compliance mode (immutable)

Compliance mode is the strictest Vault Lock. Once enabled, NO user
(including root) can delete the vault, delete recovery points within
the retention period, or change the lock configuration.

| Property | Value |
|---|---|
| Immutability | PERMANENT — cannot be reversed or modified |
| Retention enforcement | STRICT — recovery points cannot be deleted until retention expires |
| Who can override | NO ONE (including root) |
| Regulatory alignment | SEC 17a-4, FINRA 4511, HIPAA, CFTC 1.31, SOX |
| Minimum retention | Configurable (set at creation) |

**Enable compliance mode:**

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "compliant-vault" \
  --min-retention-days 365 \
  --mode "COMPLIANCE"
```

**CRITICAL:** once compliance mode is enabled, it CANNOT be disabled.
The retention period cannot be shortened. Verify the configuration
before applying.

### Governance mode (overridable)

Governance mode provides operational guardrails. Privileged users can
override the lock to delete recovery points before retention expires.

| Property | Value |
|---|---|
| Immutability | OVERRIDABLE — can be reversed by privileged users |
| Retention enforcement | ADVISORY — can be bypassed with proper permissions |
| Who can override | Users with `backup:DeleteBackupVaultLockConfiguration` or sufficient IAM permissions |
| Regulatory alignment | NOT suitable for regulatory WORM (does not meet SEC/FINRA requirements) |
| Use case | Preventing accidental deletion, operational discipline |

**Enable governance mode:**

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "governance-vault" \
  --min-retention-days 90 \
  --mode "GOVERNANCE"
```

### Verifying Vault Lock mode

```bash
# Check if Vault Lock is enabled and what mode
aws backup describe-backup-vault \
  --backup-vault-name "compliant-vault" \
  --query '{Name:BackupVaultName,Type:VaultType,Locked:LockedDate,MinRetention:MinRetentionDays}'

# VaultType values:
# "COMPLIANCE" = immutable Vault Lock
# "GOVERNANCE" = overridable Vault Lock
# (empty/null) = no Vault Lock
```

### Audit checklist for Vault Lock

| Check | Method | Expected |
|---|---|---|
| Vault Lock enabled | `describe-backup-vault` | VaultType is set |
| Mode is compliance | `describe-backup-vault` | VaultType = "COMPLIANCE" |
| Retention period adequate | `describe-backup-vault` | MinRetentionDays >= required minimum |
| Lock cannot be removed | (compliance mode property) | Permanent — verify at creation |

## KMS encryption on recovery points

### How backup encryption works

AWS Backup encrypts recovery points using KMS keys. The KMS key is
specified in the backup plan's advanced settings. If no key is
specified, AWS Backup uses the default AWS-managed key for the
resource type.

### Auditing encryption on recovery points

```bash
# List recovery points and check for KMS key
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name "my-vault" \
  --query 'RecoveryPoints[*].{
    ARN:RecoveryPointArn,
    Type:ResourceType,
    EncKey:EncryptionKeyArn,
    Created:CreationDate
  }' \
  --output table

# Find recovery points WITHOUT KMS encryption (findings)
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name "my-vault" \
  --query 'RecoveryPoints[?EncryptionKeyArn==`null`].[RecoveryPointArn,ResourceType]' \
  --output table
```

### Encryption findings classification

| Encryption Status | Classification | Action |
|---|---|---|
| Customer-managed KMS key (cmk) | PASS | No action |
| AWS-managed KMS key (aws/service-name) | WARN | Consider migrating to CMK for key control |
| No encryption key (null) | FAIL | Update backup plan to include KMS key |

### Specifying KMS key in backup plan

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "encrypted-backup-plan",
    "Rules": [{
      "RuleName": "daily-encrypted",
      "TargetBackupVaultName": "encrypted-vault",
      "ScheduleExpression": "cron(0 5 ? * * *)",
      "StartWindowMinutes": 480,
      "CompletionWindowMinutes": 10080,
      "CopyActions": []
    }],
    "AdvancedBackupSettings": [{
      "ResourceType": "EC2",
      "BackupOptions": {"WindowsVSS": "enabled"}
    }]
  }'
```

The KMS key for the vault is configured at vault creation:

```bash
aws backup create-backup-vault \
  --backup-vault-name "encrypted-vault" \
  --encryption-key-arn "arn:aws:kms:us-east-1:123456789012:key/abc-123"
```

## Cross-region replication audit

Verify that backup plans include cross-region copy actions for DR.

```bash
# Check if backup plan has cross-region copy actions
aws backup get-backup-plan \
  --backup-plan-id <plan-id> \
  --query 'BackupPlan.Rules[*].CopyActions'

# Empty CopyActions = no cross-region replication (finding)
# Non-empty CopyActions = cross-region copy configured (pass)
```

**For DR, at least one CopyAction should target a different region.**

```json
{
  "CopyActions": [{
    "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-vault",
    "Lifecycle": {"DeleteAfterDays": 180}
  }]
}
```

## Common audit findings and remediation

| Finding | Severity | Remediation |
|---|---|---|
| Resource not in any backup plan | HIGH | Add backup selection for the resource |
| Recovery point without KMS encryption | HIGH | Update backup plan with KMS key |
| No cross-region replication | MEDIUM | Add CopyAction targeting another region |
| Vault Lock in governance mode | MEDIUM | Switch to compliance mode for regulatory requirements |
| Retention below minimum threshold | MEDIUM | Update lifecycle to meet minimum retention days |
| Backup job failed | HIGH | Investigate failure, retry or fix resource |

## Expert heuristic: Vault Lock compliance vs governance

A baseline model may not distinguish the two Vault Lock modes. The
correct heuristic recognizes that compliance mode is IMMUTABLE and
governance mode is NOT.

```text
Vault Lock modes:

  COMPLIANCE mode:
    - Cannot be deleted or changed by ANY user (including root)
    - Retention period is enforced permanently
    - Once enabled, CANNOT be disabled
    - Required for: SEC 17a-4, FINRA 4511, HIPAA, CFTC 1.31
    - Use when: regulatory immutability is required

  GOVERNANCE mode:
    - Can be overridden by users with s3:PutBucketObjectLockConfiguration
      or backup:DeleteBackupVault permissions
    - Retention period is advisory (can be bypassed)
    - CAN be disabled by privileged users
    - Required for: operational guardrails (not regulatory)
    - Use when: preventing accidental deletion, but allowing override
```

**Key implication:** for regulatory compliance, ONLY compliance mode
satisfies immutability requirements. Governance mode does not meet
WORM requirements for SEC/FINRA/HIPAA. An audit must verify the mode,
not just whether Vault Lock is enabled.

## Expert heuristic: encryption audit checks KMS key presence

A baseline model may assume all recovery points are encrypted. The
correct heuristic recognizes that KMS encryption depends on the backup
plan configuration.

```text
Recovery point encryption audit:
  For each recovery point:
    1. Check if encryption key is present
    2. If KMS key present → PASS
    3. If no KMS key → FAIL (recovery point not encrypted with KMS)
    4. If AWS-managed default key → WARN (consider customer-managed key)

  Audit command:
    aws backup list-recovery-points-by-backup-vault \
      --backup-vault-name "my-vault" \
      --query 'RecoveryPoints[?EncryptionKeyArn==`null`]'
```
