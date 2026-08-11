# Eval: eventbridge-scheduled-sns-rate-control

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — EventBridge scheduled automation, SNS notifications, tag-based targets, rate control

## Prompt

Create an SSM Automation document "NightlyPatchCheck" that:
1) Uses aws:executeAwsApi to call ssm:DescribeInstancePatches.
2) Uses aws:sleep for 60 seconds between checks. 3) EventBridge
rule "NightlyPatchSchedule" with cron(0 2 ? * SUN *). 4) SNS
notification on Success and Failed to
arn:aws:sns:us-east-1:123456789012:patch-alerts. 5) Targets
via tag PatchGroup=weekly. Rate control: MaxConcurrency 10,
MaxErrors 3. Execution role: SSMAutomationRole. Schema 0.3.
Region us-east-1.
