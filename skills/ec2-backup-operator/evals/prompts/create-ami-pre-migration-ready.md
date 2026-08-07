# Eval prompt: create-ami-pre-migration-ready

Plan the following AMI creation and emit the standard VERDICT block.

Operation: create-image
Target: i-0prodapp123456789ab (prod webapp, running)
AMI name: prod-webapp-pre-migration-2026-08-07
Reboot tolerance: --no-reboot=true accepted (webapp is stateless; DB has
  its own snapshot)

```json
{
  "Instance": {
    "InstanceId": "i-0prodapp123456789ab",
    "State": "running",
    "BlockDeviceMappings": [
      {"DeviceName": "/dev/sda1", "Ebs": {"VolumeId": "vol-0root123", "State": "in-use"}},
      {"DeviceName": "/dev/sdb", "Ebs": {"VolumeId": "vol-0logs123", "State": "in-use"}},
      {"DeviceName": "/dev/sdc", "Ebs": {"VolumeId": "vol-0data123", "State": "in-use"}}
    ],
    "IamInstanceProfile": "arn:aws:iam::111111111111:instance-profile/prod-webapp",
    "Architecture": "x86_64"
  },
  "AMINameUniqueness": {
    "Check": "describe-images --owners self --filters Name=name,Values=prod-webapp-pre-migration-2026-08-07",
    "Result": "empty"
  },
  "CallerIAM": {
    "Permissions": ["ec2:CreateImage on instance ARN confirmed"]
  }
}
```

Emit the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NEW_RESOURCE, REBOOT, NOTES).
