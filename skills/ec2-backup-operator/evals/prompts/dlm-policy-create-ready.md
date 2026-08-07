# Eval prompt: dlm-policy-create-ready

Plan the following DLM lifecycle policy creation and emit the standard
VERDICT block.

Operation: create-lifecycle-policy (DLM)
PolicyType: EBS_SNAPSHOT_MANAGEMENT
Target tags: Key=BackupSchedule, Value=daily
Schedule: rate(1 day), Times=["03:00"]
Retention: count=7
IAM role: arn:aws:iam::111111111111:role/service-role/AWS-DLM-LifeCycleRole
  (trusts dlm.amazonaws.com, has ec2:CreateSnapshot/CreateTags/DeleteSnapshot)

```json
{
  "Policy": {
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "Description": "Daily snapshots of volumes tagged BackupSchedule=daily",
    "State": "ENABLED",
    "TargetTags": [{"Key": "BackupSchedule", "Value": "daily"}],
    "Schedules": [
      {
        "Name": "Daily",
        "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
        "RetainRule": {"Count": 7},
        "CopyTags": true
      }
    ]
  },
  "TargetMembership": {
    "Command": "ec2 describe-volumes --filters Name=tag:BackupSchedule,Values=daily",
    "MatchCount": 10
  },
  "IAMRole": {
    "RoleArn": "arn:aws:iam::111111111111:role/service-role/AWS-DLM-LifeCycleRole",
    "Trusts": "dlm.amazonaws.com",
    "Permissions": ["ec2:CreateSnapshot", "ec2:CreateTags", "ec2:DeleteSnapshot"]
  },
  "Region": "us-east-1"
}
```

Emit the standard VERDICT block including the exact
create-lifecycle-policy command and the CONFIRM gate.
