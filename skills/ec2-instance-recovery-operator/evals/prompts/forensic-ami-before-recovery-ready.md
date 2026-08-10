# Eval prompt: forensic-ami-before-recovery-ready

Plan the following EC2 forensic AMI capture and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: forensic-ami
Instance: i-0abcdef1234567890

```json
{
  "InstanceStatus": {
    "State": "running",
    "SystemStatus": {"Status": "impaired"},
    "InstanceStatus": {"Status": "ok"}
  },
  "InstanceDetails": {
    "RootDeviceType": "ebs",
    "BlockDeviceMappings": [
      {"DeviceName": "/dev/xvda", "Ebs": {"VolumeId": "vol-0abc", "DeleteOnTermination": true}},
      {"DeviceName": "/dev/xvdb", "Ebs": {"VolumeId": "vol-0def", "DeleteOnTermination": false}}
    ]
  },
  "ExistingAmis": [],
  "NoRebootRequested": true
}
```
