# Eval prompt: not-available-service-disabled

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: Config.1 (AWS Config Enabled)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "eu-west-2",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/Config.1",
  "Compliance": {
    "Status": "NOT_AVAILABLE",
    "StatusReasons": [
      {
        "Code": "SUPPORTED_SERVICE_NOT_ENABLED",
        "Description": "AWS Config is not enabled in eu-west-2."
      }
    ]
  },
  "Workflow": {
    "Status": "NEW"
  },
  "RecordState": "ACTIVE",
  "Severity": {
    "Label": "MEDIUM"
  },
  "UpdatedAt": "2026-08-01T12:00:00Z",
  "Resources": []
}
```
