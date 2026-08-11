# Eval prompt: budgets-ec2-stop-missing-approval-gate

Validate the existing Budgets action configuration against the
mandatory guardrails. Emit the standard validation block
(DETECTION_SOURCE, RESPONSE_SCOPE, VERDICT, WORKFLOW, GUARDRAILS,
AUDIT, FINDINGS, REMEDIATION).

Scenario: budgets-ec2-stop-missing-approval-gate

Detection source: AWS Budgets
Response scope: budget-action (RUN_SSM_DOCUMENTS STOP_EC2_INSTANCES)
Budget: monthly-ec2-budget (USD 10,000 monthly, EC2 cost filter)
Action: threshold 120% ACTUAL, ApprovalModel=AUTOMATIC,
  InstanceIds=["i-0abc12345"], Region us-east-1
Kill-switch: Parameter Store /cost/kill-switch (enabled)
IAM: role scoped to budgets:ExecuteBudgetAction
No Step Functions approval gate wired.
CUR delivery latency: 8-24h.
