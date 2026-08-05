---
description: Audit a CodeDeploy deployment group for auto-rollback enablement, CloudWatch alarm monitoring, deployment-config risk (AllAtATime, custom minimum-healthy-hosts of zero), and blue/green termination posture.
nl_triggers:
  - "audit this CodeDeploy deployment group"
  - "check CodeDeploy rollback"
  - "is auto-rollback enabled"
  - "CodeDeploy alarm configuration"
  - "AllAtATime deployment risk"
  - "deployment config too aggressive"
  - "blue/green termination too fast"
  - "CodeDeploy deployment strategy"
  - "deployment group safety audit"
  - "auto rollback configuration"
  - "ignorePollAlarmFailure"
  - "blue green termination wait"
  - "minimum healthy hosts"
  - "Lambda canary deployment"
routes_to: codedeploy-deployment-group-auditor
---

# /aws:audit-codedeploy-deployment-group

Activate the `codedeploy-deployment-group-auditor` skill and audit one or more
CodeDeploy deployment group configurations for deployment safety.

## What it does

Reads a CodeDeploy deployment group configuration (from `aws deploy
get-deployment-group`) and applies the ordered classification logic:

1. Auto-rollback evaluation — `autoRollbackConfiguration.enabled` must be
   true AND `triggers` must include `DEPLOYMENT_FAILURE`.
2. Alarm configuration — `alarmConfiguration.enabled` must be true with a
   populated `alarms` list.
3. Deployment config — `CodeDeployDefault.AllAtATime` or custom configs with
   zero minimum healthy hosts are flagged.
4. Blue/green termination — `terminationWaitTimeInMinutes: 0` and
   `WITHOUT_TRAFFIC_CONTROL` are flagged.

Emits a deterministic VERDICT per deployment group:

```text
DEPLOYMENT_GROUP: <name>
VERDICT: NO_ROLLBACK | NO_ALARMS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the failing gate and step number>
FINDINGS:
  - [NO_ROLLBACK] <finding description (Step N)>
  - [WARNING] <advisory finding>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CodeDeploy deployment group configuration and ask any of:

- "audit this CodeDeploy deployment group"
- "is auto-rollback enabled?"
- "check CodeDeploy alarm configuration"
- "is this deployment config too aggressive?"
- "blue/green termination too fast"
- "deployment strategy audit"

A bare deployment group name + any audit verb also routes here via the
orchestrator.

## Inputs

- A CodeDeploy deployment group configuration (from `aws deploy
  get-deployment-group --output json`), pasted inline or referenced by file.
- Key fields: `autoRollbackConfiguration`, `alarmConfiguration`,
  `deploymentConfigName`, `deploymentStyle`, `blueGreenConfiguration`,
  `computePlatform`.

## Outputs

- One VERDICT block per deployment group.
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: enable rollback, attach alarms, switch deployment
  config, adjust blue/green termination wait time.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CodeDeploy deployment safety).
- `/aws:audit-autoscaling-group` for ASG-level health-check and capacity
  audit (complements CodeDeploy deployment group safety).
