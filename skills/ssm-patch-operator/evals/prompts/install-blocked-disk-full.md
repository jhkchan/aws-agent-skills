# Eval prompt: install-blocked-disk-full

Plan the following SSM Patch Manager Install operation and emit the
standard VERDICT block.

Operation: install
Target: i-0full00000012345 (RHEL 9, prod worker)

```json
{
  "Instance": {
    "InstanceId": "i-0full00000012345",
    "PingStatus": "Active",
    "LastPingDateTime": "2026-08-07T02:31:00Z",
    "ResourceType": "EC2Instance",
    "PlatformType": "Linux",
    "PlatformName": "Red Hat Enterprise Linux",
    "PlatformVersion": "9.4",
    "IamRoleARN": "arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role"
  },
  "EC2": {
    "State": "running",
    "RootVolumeFreeGB": 0.8,
    "Tags": {"Patch Group": "prod-rhel"}
  },
  "EffectiveBaseline": {
    "BaselineId": "pb-0rhel-prod",
    "OperatingSystem": "REDHAT_ENTERPRISE_LINUX_9",
    "Name": "prod-rhel",
    "ApprovalRules": {
      "PatchRules": [
        {
          "PatchFilterGroup": [
            {"Key": "CLASSIFICATION", "Values": ["Security"]},
            {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
          ],
          "ApproveAfterDays": 7,
          "ComplianceLevel": "CRITICAL"
        }
      ]
    },
    "QualifyingPatchCount": 8
  },
  "MaintenanceWindow": {"WindowId": "mw-0ccc", "MinutesRemaining": 95},
  "FreeDiskCheck": {
    "Command": "aws ssm send-command --document-name AWS-RunShellScript --parameters commands=[\"df -m /\"]",
    "FreeMBOnRoot": 819
  }
}
```

Emit the standard VERDICT block. If pre-checks fail, surface the
specific disk-remediation path before retry.
