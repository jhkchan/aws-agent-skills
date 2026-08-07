# Eval prompt: aws-backup-restore-ready

Plan the following AWS Backup restore and emit the standard VERDICT
block.

Operation: start-restore-job (AWS Backup, EC2)
Recovery point: arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g
Restore IAM role: arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole
  (trusts backup.amazonaws.com)
Target subnet: subnet-0prod (has capacity)

```json
{
  "RecoveryPoint": {
    "BackupVaultName": "prod-ec2-vault",
    "RecoveryPointArn": "arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g",
    "ResourceArn": "arn:aws:ec2:us-east-1:111111111111:instance/i-0source123",
    "Status": "COMPLETED",
    "CompletionDate": "2026-08-07T01:00:00Z",
    "Metadata": {
      "InstanceType": "t3.large",
      "SubnetId": "subnet-0prod",
      "SecurityGroupIds": ["sg-0prod"],
      "IamInstanceProfile": "arn:aws:iam::111111111111:instance-profile/prod-webapp"
    }
  },
  "RestoreIAMRole": {
    "RoleArn": "arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole",
    "TrustsBackup": true
  },
  "TargetSubnet": {
    "SubnetId": "subnet-0prod",
    "AvailableIpCount": 23
  }
}
```

Emit the standard VERDICT block including the exact start-restore-job
command with metadata, the CONFIRM gate, and the new-instance /
connection-string cutover notes.
