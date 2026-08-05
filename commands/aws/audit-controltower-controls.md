---
description: Audit AWS Control Tower landing-zone state, enabled controls, guardrail enforcement integrity, and account-factory baseline health — drift, disabled mandatory controls, SCP/Config gaps.
nl_triggers:
  - "audit control tower"
  - "check landing zone drift"
  - "control tower guardrails"
  - "enabled controls status"
  - "control drift detection"
  - "account factory baseline"
  - "mandatory controls disabled"
  - "SCP drift control tower"
  - "config recorder gap"
  - "AWSControlTowerExecutionRole missing"
  - "landing zone upgrade check"
  - "preventive control drift"
  - "detective control not evaluating"
  - "control tower compliance"
routes_to: controltower-control-auditor
---

# /aws:audit-controltower-controls

Activate the `controltower-control-auditor` skill and audit one or more
Control Tower landing-zone or OU configurations for governance exposure.

## What it does

Reads a Control Tower audit snapshot (landing-zone state, enabled-controls
list, SCP verification, Config recorder status, execution-role health,
account-factory baselines) and applies the ordered classification logic:

1. Pre-flight landing zone metadata gate — short-circuit FAILED landing
   zones and organization feature gaps.
2. Landing zone drift — StackSets modified outside Control Tower → DRIFT.
3. Control-level drift — SCP content modified, Config Rule deleted, hook
   removed → DRIFT.
4. Mandatory control enforcement — FAILED status or missing from enabled
   list → DISABLED_CONTROL.
5. Config service health — recorder disabled or aggregation broken →
   CONFIG_GAP.
6. Execution role health — AWSControlTowerExecutionRole missing or trust
   policy broken → CONFIG_GAP.
7. Account Factory baseline — StackSet instances missing → CONFIG_GAP.
8. Aggregation — worst finding wins (DRIFT > DISABLED_CONTROL >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per landing zone or OU:

```text
LANDING_ZONE: <name>
OU: <ou-arn>
VERDICT: DRIFT | DISABLED_CONTROL | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [DRIFT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Control Tower audit snapshot and ask any of:

- "audit my Control Tower landing zone"
- "check for control drift"
- "are my guardrails enforcing correctly"
- "is the landing zone drifted"
- "are mandatory controls enabled"
- "Config recorder gap in Control Tower"
- "AWSControlTowerExecutionRole missing"

A landing zone name or OU ARN + any audit verb ("audit control tower",
"check guardrails") also routes here via the orchestrator.

## Inputs

- A Control Tower audit snapshot including: landing zone state + version,
  enabled-controls list with statuses, SCP verification results, Config
  recorder status per account, execution-role presence, and account-factory
  baseline StackSet status.
- For live-account audits: provide a landing-zone identifier or OU ARN and
  the skill will emit the CLI commands to collect the data.

## Outputs

- One VERDICT block per landing zone or OU (multiple findings aggregate to
  the worst severity).
- Enumerated FINDINGS list with per-finding verdict and step citation.
- Specific remediation: disable/re-enable controls for drift, enable
  Config recorder, recreate execution role, update landing zone.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Control Tower governance).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  compliance findings that may overlap with detective control output.
