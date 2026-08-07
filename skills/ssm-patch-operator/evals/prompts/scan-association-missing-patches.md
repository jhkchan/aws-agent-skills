# Eval prompt: scan-association-missing-patches

Diagnose and remediate the following SSM patch drift. Emit the standard
VERDICT block for the safest remediation.

Operation: diagnose + remediate
Instance: i-0a1b2c3d4e5f67890 (Ubuntu 22.04)
Symptom: Association Status Success, but list-compliance-items shows
  ComplianceStatus NON_COMPLIANT with 12 missing Critical patches

```json
{
  "Instance": {
    "InstanceId": "i-0a1b2c3d4e5f67890",
    "PingStatus": "Active",
    "PlatformType": "Linux",
    "PlatformName": "Ubuntu",
    "PlatformVersion": "22.04",
    "IamRoleARN": "arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role"
  },
  "EC2": {
    "State": "running",
    "RootVolumeFreeGB": 14,
    "Tags": {"Patch Group": "prod-ubuntu"}
  },
  "Association": {
    "AssociationId": "0a1b2c3d-4567-8901-abcd-ef0123456789",
    "DocumentName": "AWS-RunPatchBaseline",
    "Parameters": {"Operation": ["Scan"]},
    "ScheduleExpression": "rate(1 day)",
    "LastExecutionDate": "2026-08-07T02:00:00Z",
    "Status": "Success"
  },
  "EffectiveBaseline": {
    "BaselineId": "pb-0ubuntu-prod",
    "OperatingSystem": "UBUNTU_22_04",
    "Name": "prod-ubuntu"
  },
  "Compliance": {
    "ComplianceStatus": "NON_COMPLIANT",
    "MissingCriticalCount": 12,
    "MissingImportantCount": 3
  }
}
```

Propose the safest remediation that preserves the existing targeting and
schedule. Emit the standard VERDICT block.
