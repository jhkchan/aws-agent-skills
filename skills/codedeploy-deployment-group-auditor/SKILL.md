---
name: codedeploy-deployment-group-auditor
description: Audits AWS CodeDeploy deployment groups for auto-rollback enablement, CloudWatch alarm monitoring, deployment-config risk (AllAtATime, custom minimum-healthy-hosts of zero), and blue/green termination posture (immediate termination, no traffic control). Emits a deterministic verdict (NO_ROLLBACK | NO_ALARMS | CONFIG_GAP | OK) per deployment group with enumerated findings and CLI remediation. Use when reviewing CodeDeploy deployment groups, validating rollback configuration, checking alarm coverage, auditing deployment strategy, or hardening blue/green termination before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline config classification. Live-account audits use aws deploy get-deployment-group and aws deploy batch-get-deployment-groups (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  verdict_shape: NO_ROLLBACK | NO_ALARMS | CONFIG_GAP | OK
  when_to_use: 'Audit a CodeDeploy deployment group before production deployment. Trigger example: "audit this CodeDeploy deployment group", "is auto-rollback enabled on <dg>?", "check CodeDeploy alarms", "AllAtATime deployment risk", "blue/green termination too fast". Validates auto-rollback, alarm coverage, deployment-config risk, and blue/green termination posture; emits a deterministic verdict per group.'
  activation_triggers: audit this CodeDeploy deployment group, is auto-rollback enabled, check CodeDeploy alarm configuration, AllAtATime deployment risk, blue/green termination too fast, deployment config too aggressive, CodeDeploy rollback configuration, deployment strategy audit
  invocation_schema: 'Input: either (a) a CodeDeploy deployment group JSON document (from aws deploy get-deployment-group), optionally paired with deployment config metadata, OR (b) a deployment group name + application name for live-account audit. Output: deterministic DEPLOYMENT_GROUP/VERDICT/REASON/FINDINGS/REMEDIATION block per deployment group, where VERDICT is in {NO_ROLLBACK, NO_ALARMS, CONFIG_GAP, OK, ERROR}.'
  invocation_example: "# Minimal valid input shape (offline audit)\n{\n  \"deploymentGroupName\": \"my-dg\",\n  \"applicationName\": \"my-app\",\n  \"computePlatform\": \"Server\",\n  \"deploymentConfigName\": \"CodeDeployDefault.OneAtATime\",\n  \"deploymentStyle\": {\"deploymentType\": \"IN_PLACE\", \"deploymentOption\": \"WITH_TRAFFIC_CONTROL\"},\n  \"autoRollbackConfiguration\": {\"enabled\": true, \"triggers\": [\"DEPLOYMENT_FAILURE\"]},\n  \"alarmConfiguration\": {\"enabled\": true, \"ignorePollAlarmFailure\": false,\n    \"alarms\": [{\"name\": \"HighErrorRate\"}]}\n}\n# Expected output (single line per field, fixed order):\n# DEPLOYMENT_GROUP: my-dg\n# VERDICT: OK\n# REASON: All four gates passed (Steps 1-4).\n# FINDINGS:\n#   - [OK] autoRollbackConfiguration enabled with DEPLOYMENT_FAILURE (Step 1)\n#   - [OK] alarmConfiguration enabled with 1 alarm (Step 2)\n# REMEDIATION: None required."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CodeDeploy, deployment group, auto-rollback, CloudWatch alarms, alarm configuration, deployment config, AllAtATime, OneAtATime, blue/green, blue green, termination wait, MinimumHealthyHosts, deployment strategy, rollback configuration, ignorePollAlarmFailure, Lambda canary, deployment safety, EC2 in-place, ECS blue green, DEPLOYMENT_FAILURE
  tags: codedeploy, devtools, deployment, rollback, alarms, blue-green, audit
---

# CodeDeploy Deployment Group Auditor

## Quick start — 4-line decision tree

Evaluate in order; **first match wins.**

1. **No auto-rollback?** (`autoRollbackConfiguration.enabled: false` OR
   `DEPLOYMENT_FAILURE` missing from triggers) → **NO_ROLLBACK**
2. **No alarms?** (`alarmConfiguration.enabled: false` OR `alarms` empty)
   → **NO_ALARMS**
3. **Risky config?** (`AllAtATime`, zero minimum-healthy-hosts, blue/green
   0-minute termination, `WITHOUT_TRAFFIC_CONTROL`) → **CONFIG_GAP**
4. **All clear?** → **OK**

## Mindset

CodeDeploy is the safety gate between a new revision and production
traffic. The verdict reflects the **first** safety gate that fails,
evaluated in priority order — rollback before alarms before config —
because a deployment without automatic rollback is a manual recovery
exercise regardless of alarm coverage. Rationale: rollback + alarms
partially mitigate a risky config, but nothing mitigates a missing
rollback. The full thresholds, edge cases, and operator-only gotchas
are in the Reference at the end.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| `autoRollbackConfiguration` absent or `enabled: false` | **NO_ROLLBACK** | Step 1 |
| `enabled: true` but `triggers` missing `DEPLOYMENT_FAILURE` | **NO_ROLLBACK** | Step 1 |
| `alarmConfiguration` absent or `enabled: false` | **NO_ALARMS** | Step 2 |
| `enabled: true` but `alarms` list empty | **NO_ALARMS** | Step 2 |
| `deploymentConfigName: CodeDeployDefault.AllAtATime` | **CONFIG_GAP** | Step 3 |
| Custom config `minimumHealthyHosts` value 0 (HOST_COUNT) or 0% (FLEX_COUNT) | **CONFIG_GAP** | Step 3 |
| `CodeDeployDefault.LambdaAllAtOnce` | **CONFIG_GAP** | Step 3 |
| Blue/green with `terminationWaitTimeInMinutes: 0` | **CONFIG_GAP** | Step 4 |
| `deploymentStyle.deploymentOption: WITHOUT_TRAFFIC_CONTROL` (blue/green) | **CONFIG_GAP** | Step 4 |
| All dimensions pass | **OK** | Step 5 |

Evaluation is **ordered**: the first matching gate produces the verdict.
NO_ROLLBACK is evaluated before NO_ALARMS because a deployment without
rollback is dangerous regardless of alarm coverage.

## Pre-flight: deployment group metadata gate

Before classification, verify the deployment group JSON is from the correct
API response shape (`get-deployment-group` or `batch-get-deployment-groups`).
Misidentified inputs produce false positives.

| Attribute | Effect on audit |
|---|---|
| `computePlatform` | `Server` (EC2), `Lambda`, or `ECS`. Determines valid deployment configs. Lambda uses `LambdaCanary*` / `LambdaLinear*`; Server uses `OneAtATime` / `HalfAtATime` / `AllAtATime`; ECS uses blue/green with traffic control. |
| `deploymentStyle.deploymentType` | `IN_PLACE` or `BLUE_GREEN`. Blue/green provisions a replacement fleet — termination config is audited (Step 4). In-place does not. |
| `deploymentStyle.deploymentOption` | `WITH_TRAFFIC_CONTROL` or `WITHOUT_TRAFFIC_CONTROL`. Only meaningful for blue/green. `WITHOUT_TRAFFIC_CONTROL` bypasses gradual traffic shifting. |
| `autoRollbackConfiguration` | The authoritative rollback control. Has `enabled` (boolean) and `triggers` (list of `DEPLOYMENT_FAILURE`, `DEPLOYMENT_STOP_ON_ALARM`, `DEPLOYMENT_STOP_ON_REQUEST`). |
| `alarmConfiguration` | Has `enabled`, `ignorePollAlarmFailure`, and `alarms` (list of alarm-name objects). |
| `targetRevision` | The app revision tracked by the deployment group. If absent, no known-good rollback target is pinned — note as WARNING. |

Live-account pre-flight checks (IAM read/update permissions, service-role trust per compute platform, config snapshot): [Diagnostic commands](references/diagnostic-commands.md).

**If the deployment group JSON is malformed** (invalid JSON, missing
`deploymentGroupName`), output:

```text
DEPLOYMENT_GROUP: <name or "unknown">
VERDICT: ERROR
REASON: Deployment group document is not valid JSON or is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws deploy get-deployment-group --application-name <app> --deployment-group-name <dg> --output json` and re-audit.
```

## Process — Classification logic (apply in order, first match wins)

### Step 0: Expert knowledge — operator-only behaviors that change classification

All seven operator-only behaviors (partial triggers, ignorePollAlarmFailure, AllAtATime+rollback, 0-minute termination, single-instance OneAtATime, legacy rollbackEnabled, WITHOUT_TRAFFIC_CONTROL): [Advanced patterns](references/advanced-patterns.md).

### Step 1: Auto-rollback evaluation (highest priority — first gate)

Check `autoRollbackConfiguration`:

- **Absent or `enabled: false`** → **NO_ROLLBACK**. The deployment has no
  automatic recovery path. A failed deployment leaves instances in a broken
  state until an operator manually triggers rollback or redeploys.

- **`enabled: true` but `triggers` missing `DEPLOYMENT_FAILURE`** →
  **NO_ROLLBACK**. Without the `DEPLOYMENT_FAILURE` trigger, rollback only
  fires on the specified triggers (alarm breach, manual stop request).
  Application-level failures that do not trigger an alarm will not auto-rollback.

- **`enabled: true` with `DEPLOYMENT_FAILURE` in triggers** → Pass this gate.
  The ideal trigger set includes all three: `DEPLOYMENT_FAILURE`,
  `DEPLOYMENT_STOP_ON_ALARM`, `DEPLOYMENT_STOP_ON_REQUEST`. If
  `DEPLOYMENT_STOP_ON_REQUEST` is missing, note as a WARNING finding
  (operators cannot trigger automated rollback mid-deployment) but do not
  fail the gate — `DEPLOYMENT_FAILURE` is the minimum.

### Step 2: Alarm configuration evaluation (second gate)

Check `alarmConfiguration`:

- **Absent or `enabled: false`** → **NO_ALARMS**. Deployments proceed without
  CloudWatch alarm monitoring. Application-level failures (error rate spikes,
  latency regressions, custom health-check breaches) are invisible to
  CodeDeploy — only instance-level health checks remain.

- **`enabled: true` but `alarms` list is empty** → **NO_ALARMS**. Alarm
  monitoring is nominally enabled but no alarms are configured — the safety
  net has no threads.

- **`enabled: true` with populated `alarms`** → Pass this gate. Also check
  `ignorePollAlarmFailure`: if `true`, append a WARNING finding (alarm polling
  failures are silently ignored — the safety net may disappear during
  infrastructure events) but do not change the verdict.

### Step 3: Deployment config evaluation (third gate)

Check `deploymentConfigName`:

- **`CodeDeployDefault.AllAtATime`** → **CONFIG_GAP**. Deploys to every
  instance simultaneously. Even with rollback, all instances are at risk
  during the deployment window. Use `OneAtATime` or `HalfAtATime`.

- **`CodeDeployDefault.LambdaAllAtOnce`** (Lambda compute platform) →
  **CONFIG_GAP**. Shifts 100% of traffic to the new function version
  immediately with no canary observation window.

- **Custom config with `minimumHealthyHosts.type: HOST_COUNT` and
  `value: 0`** → **CONFIG_GAP**. Zero healthy hosts required — the deployment
  proceeds even if every instance is unhealthy.

- **Custom config with `minimumHealthyHosts.type: FLEX_COUNT` and
  `value: 0`** → **CONFIG_GAP**. Zero percent of hosts must remain healthy —
  functionally identical to AllAtATime.

- **`CodeDeployDefault.OneAtATime` or `CodeDeployDefault.HalfAtATime`** →
  Pass this gate. These configs maintain healthy instances throughout.

- **Lambda canary/linear configs** → Pass, but note configs with very short
  bake times (e.g., `LambdaCanary10Percent0Minutes`) provide no observation
  window — flag as WARNING if the time component is 0.

### Step 4: Blue/green termination evaluation (fourth gate — BLUE_GREEN only)

If `deploymentStyle.deploymentType` is `BLUE_GREEN`:

- **`blueGreenConfiguration.terminateBlueInstancesOnDeploymentSuccess.terminationWaitTimeInMinutes:
  0`** → **CONFIG_GAP**. Immediate termination of blue instances after green
  deployment success — no baking window to catch delayed green-fleet failures.

- **`deploymentStyle.deploymentOption: WITHOUT_TRAFFIC_CONTROL`** →
  **CONFIG_GAP**. Blue/green without gradual traffic shifting via the load
  balancer. You get fleet-provisioning complexity without the instant
  rollback safety of traffic-weight flipping.

- **`terminationWaitTimeInMinutes >= 1` and `WITH_TRAFFIC_CONTROL`** →
  Pass this gate. Recommended minimum is 5 minutes, but 1+ is acceptable for
  fast-feedback environments.

If `deploymentStyle.deploymentType` is `IN_PLACE`, skip this step entirely.

### Step 5: Aggregation

If all gates pass (Steps 1-4), the verdict is **OK**. The evaluation is
ordered — the first failing gate determines the verdict. This ordering
reflects operational priority: a missing rollback is more dangerous than a
missing alarm, which is more dangerous than a risky config (because rollback
+ alarms partially mitigate config risk).

## Output format

### Single deployment group

```text
DEPLOYMENT_GROUP: <name>
VERDICT: NO_ROLLBACK | NO_ALARMS | CONFIG_GAP | OK | ERROR
REASON: <one sentence citing the failing gate and step number>
FINDINGS:
  - [NO_ROLLBACK|NO_ALARMS|CONFIG_GAP|WARNING|OK] <description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**Field order is fixed.** Emit exactly one VERDICT line. The first
finding tag in FINDINGS MUST match the verdict (except for OK and
WARNING-only outputs). For an ERROR (unparseable input), use:
`VERDICT: ERROR` + a REASON explaining the parse failure + a
REMEDIATION pointing to the canonical `get-deployment-group` command.

### Batch input (multiple deployment groups)

When the input contains multiple deployment group documents (e.g.,
`batch-get-deployment-groups` output, a CloudFormation stack with several
`AWS::CodeDeploy::DeploymentGroup` resources, or a directory of JSON
exports), emit **one verdict block per deployment group**, separated by a
blank line. Preserve input order. Append a final summary line:

```text
SUMMARY: <N> deployment groups — <X> OK, <Y> CONFIG_GAP, <Z> NO_ALARMS, <W> NO_ROLLBACK, <E> ERROR
```

If any group fails to parse, emit its block as ERROR and continue with the
next group — do NOT abort the batch on a single malformed entry.

### Worked example — AllAtATime with rollback enabled

```text
DEPLOYMENT_GROUP: allatatime-config-gap-dg
VERDICT: CONFIG_GAP
REASON: deploymentConfigName is CodeDeployDefault.AllAtATime — every instance
is deployed simultaneously, putting the entire fleet at risk during the
deployment window (Step 3).
FINDINGS:
  - [CONFIG_GAP] deploymentConfigName is CodeDeployDefault.AllAtATime (Step 3)
  - [OK] autoRollbackConfiguration enabled with DEPLOYMENT_FAILURE trigger (Step 1)
  - [OK] alarmConfiguration enabled with 2 alarms (Step 2)
REMEDIATION:
  1. Switch to OneAtATime: aws deploy update-deployment-group
     --application-name <app> --deployment-group-name allatatime-config-gap-dg
     --deployment-config-name CodeDeployDefault.OneAtATime.
  2. If OneAtATime is too slow for large fleets, use HalfAtATime as a
     compromise — at most half the fleet is at risk simultaneously.
```

### Worked example — blue/green with 0-minute termination

Full output block: [Worked examples](references/worked-examples.md).

## Edge-case handling

Edge cases (partially malformed config, ECS blue/green defaults, Lambda without target revision, leftover blueGreenConfiguration, empty target set): [Advanced patterns](references/advanced-patterns.md).

## Anti-Patterns — NEVER

- NEVER classify a deployment group with `autoRollbackConfiguration` absent or
  `enabled: false` as anything other than **NO_ROLLBACK**. Without auto-rollback,
  a failed deployment is a manual recovery exercise — every minute of downtime
  is operator-dependent.

- NEVER treat `autoRollbackConfiguration.enabled: true` as sufficient without
  checking `triggers` includes `DEPLOYMENT_FAILURE`. If that trigger is missing,
  rollback will not fire on deployment failure — only on the listed triggers.
  This is the most common silent misconfiguration in CodeDeploy.

- NEVER classify a deployment group with `alarmConfiguration.enabled: false` as
  OK. Even with perfect rollback, alarms catch application-level failures
  (error rate, latency, health-check breach) that deployment-level health
  checks miss. Without alarms, CodeDeploy only knows about instance-level
  health — not whether the application is actually serving traffic correctly.

- NEVER treat `CodeDeployDefault.AllAtATime` as acceptable when rollback is
  enabled. AllAtATime takes down all instances simultaneously. Even with
  rollback, the failure window = detection time + rollback time, during which
  the entire fleet is offline. OneAtATime or HalfAtATime maintain healthy
  instances throughout.

- NEVER ignore `ignorePollAlarmFailure: true`. This flag silently disables
  alarm monitoring when CloudWatch is unreachable — the exact scenario where
  infrastructure events make alarm monitoring most critical. Always flag it as
  a WARNING finding regardless of the verdict.

- NEVER evaluate `rollbackEnabled` (legacy boolean) instead of
  `autoRollbackConfiguration`. The legacy field is deprecated and does not
  provide trigger-level control. A deployment with `rollbackEnabled: true` but
  `autoRollbackConfiguration.enabled: false` does NOT have proper rollback.

- NEVER classify `terminationWaitTimeInMinutes: 0` on a blue/green deployment
  as OK. Immediate blue instance termination eliminates the fallback fleet
  before delayed failures (memory leaks, connection pool exhaustion) can
  surface. The minimum safe baking window is at least 1 minute, recommended 5.

- NEVER treat `WITHOUT_TRAFFIC_CONTROL` blue/green as equivalent to
  `WITH_TRAFFIC_CONTROL`. Without traffic control, there is no gradual traffic
  shift — CodeDeploy deregisters blue instances and registers green instances
  via ELB. Rollback requires a full re-deployment, not a traffic-weight flip.

- NEVER assume OneAtATime guarantees zero-downtime on a single-instance
  deployment group. With one instance, OneAtATime deploys to that instance —
  there is no healthy instance to maintain. Check target breadth (EC2 tags,
  ASG count) when the fleet is small.

- NEVER recommend disabling auto-rollback as a remediation for false alarm
  triggers. The correct fix is to tune alarm thresholds or add suppression
  windows, not to remove the rollback safety net.

- NEVER assume blue/green termination wait time defaults to a safe value
  when `terminateBlueInstancesOnDeploymentSuccess` is absent. The API default
  is 0 minutes — immediate termination. Always verify the explicit
  `terminationWaitTimeInMinutes` value is at least 1 minute for production
  blue/green deployments.

- NEVER change deployment config name and enable rollback in the same
  `update-deployment-group` call without confirming the operator is ready for
  the behavioral change. Config changes take effect on the NEXT deployment —
  the current deployment is unaffected.

- NEVER assume a missing `terminateBlueInstancesOnDeploymentSuccess` block is
  safe. The API default is `terminationWaitTimeInMinutes: 0` — immediate
  termination. An absent block is equivalent to a 0-minute wait, NOT to a
  safe default. Always treat an absent block as CONFIG_GAP for blue/green.

- NEVER assume `DEPLOYMENT_STOP_ON_ALARM` will catch a pre-existing breach.
  CodeDeploy only reacts to OK→ALARM transitions during the in-progress
  deployment; alarms already in ALARM state at `create-deployment` time do
  NOT halt the deployment. Recommend operators confirm alarms are in OK
  state before triggering a deploy.

- NEVER assume CloudWatch alarm names in `alarmConfiguration.alarms` exist
  in the deployment group's region. CodeDeploy does not validate alarm
  existence at config time — a cross-region alarm name silently never fires.
  Confirm each alarm resolves in-region.

- NEVER pass a partial triggers list to `update-deployment-group`. The
  `--auto-rollback-configuration` flag REPLACES the triggers list (it is
  not additive). Operators frequently lose `DEPLOYMENT_STOP_ON_ALARM` by
  passing only `DEPLOYMENT_FAILURE`. Always re-pass the full intended set.

## Pre-flight safety checks (run before any remediation CLI)

Confirmation gate, config snapshot, privilege-escalation warning, and change-scheduling guidance: [Diagnostic commands](references/diagnostic-commands.md).

## Remediation guidance

### For NO_ROLLBACK

1. Enable auto-rollback with all three triggers:
   ```bash
   aws deploy update-deployment-group \
     --application-name <app> \
     --deployment-group-name <dg> \
     --auto-rollback-configuration enabled=true,triggers=DEPLOYMENT_FAILURE,DEPLOYMENT_STOP_ON_ALARM,DEPLOYMENT_STOP_ON_REQUEST
   ```
2. If only `DEPLOYMENT_FAILURE` was missing from triggers, add it to the
   existing triggers list — do not remove `DEPLOYMENT_STOP_ON_ALARM`.
3. Verify rollback works by running a test deployment with a known-bad
   revision and confirming auto-rollback triggers within the expected window.

### For NO_ALARMS

1. Identify application health metrics (error rate, latency, HTTP 5xx count,
   custom health check).
2. Create CloudWatch alarms for each metric with appropriate thresholds.
3. Attach alarms to the deployment group:
   ```bash
   aws deploy update-deployment-group \
     --application-name <app> \
     --deployment-group-name <dg> \
     --alarm-configuration enabled=true,ignorePollAlarmFailure=false,alarms=[{name=HighErrorRate}]
   ```
4. Set `ignorePollAlarmFailure` to `false` — never silently skip alarm
   monitoring during deployments.

### For CONFIG_GAP — AllAtATime or custom zero-healthy-hosts

1. Switch to OneAtATime (safest) or HalfAtATime (compromise for large fleets):
   ```bash
   aws deploy update-deployment-group \
     --application-name <app> \
     --deployment-group-name <dg> \
     --deployment-config-name CodeDeployDefault.OneAtATime
   ```
2. For custom minimum-healthy-hosts of 0, create a safe deployment config:
   ```bash
   aws deploy create-deployment-config \
     --deployment-config-name SafeMinimumHealthy \
     --minimum-healthy-hosts type=HOST_COUNT,value=1
   ```
3. Then update the deployment group to use the new config name.

### For CONFIG_GAP — blue/green termination

1. Set termination wait time to at least 5 minutes:
   ```bash
   aws deploy update-deployment-group \
     --application-name <app> \
     --deployment-group-name <dg> \
     --blue-green-deployment-configuration \
       terminateBlueInstancesOnDeploymentSuccess={action=TERMINATE,terminationWaitTimeInMinutes=5}
   ```
2. If `deploymentOption` is `WITHOUT_TRAFFIC_CONTROL`, switch to
   `WITH_TRAFFIC_CONTROL` — this requires a load balancer configured on the
   deployment group.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying that CloudWatch alarms used in `alarmConfiguration`
   have appropriate thresholds and are not in `INSUFFICIENT_DATA` state during
   deployments.
3. Recommend including `DEPLOYMENT_STOP_ON_REQUEST` in triggers if not present
   — it enables operator-initiated automated rollback mid-deployment.
4. For blue/green, verify the baking window (`terminationWaitTimeInMinutes`)
   is sufficient for the application's failure-detection latency.

## Reference — deployment internals & non-obvious behaviors

Deployment lifecycle and rollback mechanics, senior-engineer gotchas (alarm-transition blind spots, rollback-of-rollback, config caps, tag-filter AND/OR semantics, bundle-type validation), compute-platform specifics, and API quirks: [Advanced patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent features — ECS blue/green, zonal deployment configs, rollback enhancements: [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — operator-only behaviors, edge-case catalog, deployment internals and gotchas, recent features
- [Worked examples](references/worked-examples.md) — blue/green 0-minute-termination CONFIG_GAP example
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight checks and remediation safety gate

## Domain

AWS CloudOps / CodeDeploy Deployment Safety & Compliance.

## AWS documentation

- **AWS CodeDeploy User Guide** — https://docs.aws.amazon.com/codedeploy/latest/userguide/welcome.html
- **CodeDeploy Security** — https://docs.aws.amazon.com/codedeploy/latest/userguide/security.html
- **CodeDeploy API Reference** — https://docs.aws.amazon.com/codedeploy/latest/APIReference/
- **AWS CLI — codedeploy (deploy) commands** — https://docs.aws.amazon.com/cli/latest/reference/deploy/
