# Baseline (no-skill) response: security-hub-missing

This file captures what a generic assistant produces WITHOUT the
cloudtrail-alert-automator skill loaded.

---

To send CloudTrail alerts to Security Hub, you can use the
BatchImportFindings API in your Lambda function. Create a custom
finding with the event details and import it.

```python
securityhub.batch_import_findings(Findings=[{
    'Id': 'some-unique-id',
    'Severity': {'Label': 'HIGH'},
    'Title': 'IAM Policy Change Detected',
    ...
}])
```

You'll need to make sure Security Hub is enabled in your account first.
If it's not enabled, the API calls will fail.

Set up the EventBridge rule for AttachRolePolicy and CreateAccessKey,
wire it to the Lambda, and have the Lambda publish to both SNS and
Security Hub.
