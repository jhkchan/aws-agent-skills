# Eval: self-managed-account-list

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SELF_MANAGED, admin + execution roles cited, multi-account, multi-region

## Prompt

Create a StackSet named config-baseline using SELF_MANAGED
permission model. Target accounts 111111111111,
222222222222, and 333333333333 in regions us-east-1 and
eu-west-1. Template at file://config-baseline.yaml (8,000
bytes). Administration role:
arn:aws:iam::111111111111:role/AWSCloudFormationStackSetAdministrationRole.
Execution role AWSCloudFormationStackSetExecutionRole is
pre-provisioned in all three target accounts. No IAM
capabilities needed. Parameters: LogLevel=INFO.
Account ID: 111111111111.
