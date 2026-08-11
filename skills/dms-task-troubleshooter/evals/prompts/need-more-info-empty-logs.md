# Eval prompt: need-more-info-empty-logs

Diagnose the following DMS task failure report and emit the standard
VERDICT block.

Task: arn:aws:dms:us-east-1:111111111111:task:TASK007
The task is failing but I don't know why. Can you help?

```json
{
  "TaskStatus": "failed",
  "TaskLogs": "empty (Logging=ESSENTIAL)",
  "SourceEngine": "not provided",
  "TargetEngine": "not provided",
  "ErrorMessage": "not provided",
  "CloudWatchMetrics": "not provided"
}
```
