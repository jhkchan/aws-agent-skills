# Eval: conditional-branch-on-metric

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ConditionStep with JsonGet-from-property-file, if_steps register model, else_steps FailStep

## Prompt

Add a ConditionStep to my SageMaker Pipeline. The prior step
"Evaluate" writes a PropertyFile evaluation_report containing
{"metrics": {"accuracy": {"value": 0.93}}}. The ConditionStep
"CheckAUC" should branch when accuracy >= ApprovalThreshold
(default 0.9). if_steps: CreateModelStep, RegisterModelStep to
group classifier-group (PendingManualApproval). else_steps:
FailStep with message "metric below threshold". Pipeline is in
us-east-1.
