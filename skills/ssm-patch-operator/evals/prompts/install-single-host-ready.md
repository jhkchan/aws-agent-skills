# Eval prompt: install-single-host-ready

Plan the following SSM Patch Manager Install operation and emit the standard
VERDICT block.

Operation: install
Target: i-0abc123def456789a (Amazon Linux 2, prod web server)
Baseline: pb-0aaa1234 (custom, prod-linux-critical, via Patch Group tag
  "prod-linux-critical")
Reboot tolerance: NoReboot=true preferred (kernel patches will activate on
  the next maintenance-window reboot)

```json
{
  "Instance": {
    "InstanceId": "i-0abc123def456789a",
    "PingStatus": "Active",
    "LastPingDateTime": "2026-08-07T02:30:00Z",
    "ResourceType": "EC2Instance",
    "PlatformType": "Linux",
    "PlatformName": "Amazon Linux",
    "PlatformVersion": "2.0.20240620.0",
    "IamRoleARN": "arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role"
  },
  "EC2": {
    "State": "running",
    "RootVolumeFreeGB": 18,
    "Tags": {"Patch Group": "prod-linux-critical", "env": "prod"}
  },
  "EffectiveBaseline": {
    "BaselineId": "pb-0aaa1234",
    "OperatingSystem": "AMAZON_LINUX_2",
    "Name": "prod-linux-critical",
    "ApprovalRules": {
      "PatchRules": [
        {
          "PatchFilterGroup": [
            {"Key": "CLASSIFICATION", "Values": ["Security"]},
            {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
          ],
          "ApproveAfterDays": 3,
          "ComplianceLevel": "CRITICAL",
          "EnableNonSecurity": false
        }
      ]
    },
    "QualifyingPatchCount": 14
  },
  "MaintenanceWindow": {"WindowId": "mw-0aaa", "MinutesRemaining": 95}
}
```

Emit the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, COMPLIANCE_DELTA, REBOOT, NOTES).
