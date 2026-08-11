# Eval: nested-runbook-branch-targets

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — aws:branch conditional routing, nested runbook via aws:executeAutomation, tag-based targets, rate control

## Prompt

Create an SSM Automation document "AutoRemediateByState" that:
1) Uses aws:executeAwsApi to check instance state. 2) Uses
aws:branch to route: if running → StopStep, if stopped →
StartStep, default → NoOpStep. 3) StopStep and StartStep use
aws:changeInstanceState. 4) NoOpStep uses aws:executeAutomation
to invoke child runbook "ChildHealthCheck" with the instance ID.
Targets via tag Environment=production. Rate control:
MaxConcurrency 5, MaxErrors 1. Execution role: SSMAutomationRole.
Schema version 0.3. Region us-east-1.
