# Eval prompt: start-cross-region-copy-ready

Plan the following AWS Backup cross-region copy job and emit the
standard VERDICT block.

Operation: start-copy
Source region: us-east-1
Source vault: prod-daily-vault
Recovery point ARN: arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4
Destination region: us-west-2
Destination vault ARN: arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault
IAM role: arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole

```json
{
  "CopyPreCheck": {
    "describe-recovery-point.1-2-3-4": {
      "Status": "COMPLETED",
      "ResourceType": "EC2",
      "BackupSizeInBytes": 8589934592
    },
    "describe-backup-vault.dr-vault.us-west-2": {
      "exists": true,
      "EncryptionKeyArn": "arn:aws:kms:us-west-2:111111111111:key/xyz"
    },
    "source_kms_policy": {
      "grants": ["kms:Decrypt to backup.us-east-1.amazonaws.com"]
    },
    "destination_kms_policy": {
      "grants": ["kms:GenerateDataKey to backup.us-west-2.amazonaws.com"]
    },
    "caller_iam": {
      "role": "AWSBackupDefaultServiceRole",
      "permissions": ["backup:StartCopyJob"]
    }
  }
}
```
