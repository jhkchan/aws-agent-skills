# Eval prompt: cloudwatch-recovery-alarm-stop-start-ready

Plan the following EC2 instance recovery operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: stop-start (recover from SystemStatus impaired)
Instance: i-0abcdef1234567890

```json
{
  "InstanceStatus": {
    "State": "running",
    "SystemStatus": {"Status": "impaired"},
    "InstanceStatus": {"Status": "ok"},
    "Events": []
  },
  "InstanceDetails": {
    "InstanceType": "m5.2xlarge",
    "RootDeviceType": "ebs",
    "BlockDeviceMappings": [
      {"DeviceName": "/dev/xvda", "Ebs": {"VolumeId": "vol-0abc", "DeleteOnTermination": true}}
    ],
    "Placement": {"GroupName": "", "Tenancy": "default"},
    "CapacityReservationId": null
  },
  "AsgMembership": null,
  "ExistingRecoveryAlarms": [],
  "CallerPermissions": [
    "ec2:StopInstances",
    "ec2:StartInstances",
    "cloudwatch:PutMetricAlarm"
  ]
}
```
