# Eval prompt: multi-account-org-deployment

Design a multi-account GuardDuty automation pipeline for the following
Organizations environment. Emit the standard AUTOMATION block. Include
the cross-account EventBridge forwarding rule and the StackSet
deployment pattern.

Design reference: multi-account-org-deployment
Delegated admin account: 111111111111
Member accounts: 222222222222, 333333333333, 444444444444
Regions: us-east-1, us-west-2, eu-west-1
GuardDuty: enabled in all member accounts via delegated admin
Lambda remediation: guardduty-auto-remediation (deployed via StackSet)
Isolation SG: deployed to all VPCs via StackSet
SNS topic (centralized): arn:aws:sns:us-east-1:111111111111:guardduty-alerts
Pre-prod validation: completed in sandbox OU.
