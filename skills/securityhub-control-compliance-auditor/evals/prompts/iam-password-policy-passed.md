# Eval prompt: iam-password-policy-passed

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: IAM.7 (IAM Password Policy)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "us-east-1",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/IAM.7",
  "Compliance": {
    "Status": "PASSED",
    "StatusReasons": []
  },
  "Workflow": {
    "Status": "RESOLVED"
  },
  "RecordState": "ACTIVE",
  "Severity": {
    "Label": "MEDIUM"
  },
  "UpdatedAt": "2026-08-01T06:00:00Z",
  "Resources": [
    {
      "Type": "Aws::IAM::Account",
      "Id": "arn:aws:iam::123456789012:root"
    }
  ]
}
```
