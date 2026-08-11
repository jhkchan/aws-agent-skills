# Eval: zero-spend-sandbox-with-ec2-stop

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — $0.01 zero-spend budget with 50% ACTUAL (fires on first dollar), APPLY_IAM_POLICY + RUN_SSM_DOCUMENTS actions at 100%

## Prompt

Set up a zero-spend guardrail on sandbox account 111111111111.
Budget name "sandbox-zero-spend", MONTHLY, amount $0.01. Alert
at 50% ACTUAL (so we catch the first dollar) and 100% ACTUAL to
SNS arn:aws:sns:us-east-1:111111111111:security-alerts (policy
allows budgets.amazonaws.com). At 100% ACTUAL, run
APPLY_IAM_POLICY on SandboxFullAccessRole with policy
arn:aws:iam::111111111111:policy/BudgetDenyAll. Also at 100%
ACTUAL, run RUN_SSM_DOCUMENTS STOP_EC2_INSTANCES on
i-0aaa111222bbb33344 in us-east-1. ExecutionRoleArn
arn:aws:iam::111111111111:role/BudgetActionsRole (trust verified
on budgets.amazonaws.com). ApprovalModel AUTOMATIC.
