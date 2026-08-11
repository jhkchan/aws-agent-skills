# Baseline (no-skill) response: deploy-patch-group-maintenance-window-ready

This file captures what a generic assistant produces WITHOUT the
ssm-patch-baseline-deployer skill loaded.

---

To set up maintenance window patching, run:

```bash
aws ssm register-target-with-maintenance-window \
  --window-id mw-0abc123 \
  --resource-type INSTANCE \
  --targets '[{"Key":"tag:Patch Group","Values":["al2023-prod-web"]}]'

aws ssm register-task-with-maintenance-window \
  --window-id mw-0abc123 \
  --targets '[{"Key":"WindowTargetIds","Values":["<target-id>"]}]' \
  --task-arn AWS-RunPatchBaseline \
  --task-type RUN_COMMAND \
  --task-parameters '{"Operation":["Install"]}'
```

Patches will install during the maintenance window.
