# Baseline (no-skill) response: mw-register-task-ready

This file captures what a generic assistant produces WITHOUT the
ssm-patch-operator skill loaded.

---

You can register a patching task on your maintenance window with:

```bash
aws ssm register-task-with-maintenance-window \
  --window-id mw-0bbb \
  --targets "Key=tag:Patch Group,Values=prod-linux-critical" \
  --task-arn "AWS-RunPatchBaseline" \
  --task-type RUN_COMMAND \
  --service-role-arn arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole \
  --task-invocation-parameters '{"RunCommand":{"Parameters":{"Operation":["Install"],"RebootOption":["NoReboot"]}}}'
```

The task will run every Saturday at 02:00 UTC.
