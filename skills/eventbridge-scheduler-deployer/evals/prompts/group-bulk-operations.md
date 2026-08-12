# Eval: group-bulk-operations

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — group creation, two schedules with MAXIMUM flexible time window (cost optimization), bulk enable/disable capability noted

## Prompt

Create an EventBridge Scheduler schedule group called
maintenance-jobs in us-east-1, account 123456789012. Add two
schedules to the group: daily-cleanup (rate(1 day)) targeting
Lambda cleanup-function and weekly-audit (cron(0 0 ? * SUN *))
targeting Lambda audit-function. Flexible time window MAXIMUM
for both (cost optimization). Tags: Environment=production.
