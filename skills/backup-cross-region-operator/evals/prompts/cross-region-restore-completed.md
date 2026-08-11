# Eval prompt: cross-region-restore-completed

Plan the following AWS Backup cross-region restore and emit the
standard VERDICT block (post-verification form).

Operation: start-cross-region-restore (post-verification)
DR region: us-west-2 (restore runs here)
Vault: dr-vault
RecoveryPointArn: arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8
Resource type: EC2
Metadata: InstanceId=i-restored-xregion, SubnetId=subnet-xyz, SecurityGroupIds=sg-xyz, InstanceType=t3.medium

```json
{
  "RestorePreCheck": {
    "describe-recovery-point.5-6-7-8.us-west-2": {
      "Status": "COMPLETED",
      "ResourceType": "EC2",
      "EncryptionKeyArn": "arn:aws:kms:us-west-2:111111111111:key/xyz"
    },
    "destination_kms_grant": {
      "kms:Decrypt to AWSBackupDefaultServiceRole": true
    },
    "caller_iam": {
      "role": "AWSBackupDefaultServiceRole",
      "permissions": ["backup:StartRestoreJob", "ec2:RunInstances",
                      "kms:Decrypt"]
    }
  },
  "RestoreExecution": {
    "executed_cli": "aws backup start-restore-job --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 --metadata {...} --region us-west-2",
    "returned_restore_job_id": "RESTORE-XREGION-XYZ"
  },
  "RestorePostVerify": {
    "describe-restore-job.RESTORE-XREGION-XYZ.us-west-2": {
      "Status": "COMPLETED",
      "CreatedResourceArn": "arn:aws:ec2:us-west-2:111111111111:instance/i-restored-xregion",
      "CompletionDate": "2026-08-09T16:42:17Z"
    },
    "ec2.describe-instances.i-restored-xregion.us-west-2": {
      "State": "running",
      "LaunchTime": "2026-08-09T16:35:02Z"
    }
  }
}
```
