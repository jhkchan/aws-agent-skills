# Eval prompt: suppressed-failed

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: EC2.15 (EC2 Security Group 0.0.0.0/0 on Admin Port)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "us-east-1",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/EC2.15",
  "Compliance": {
    "Status": "FAILED",
    "StatusReasons": []
  },
  "Workflow": {
    "Status": "SUPPRESSED"
  },
  "RecordState": "ACTIVE",
  "Severity": {
    "Label": "HIGH"
  },
  "UpdatedAt": "2026-07-20T10:00:00Z",
  "FirstObservedAt": "2026-06-01T08:00:00Z",
  "Resources": [
    {
      "Type": "Aws::EC2::SecurityGroup",
      "Id": "arn:aws:ec2:us-east-1:123456789012:security-group/sg-0abc123"
    }
  ]
}
```
