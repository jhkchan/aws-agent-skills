# Diagnostic Commands — Backup Vault Compliance

Load-on-demand inventory, verification, and audit command listings for the Backup
Vault Compliance Automator skill.

## Step 1: Inventory the current backup state

```bash
# Vault inventory (name, encryption, lock state, recovery point count)
aws backup list-backup-vaults --query 'BackupVaultList[*].[BackupVaultName,EncryptionKeyArn,LockState,NumberOfRecoveryPoints]'

# Vault policy and lock state
aws backup get-backup-vault-policy --backup-vault-name <vault>
aws backup describe-backup-vault --backup-vault-name <vault> --query '[LockState,MinRetentionDays,VaultLockDate]'

# Recovery point encryption status
aws backup list-recovery-points-by-backup-vault --backup-vault-name <vault> \
  --query 'RecoveryPoints[*].[RecoveryPointArn,ResourceType,Status,EncryptionKeyArn]'

# Backup plans, selections, and copy jobs
aws backup list-backup-plans --query 'BackupPlansList[*].[BackupPlanId,BackupPlanName]'
aws backup list-backup-selections --backup-plan-id <plan-id>
aws backup list-copy-jobs --by-state COMPLETED
```

Surface in the output: vaults without policies, vaults without locks,
recovery points without encryption, resources without backup selections.

## Step 4: Verify recovery point encryption

Check each recovery point:

```python
import boto3

backup = boto3.client('backup')

def verify_encryption(vault_name, approved_kms_key_arn):
    paginator = backup.get_paginator('list_recovery_points_by_backup_vault')
    violations = []

    for page in paginator.paginate(BackupVaultName=vault_name):
        for rp in page['RecoveryPoints']:
            arn = rp['RecoveryPointArn']
            kms_key = rp.get('EncryptionKeyArn')

            if kms_key is None:
                violations.append(f"UNENCRYPTED: {arn} ({rp['ResourceType']})")
            elif kms_key != approved_kms_key_arn:
                violations.append(f"WRONG_KEY: {arn} uses {kms_key}, expected {approved_kms_key_arn}")

    return violations
```

## Step 5: Audit backup plan coverage — resource enumeration

```bash
# List all EC2 instances
aws ec2 describe-instances \
  --query 'Reservations[*].Instances[*].InstanceId' \
  --output text \
  --region us-east-1

# List all RDS instances
aws rds describe-db-instances \
  --query 'DBInstances[*].DBInstanceIdentifier' \
  --output text \
  --region us-east-1

# List all DynamoDB tables
aws dynamodb list-tables \
  --output text \
  --region us-east-1

# List backup selections
aws backup list-backup-plans \
  --output json \
  --region us-east-1
```

## Step 6: Validate cross-region replication

```bash
aws backup list-copy-jobs --by-state COMPLETED --output json --region us-east-1
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault-dr --region us-west-2
```
