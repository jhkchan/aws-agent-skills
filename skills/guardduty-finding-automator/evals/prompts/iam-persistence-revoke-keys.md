# Eval prompt: iam-persistence-revoke-keys

Design an automated GuardDuty response workflow for the following finding.
Emit the standard AUTOMATION block.

Design reference: iam-persistence-revoke-keys
Account: 111111111111
Region: us-east-1

GuardDuty finding type: Persistence:IAMUser/AccessKeyCreated
Severity: 8.0 (HIGH)
Sample resource: AIDACKCEVSQ6C2EXAMPLE (compromised IAM user)
New key created: AKIAIOSFODNN7EXAMPLE (attacker-created)
The key was last used 3 hours ago.
SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
Lambda: guardduty-auto-remediation
Security Hub: enabled
Pre-prod validation: completed.
