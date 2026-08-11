# Eval: standard-migration-waitfortasktoken

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — .waitForTaskToken + 6-min runtime both incompatible with Express

## Prompt

Migrate this Standard state machine to EXPRESS for cost
savings. The state machine "approval-flow" (account
123456789012, region us-east-1) uses an SQS
sendMessage.waitForTaskToken integration at line 18 to wait
for an external approval callback. The workflow also has a
4-minute Glue .sync job plus a 2-minute downstream ECS task.
Total workflow runtime is up to 6 minutes when the callback
is slow. Set up CloudWatch Logs at ERROR level.
