# Eval prompt: stackset-multi-account

Design a multi-account patch-baseline rollout via CloudFormation
StackSets. Emit the standard PATCH block including the StackSet template
and the patch-group-association automation strategy.

Design reference: stackset-multi-account
Account: 111111111111 (management account)
Region: us-east-1

Organization OU: ou-abc-123defghi (15 member accounts)
Fleet per account: ~20-50 Amazon Linux 2023 instances each
Desired baseline: al2023-org-baseline
  - Critical/Important: ApproveAfterDays 0
  - Medium: ApproveAfterDays 7
StackSet permission model: SERVICE_MANAGED
Auto-deployment: enabled, do not retain on account removal
