# Eval prompt: install-blocked-no-patch-group

Plan the following SSM Patch Manager Install operation and emit the
standard VERDICT block.

Operation: install
Target: i-0fedcba9876543210 (Amazon Linux 2)
Operator intent: apply the prod-linux-critical baseline rules

```json
{
  "Instance": {
    "InstanceId": "i-0fedcba9876543210",
    "PingStatus": "Active",
    "LastPingDateTime": "2026-08-07T02:28:00Z",
    "ResourceType": "EC2Instance",
    "PlatformType": "Linux",
    "PlatformName": "Amazon Linux",
    "PlatformVersion": "2.0.20240620.0",
    "IamRoleARN": "arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role"
  },
  "EC2": {
    "State": "running",
    "RootVolumeFreeGB": 22,
    "Tags": {"env": "prod"}
  },
  "EffectiveBaseline": {
    "BaselineId": "arn:aws:ssm:us-east-1:733311325942:patchbaseline/pb-0fb1df32",
    "OperatingSystem": "AMAZON_LINUX_2",
    "Name": "AWS-AmazonLinux2DefaultPatchBaseline",
    "Owner": "AWS",
    "Description": "Default baseline for Amazon Linux 2 provided by AWS."
  },
  "CustomBaselineAvailable": {
    "BaselineId": "pb-0aaa1234",
    "Name": "prod-linux-critical",
    "NotLinkedReason": "Instance has no 'Patch Group' tag matching the baseline Name"
  }
}
```

Emit the standard VERDICT block. If the pre-checks fail, surface the
specific remediation that links the instance to the operator's intended
baseline.
