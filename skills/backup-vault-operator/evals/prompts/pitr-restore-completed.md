# Eval prompt: pitr-restore-completed

A point-in-time restore for EC2 has been executed. Post-verification
checks have already passed. Emit the standard VERDICT block in
post-verification form.

Operation: start-restore (post-verification after execution)
Vault: prod-compliance-vault
RecoveryPointArn: arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4
Resource type: EC2
Metadata:
  InstanceId: i-restored-pitr
  SubnetId: subnet-abc123
  SecurityGroupIds: sg-abc123
  InstanceType: t3.medium
  RestoreTime: 2026-08-09T14:30:00Z

```json
{
  "RecoveryPoint": {
    "describe-recovery-point": {
      "Status": "COMPLETED",
      "ContinuousBackup": true,
      "ResourceType": "EC2"
    },
    "window_check": {
      "RestoreTime": "2026-08-09T14:30:00Z",
      "within_35_day_window": true
    }
  },
  "ExecutedCLI": "aws backup start-restore-job --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 --metadata {\"InstanceId\":\"i-restored-pitr\",\"SubnetId\":\"subnet-abc123\",\"SecurityGroupIds\":\"sg-abc123\",\"InstanceType\":\"t3.medium\",\"RestoreTime\":\"2026-08-09T14:30:00Z\"} --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole --resource-type EC2",
  "PostExecutionChecks": {
    "describe-restore-job.RESTORE-JOB-XYZ": {
      "Status": "COMPLETED",
      "CreatedResourceArn": "arn:aws:ec2:us-east-1:111111111111:instance/i-restored-pitr",
      "CompletionDate": "2026-08-09T14:42:17Z"
    },
    "ec2.describe-instances.i-restored-pitr": {
      "State": "running",
      "LaunchTime": "2026-08-09T14:35:02Z"
    }
  }
}
```
