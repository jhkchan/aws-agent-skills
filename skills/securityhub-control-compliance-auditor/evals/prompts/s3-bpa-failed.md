# Eval prompt: s3-bpa-failed

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: S3.2 (S3 Bucket-Level Public Access Prohibition)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "us-east-1",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/S3.2",
  "Compliance": {
    "Status": "FAILED",
    "StatusReasons": []
  },
  "Workflow": {
    "Status": "NEW"
  },
  "RecordState": "ACTIVE",
  "Severity": {
    "Label": "HIGH"
  },
  "UpdatedAt": "2026-08-01T12:00:00Z",
  "FirstObservedAt": "2026-07-15T08:00:00Z",
  "Resources": [
    {
      "Type": "Aws::S3::Bucket",
      "Id": "arn:aws:s3:::app-uploads-prod"
    }
  ]
}
```
