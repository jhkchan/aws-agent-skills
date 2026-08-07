# Eval prompt: mw-register-task-ready

Plan the following maintenance window task registration and emit the
standard VERDICT block.

Operation: register-mw-task
Window: mw-0bbb

```json
{
  "Window": {
    "WindowId": "mw-0bbb",
    "Name": "prod-patch-window",
    "Schedule": "cron(0 2 ? * SAT *)",
    "ScheduleTimezone": "UTC",
    "Duration": 4,
    "Cutoff": 1,
    "Enabled": true
  },
  "Targets": {
    "Key": "tag:Patch Group",
    "Values": ["prod-linux-critical"],
    "MatchingInstanceCount": 14,
    "VerifiedVia": "describe-maintenance-window-targets"
  },
  "Task": {
    "TaskArn": "AWS-RunPatchBaseline",
    "TaskType": "RUN_COMMAND",
    "Parameters": {
      "Operation": "Install",
      "RebootOption": "NoReboot",
      "SnapshotIds": ""
    }
  },
  "ServiceRole": {
    "RoleArn": "arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole",
    "TrustsSSM": true,
    "AttachedPolicies": ["AmazonSSMAutomationRole"]
  },
  "RateControl": {
    "MaxConcurrency": "10%",
    "MaxErrors": 0
  }
}
```

Emit the standard VERDICT block including the exact
register-task-with-maintenance-window command with rate-control.
