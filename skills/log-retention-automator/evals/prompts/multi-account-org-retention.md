# Eval prompt: multi-account-org-retention

Design a multi-account CloudWatch Logs retention rollout across an
AWS Organizations fleet. Emit the standard RETENTION block (POLICY,
TRIGGER, ARCHIVAL, VERDICT, TEMPLATE).

Design reference: multi-account-org-retention
Account: 111111111111 (management account)
Region: us-east-1

Organization: 45 member accounts across 3 OUs.
Requirement: deploy auto-retention to all accounts.
Standard tier: prod=90d, staging=30d, dev=7d, default=14d.
StackSet: SERVICE_MANAGED permission model.
Centralized audit: management account Lambda sweeps daily.

Emit the standard RETENTION block. Include the CloudFormation StackSet
create command, cross-account IAM role trust policy, and the
centralized audit Lambda design.
