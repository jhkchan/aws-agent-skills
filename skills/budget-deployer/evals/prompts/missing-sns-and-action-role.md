# Eval: missing-sns-and-action-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — ExecutionRoleArn not provided + SNS topic policy lacks budgets.amazonaws.com

## Prompt

Help me create an AWS Budget for account 111111111111 named
"dev-spend". Budget $5,000 MONTHLY. I want a budget action that
applies an IAM deny policy at 100% ACTUAL. Use SNS topic
arn:aws:sns:us-east-1:111111111111:dev-alerts (policy currently
only allows lambda.amazonaws.com to publish). Region: us-east-1.
