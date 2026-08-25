# Deployment strategies and rollback — deep reference

This reference expands the SKILL.md deployment strategy and rollback
sections with the strategy semantics, alarm wiring details,
CodeDeploy integration, and diagnostic runbooks. Load when defining
a deployment strategy, wiring rollback alarms, or diagnosing a
deployment that rolled back or terminated.

## Deployment strategy parameter semantics

### Parameter matrix

| Parameter | Range | Effect |
|---|---|---|
| `GrowthFactor` | 1-100 (% per step) | Step count = `ceil(100 / GrowthFactor)` |
| `GrowthType` | `LINEAR` / `EXPONENTIAL` | Linear steps in equal increments; exponential doubles each step |
| `DeploymentDurationInMinutes` | 0-1440 | Time AppConfig takes to fan out the step's percentage of targets |
| `BakeTimeInMinutes` | 0-1440 | Hold AFTER each step, before next step — the rollback window |
| `FinalBakeTimeInMinutes` | 0-1440 | Final hold after 100% before `COMPLETED` |
| `ReplicateTo` | `NONE` / `SSM_DOCUMENT` | Replicate the configuration to SSM Parameter Store (deprecated path; prefer direct integration) |
| `ReplicaMultiplier` | 1-10 | Multiply per-step duration for distributing across replica sets |

### Built-in strategies (2026)

| Name | GrowthFactor | DeploymentDuration | BakeTime | Use case |
|---|---|---|---|---|
| `AppConfig.AllAtOnce` | 100% | 0 min | 0 min | Dev / sandbox; atomic — no bake |
| `AppConfig.Linear50PercentEvery30Minutes` | 50% | 30 min | 30 min | Conservative 2-step canary |

Built-in strategies cannot be deleted and do not accept custom
alarms. For production rollouts, create a custom strategy with
`MonitorList` alarms wired.

### Step count calculation

```
step_count = ceil(100 / GrowthFactor)
wall_clock ≈ step_count * (DeploymentDurationInMinutes + BakeTimeInMinutes) + FinalBakeTimeInMinutes
```

For `GrowthFactor=20, DeploymentDurationInMinutes=30, BakeTimeInMinutes=30, FinalBakeTimeInMinutes=30`:
- step_count = 5 (20/40/60/80/100)
- wall_clock = 5 * (30 + 30) + 30 = 330 minutes (~5.5 hours)

For all-at-once (`GrowthFactor=100`): step_count = 1, wall_clock = 0
(no bake unless `FinalBakeTimeInMinutes` is set).

### Growth type comparison

| GrowthType | Step percentages (GrowthFactor=20) | When to use |
|---|---|---|
| `LINEAR` | 20 → 40 → 60 → 80 → 100 | Predictable blast radius per step |
| `EXPONENTIAL` | 20 → 40 (×2) → 80 (×2) → 100 | Aggressive start, fast scale on early success |

Exponential growth skips intermediate percentages; use only when
early steps give high confidence (long prior bake, robust alarms).

## Rollback model

### How rollback triggers

1. The deployment enters `Baking` state at each step boundary.
2. During `Baking`, AppConfig polls each `MonitorList[].AlarmArn`
   via CloudWatch.
3. If any alarm transitions to `ALARM` during the bake window,
   AppConfig enters `ROLLING_BACK`.
4. Rollback reverts targets to the configuration version of the
   last `COMPLETED` deployment on this environment.
5. If no prior `COMPLETED` exists, rollback cannot revert — the
   deployment enters `ROLLED_BACK` with targets in an undefined
   state.

### Rollback cannot cross environments

Rollback reverts the configuration version on the **same
environment**. To revert across environments (e.g., prod → staging
config), issue a new `start-deployment` referencing the staging
configuration profile / version.

### Manual rollback via `StopDeployment`

```bash
aws appconfig stop-deployment \
  --application-id <app> \
  --environment-id <env> \
  --deployment-number <n>
```

`StopDeployment` on a `DEPLOYING` deployment triggers
`ROLLING_BACK` if a prior `COMPLETED` deployment exists; otherwise
the deployment enters `ROLLED_BACK`. `StopDeployment` on a
`Baking` deployment is equivalent — the bake is interrupted and
rollback proceeds.

`StopDeployment` on a `COMPLETED` deployment is a no-op.

### Rollback without a prior COMPLETED

If this is the first deployment on an environment and it rolls
back, there is no known-good version. Targets remain at whatever
state they were in before the deployment started (often "no
configuration"). The remediation is:

1. Identify the prior known-good configuration version (likely
   from another environment or a `list-hosted-configuration-versions`
   lookup).
2. Issue a fresh `start-deployment` referencing that version.

## CloudWatch alarm wiring

### Where alarms live

`MonitorList` is set on the **deployment strategy**, not on the
individual deployment. All deployments using a strategy inherit
its alarms. To customize alarms per deployment, create a separate
strategy.

The AWS CLI `create-deployment-strategy` does not expose
`MonitorList` directly in 2026 — use the SDK, console, or
`update-deployment-strategy` via the API to set
`MonitorList[].AlarmArn` and `MonitorList[].AlarmRoleArn`.

### Alarm semantics

- AppConfig checks alarms only during `Baking` windows.
- An alarm in `ALARM` at start-deployment time blocks the deployment
  (pre-check fails).
- An alarm transitioning to `ALARM` during `Baking` triggers
  rollback.
- An alarm in `INSUFFICIENT_DATA` does NOT trigger rollback
  (treat as healthy).
- The `AlarmRoleArn` must grant AppConfig permission to describe
  the alarm (`cloudwatch:DescribeAlarms`).

### Recommended alarm patterns

| Configuration type | Alarm to wire |
|---|---|
| Timeout / latency change | Application-level p99 latency alarm (CloudWatch metric or custom) |
| Feature flag rollout | Error-rate alarm on the affected endpoint |
| Database config change | Connection-count alarm, query-latency alarm |
| Throttling config | Throttle-count alarm on the API Gateway stage |

Always pair the alarm threshold with the new configuration's
**expected** band. A configuration that legitimately raises latency
(e.g., adds a logging step) will trigger an over-tight alarm.

## CodeDeploy integration

### When to use CodeDeploy with AppConfig

- You need pre-traffic / post-traffic hooks (Lambda functions,
  shell scripts) beyond pure alarm-based rollback.
- You want a unified deployment console across compute (EC2 / ECS /
  Lambda) and configuration (AppConfig).
- You want canary / linear / all-at-once orchestrated by
  CodeDeploy's traffic router.

### Deployment config names

| CodeDeploy deployment config | Router | Equivalent AppConfig strategy |
|---|---|---|
| `AppConfig.AllAtOnce` | CodeDeploy traffic router | All-at-once |
| `AppConfig.50Percent` | CodeDeploy traffic router | 2-step canary |
| `AppConfig.Linear20PercentEvery30Minutes` | CodeDeploy traffic router | 5-step linear canary |
| `CodeDeployDefault.Lambda.Canary10Percent5Minutes` | Lambda alias shift | Not AppConfig-specific |

`AppConfig.*` deployment configs require the deployment group's
`deploymentStyle.deploymentOption = WITH_TRAFFIC_CONTROL` and a
service role with `appconfig:*` and `codedeploy:*` permissions.

### CodeDeploy lifecycle events

| Event | When | Hook use |
|---|---|---|
| `BeforeInstall` | Before the deployment starts | Validate prerequisites, freeze traffic |
| `AfterInstall` | After the configuration is deployed to the first batch | Smoke tests |
| `ApplicationStart` | After traffic shifts to the new configuration | Health check |
| `ApplicationStop` | Before traffic shifts away from the old configuration | Drain |
| `ValidateService` | After the deployment completes | End-to-end verification |

Use `BeforeInstall` to validate the configuration payload; use
`ValidateService` to confirm the new configuration is live and
healthy.

## Diagnostic runbooks

### Deployment entered ROLLING_BACK unexpectedly

1. `get-deployment --deployment-number <n>` — read `EventLog` for
   the rollback trigger.
2. The trigger names a `MonitorList` alarm. Capture the alarm name.
3. `cloudwatch describe-alarms --alarm-names <name>` — read the
   metric, threshold, and current state.
4. `cloudwatch get-metric-statistics` for the alarm metric over
   the bake window — verify whether the breach was real or
   noise.
5. Decide:
   - Real breach: fix the configuration payload, then re-deploy.
   - Noise (alarm over-sensitive): widen the threshold, then
     re-deploy.
6. Re-deploy via `start-deployment` referencing the corrected
   configuration version.

### Deployment stuck in DEPLOYING past expected wall-clock

1. `get-deployment` — capture `State`, `PercentageComplete`,
   `EventLog`.
2. If `EventLog` shows recent step transitions, the deployment is
   healthy — wait for the next step boundary.
3. If `EventLog` shows no transitions for > 2 × step duration:
   - Check IAM: did the caller lose `appconfig:GetDeployment`?
     (`get-deployment` itself failing is a symptom.)
   - Check the configuration profile: was it deleted? The
     deployment will transition to `TERMINATED`.
   - Check the deployment strategy: was it deleted? Same —
     `TERMINATED`.
4. If targets are not receiving the new version despite 100%
   completion, the runtime (Lambda extension 45s, agent 60s)
   introduces lag — wait one more poll cycle before escalating.

### Deployment TERMINATED

`TERMINATED` is terminal and non-recoverable. Causes:

| Cause | Diagnostic | Fix |
|---|---|---|
| Configuration profile deleted mid-deployment | `list-configuration-profiles` — profile missing | Re-create the profile; issue a new start-deployment |
| Configuration data failed schema validation | `EventLog` shows validation error | Fix the payload; upload a new hosted-configuration-version; re-deploy |
| IAM regression on caller | `EventLog` shows AccessDenied | Restore the IAM policy; issue a new start-deployment |
| KMS key disabled | `EventLog` shows KMSAccessDenied | Re-enable the key; re-deploy |

After fixing the cause, always issue a fresh `start-deployment` —
a terminated deployment cannot be resumed.

---

## Step-by-step CLI walkthroughs (moved verbatim from SKILL.md)

The SKILL.md body keeps only pattern stubs under progressive disclosure
(agentskills.io); the original boilerplate sections below were moved
verbatim so no content is lost.

### Create a linear deployment strategy with bake time (5-step canary)

```bash
aws appconfig create-deployment-strategy \
  --name "linear-20-percent-30min-bake" \
  --description "5-step canary: 20% every 30 min with 30-min bake" \
  --deployment-duration-in-minutes 30 \
  --growth-factor 20 \
  --growth-type LINEAR \
  --replicate-to NONE \
  --bake-time-in-minutes 30 \
  --final-bake-time-in-minutes 30
```

`GrowthFactor=20` with `GrowthType=LINEAR` produces 5 steps
(20/40/60/80/100). `BakeTimeInMinutes=30` holds each step for 30
minutes after the deployment step completes. Total wall-clock is
~5 × (30 + 30) = 300 minutes.

### Start a deployment with rollback alarms

```bash
aws appconfig start-deployment \
  --application-id $APP_ID \
  --environment-id $ENV_ID \
  --deployment-strategy-id "linear-20-percent-30min-bake" \
  --configuration-profile-id $PROFILE_ID \
  --configuration-version 7 \
  --description "Raise checkout timeout to 5000 ms (cutoff 2026-08)" \
  --tags '[{"Key":"owner","Value":"payments-platform"}]' \
  --kms-key-identifier arn:aws:kms:us-east-1:111122223333:key/abc
```

To wire rollback alarms, use the AppConfig API
(`UpdateDeploymentStrategy` does not accept alarms in the CLI);
use the SDK or the AWS console to set
`DeploymentStrategy.MonitorList[].AlarmArn` and
`TriggerPattern`. Alternatively, attach alarms via
`cloudwatch describe-alarms` polling in the deployment watcher.

### CodeDeploy-managed AppConfig deployment (canary)

```bash
# Deployment group using AppConfig.50Percent canary over 15 minutes
aws deploy create-deployment-group \
  --application-name checkout-codedeploy \
  --deployment-group-name checkout-dg-prod \
  --service-role-arn arn:aws:iam::111122223333:role/codedeploy-role \
  --deployment-config-name AppConfig.50Percent \
  --deployment-style deploymentType=BLUE_GREEN,deploymentOption=WITH_TRAFFIC_CONTROL
```

Use `AppConfig.50Percent`, `AppConfig.AllAtOnce`, or
`AppConfig.Linear20PercentEvery30Minutes` as the
`deployment-config-name` to drive CodeDeploy with the AppConfig
router. CodeDeploy orchestrates pre/post traffic hooks; AppConfig
provides the configuration store.
