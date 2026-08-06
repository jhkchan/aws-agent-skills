# Eval prompt: archived-finding

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: CloudTrail.1 (CloudTrail Should Be Enabled)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "us-east-1",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/CloudTrail.1",
  "Compliance": {
    "Status": "FAILED",
    "StatusReasons": []
  },
  "Workflow": {
    "Status": "RESOLVED"
  },
  "RecordState": "ARCHIVED",
  "Severity": {
    "Label": "HIGH"
  },
  "UpdatedAt": "2026-06-01T12:00:00Z",
  "FirstObservedAt": "2026-05-01T08:00:00Z",
  "Resources": [
    {
      "Type": "Aws::CloudTrail::Trail",
      "Id": "arn:aws:cloudtrail:us-east-1:123456789012:trail/old-trail"
    }
  ]
}
```
