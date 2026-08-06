# Eval prompt: not-available-no-resources

Classify the following AWS Security Hub control finding against the compliance
verdict framework. Emit the standard VERDICT block (CONTROL, VERDICT, REASON,
SEVERITY, REMEDIATION).

Control: Redshift.1 (Redshift Clusters Public Access)
Finding JSON (ASFF):

```json
{
  "AwsAccountId": "123456789012",
  "Region": "us-east-1",
  "GeneratorId": "arn:aws:securityhub:::ruleset/foundational-security-best-practices/v/1.0.0/Redshift.1",
  "Compliance": {
    "Status": "NOT_AVAILABLE",
    "StatusReasons": [
      {
        "Code": "NO_RESOURCES",
        "Description": "No Redshift clusters found in this account."
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
