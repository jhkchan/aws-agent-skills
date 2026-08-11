# Baseline (no-skill) response: custom-finding-no-runbook

This file captures what a generic assistant produces WITHOUT the
securityhub-remediation-automator skill loaded.

---

For a custom finding about exposed credentials in Lambda environment
variables, you would need to write a custom Lambda function to handle
the remediation. There's no managed SSM runbook for this.

The Lambda would need to read the finding, get the function name,
rotate the credential in Secrets Manager, and update the environment
variable. Then update the finding status.

You can set up an EventBridge rule to trigger the Lambda on the finding.
You'll also need proper IAM permissions for Lambda, Secrets Manager, and
Security Hub.
