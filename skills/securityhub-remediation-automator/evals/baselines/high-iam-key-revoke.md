# Baseline (no-skill) response: high-iam-key-revoke

This file captures what a generic assistant produces WITHOUT the
securityhub-remediation-automator skill loaded.

---

For the IAM unused access key finding, you can use the SSM runbook
AWS-IAMRevokeUnusedAccessKey to deactivate the key automatically. Wire
it through EventBridge when Security Hub generates the finding.

Be careful to check if the key is actually in use before revoking it.
Maybe look at CloudTrail logs. You should use
`batch-update-findings` to update the workflow status after.

The EventBridge rule would filter on the severity and finding type.
Configure the Lambda to call SSM start-automation-execution.
