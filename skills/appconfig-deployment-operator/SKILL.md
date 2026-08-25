---
name: appconfig-deployment-operator
description: Operates AWS AppConfig deployment lifecycles safely — creates applications, environments, and configuration profiles (freeform and feature-flag); defines deployment strategies (linear or all-at-once, growth factor, deployment duration, bake time); starts, monitors, and completes deployments; rolls back on CloudWatch alarm; and integrates AppConfig Lambda extensions for runtime feature flags and dynamic configuration. Runs deterministic pre-checks (application / environment existence, profile schema validity, strategy sanity, alarm health, IAM), emits the exact start-deployment / stop-deployment / rollback CLI behind a CONFIRM gate, and verifies state transitions. Emits READY | BLOCKED | COMPLETED. Use when launching a staged AppConfig deployment, wiring rollback alarms, switching strategies, adopting AppConfig Lambda extensions for live feature flags, integrating AppConfig with CodeDeploy, or diagnosing a deployment stuck in DEPLOYING / ROLLING_BACK / TERMINATED.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws appconfig create-application, create-environment, create-configuration-profile, create-deployment-strategy, start-deployment, get-deployment, stop-deployment, list-deployments, get-configuration, aws codedeploy stop-deployment, and aws cloudwatch describe-alarms (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Launching or operating an AppConfig deployment (start, monitor, stop, rollback), defining a deployment strategy (linear, all-at-once, growth factor, deployment duration, bake time), wiring CloudWatch alarms for automatic rollback, integrating AppConfig Lambda extensions for runtime feature flags / dynamic configuration, integrating AppConfig with CodeDeploy for orchestrated deployments, creating configuration profiles (freeform JSON, feature-flag schema), creating applications and environments, diagnosing a deployment stuck in DEPLOYING, ROLLING_BACK, or TERMINATED, or choosing between AppConfig.AllAtOnce / Linear / AppConfig deployments via CodeDeploy.
  when_not_to_use: General secrets management (use Parameter Store or Secrets Manager), SSM document execution (use ssm-documents-operator), CloudFormation stack updates (use cloudformation-stack operators), or service mesh traffic shifting (use appmesh-deployer).
  activation_triggers: AppConfig deployment, start-deployment, stop-deployment, rollback AppConfig, deployment strategy, growth factor, bake time, linear deployment, all-at-once, feature flag, AppConfig Lambda extension, AppConfig agent, configuration profile, AppConfig CodeDeploy, deployment stuck DEPLOYING, ROLLING_BACK, AppConfig TERMINATED, dynamic configuration
  invocation_schema: 'Input: either (a) an AppConfig deployment intent (start, stop, rollback, define-strategy, create-profile, create-environment, create-application) with target application / environment / profile / strategy identifiers, OR (b) a deployment-id + operation for live-account execution. Output: a deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AppConfig, feature flags, dynamic configuration, deployment strategy, linear deployment, all-at-once, growth factor, bake time, rollback, CloudWatch alarm, Lambda extension, CodeDeploy, configuration profile, environment, staged rollout, canary, AppConfig agent, StartDeployment, configuration data
  tags: appconfig, configuration, feature-flags, operate, staged-rollout, rollback, codedeploy
---

# AppConfig Deployment Operator

## What this skill does

Executes AWS AppConfig deployment operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI, emits
the exact `start-deployment` / `stop-deployment` / rollback sequence
behind a CONFIRM gate, and verifies state transitions after apply.
Every deployment surfaces growth factor, bake time, and rollback
alarm wiring.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + strategy semantics | Before any operation |
| **§ Mindset** | Pre-checks, percentage-of-target semantics, alarm rollback | Understanding the safety model |
| **§ Pre-flight** | Application / environment / profile metadata gate | Before executing any CLI |
| **§ Process** | Per-operation planning: create resources, define strategy, start, rollback, CodeDeploy | When choosing which operation |
| **§ Common patterns** | Feature flag, freeform, Lambda extension, CodeDeploy boilerplate | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (missing application / environment / configuration profile, schema validation failure, alarm in ALARM state, IAM permission missing, configuration data oversized) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Deployment applied and post-verification passed (`State: COMPLETED`, percentage reached 100%, alarms healthy, hosts received the new configuration) | Emit `get-deployment` summary |

**Priority order for pre-checks (all must pass for READY):**

1. **Application / environment / configuration profile existence** — ARNs resolve, environment is `READY_FOR_DEPLOYMENT`, profile version is not in a terminal-failed state.
2. **Configuration data validity** — size <= 64 KB (hosted configuration), schema (Validators) passes for JSON / feature-flag profiles.
3. **Deployment strategy sanity** — `GrowthFactor * DeploymentDurationInMinutes * ReplicaMultiplier >= BakeTimeInMinutes`. All-at-once (`GrowthFactor=100`) skips bake steps.
4. **CloudWatch alarm health** — every alarm in `MonitorList` is `OK`; any `ALARM` blocks the deployment.
5. **IAM permissions** — caller holds `appconfig:StartDeployment`, `appconfig:GetDeployment`, `appconfig:StopDeployment`, `cloudwatch:DescribeAlarms`.
6. **KMS key (if encryption configured)** — caller has `kms:Decrypt` and `kms:GenerateDataKey` on the configured key.
7. **No in-progress deployment** — `list-deployments --environment-id <id>` returns no `DEPLOYING` deployment on the target environment.

**Deployment strategy semantics (2026):**

| Strategy | GrowthFactor | DeploymentDuration | BakeTime | When to use |
|---|---|---|---|---|
| `AppConfig.AllAtOnce` (built-in) | 100% | 0 min | 0 min | Dev / sandbox; no bake |
| `AppConfig.Linear50PercentEvery30Minutes` (built-in) | 50% | 30 min | 30 min | Conservative 2-step canary |
| Linear custom | 20% | 30 min | 30 min | 5-step canary (20/40/60/80/100) |
| Exponential custom | 20% | 30 min | 30 min | Aggressive; faster at low risk |
| CodeDeploy-appended | 25% | 60 min | 60 min | When using AppConfig.50Percent / Canary entries in CodeDeploy |

`ReplicaMultiplier` (default 1) multiplies the per-step duration; use
when distributing across replica sets.

## Mindset

Three AppConfig realities drive every deployment operation:

- **Percentage-of-target is per-evaluation, not per-host.** AppConfig
  rolls out to a percentage of targets at each step boundary
  (`GrowthFactor` / `ReplicaMultiplier`). With Lambda extension or
  agent, the percentage is enforced by the service across `GetConfiguration`
  callers — a host that calls between steps sees the version
  consistent with the current step. Do not assume one-shot
  fan-out; the runtime must re-call `GetConfiguration`.

- **Rollback is alarm-driven, not metric-driven.** AppConfig rolls back
  only when a CloudWatch alarm in `MonitorList` transitions to `ALARM`
  during the deployment window. A metric rising but not breaching
  an alarm threshold does NOT trigger rollback. Always pair the
  deployment with alarms calibrated to the new configuration's
  expected error / latency band.

- **`TERMINATED` is the silent failure mode.** A deployment can
  `TERMINATE` if the configuration data fails validation, the
  referenced profile is deleted mid-deployment, or the caller
  lacks `appconfig:GetConfiguration` on the resource policy. A
  `TERMINATED` deployment cannot be rolled back — it leaves
  targets in their last-known-good state but no longer receives
  updates. Always re-issue a new `start-deployment` after fixing
  the cause.

## Pre-flight: application / environment metadata gate

Run before classification. `list-applications` returns max 50/page
(`--max-results 50`, paginate with `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `appconfig list-applications` — confirm application exists; capture `Id`.
2. `appconfig list-environments --application-id <app>` — confirm target environment; capture `Id` and `State`.
3. `appconfig list-configuration-profiles --application-id <app>` — confirm profile; capture `Id`, `Type`, `Validators`.
4. `appconfig get-hosted-configuration-version --application-id <app> --configuration-profile-id <profile> --version-number <v>` — read the configuration payload and validate against schema.
5. `appconfig list-deployment-strategies` — confirm strategy; capture `Id`, `GrowthFactor`, `DeploymentDurationInMinutes`, `BakeTimeInMinutes`, `ReplicaMultiplier`.
6. `appconfig list-deployments --application-id <app> --environment-id <env>` — check for an active `DEPLOYING` deployment.
7. `cloudwatch describe-alarms --alarm-names <names>` — verify every `MonitorList` alarm is `OK`.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `Environment.State: READY_FOR_DEPLOYMENT` | Required; any other state blocks start-deployment |
| `ConfigurationProfile.Type: AWS.AppConfig.FeatureFlags` | Requires a feature-flag schema Validators; JSON payload must match |
| `MonitorList[].AlarmArn` in `ALARM` | Deployment auto-rolls back; refuse to start |
| `Deployment.State: DEPLOYING` | Cannot start another; either wait or stop first |
| `HostedConfigurationVersion` size > 64 KB | Rejected by the service; split or move to S3-backed |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AppConfig behaviors

- **`GetConfiguration` is the single source of truth at runtime.**
  Targets call `GetConfiguration` (or the Lambda extension / agent
  on their behalf); the response includes the `Configuration` payload
  and a `ClientConfigurationVersion` token. Cached tokens are served
  from a fast tier but a token older than the polling interval can
  return the prior version. Always respect the `NextPollConfiguration`
  hint.

- **Bake time begins AFTER the step finishes deploying, not after the step starts.**
  `BakeTimeInMinutes` waits at each step for the alarm window to
  stabilize before proceeding. A 30-minute deployment with 30-minute
  bake takes ~60 minutes wall-clock. Skipping bake (`BakeTime=0`) is
  the #1 silent failure mode for production rollouts.

- **All-at-once is not "atomic".** `GrowthFactor=100` deploys to 100%
  of targets immediately, but the targets receive the new version
  on their next `GetConfiguration` poll. The polling interval (45
  seconds minimum for Lambda extension) introduces a fan-out tail.
  Do not assume atomic rollout for all-at-once.

- **Rollback reverts to the previous deployed version, not the prior start-deployment.**
  AppConfig tracks the "known-good" version as the last deployment
  that reached `State: COMPLETED`. A `ROLLING_BACK` deployment
  reverts to that version. If no prior `COMPLETED` exists, rollback
  has nothing to revert to — the deployment enters `ROLLED_BACK`
  with targets in an undefined state.

- **Lambda extension requires the `AWS_APPCONFIG_EXTENSION` env vars and the extension layer ARN.**
  The extension caches configurations and polls on a 45-second
  minimum interval. The function reads via `localhost:2772` (the
  extension's HTTP server) instead of the AppConfig API. Without
  the env vars, the extension does not preload the configuration.

- **AppConfig with CodeDeploy uses `AppConfig.50Percent`, `AppConfig.AllAtOnce`, etc. as `TrafficRouter` configs.**
  CodeDeploy orchestrates the lifecycle; AppConfig provides the
  configuration store. The CodeDeploy deployment group `deploymentStyle`
  is `ALL_AT_ONCE`, `CANARY`, `LINEAR`, or a pre-defined AppConfig
  variant. Use CodeDeploy when you need pre-traffic / post-traffic
  hooks beyond pure alarm-based rollback.

- **Feature-flag schema is restrictive.** `AWS.AppConfig.FeatureFlags`
  profiles require the payload to follow the feature-flag schema
  (`flags: { <name>: { "name": ..., "enabled": true|false, ... } }`).
  A freeform JSON payload in a feature-flag profile fails validation
  with a confusing error.

- **Hosted configuration size limit is 64 KB.** Larger configurations
  must be uploaded to S3 and referenced via a S3-source configuration
  profile. The Lambda extension can serve S3-backed configurations
  transparently.

- **`KmsKeyIdentifier` encrypts the hosted configuration at rest.**
  Without a KMS key, configurations are encrypted with an AWS-owned
  key. The Lambda extension's role must have `kms:Decrypt` on the
  configured key; otherwise the extension silently returns the
  prior (cached) version.

- **A terminated deployment leaves targets at their last-known-good version.**
  `State: TERMINATED` indicates a non-recoverable failure (deleted
  profile, IAM regression). A new `start-deployment` is required
  after the cause is fixed. Do not attempt to "resume" a terminated
  deployment.

- **`StopDeployment` triggers rollback if the deployment has already passed the rollback point.**
  Stopping during step 1 of a 5-step canary rolls back cleanly.
  Stopping after the final bake time completes with a rollback
  alarm transitions the deployment to `ROLLED_BACK` rather than
  halting.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures
in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Application ID and Environment ID resolve to existing resources.
2. Environment `State: READY_FOR_DEPLOYMENT`.
3. Caller holds `appconfig:StartDeployment` / `GetDeployment` /
   `StopDeployment` / `GetConfiguration` on the resource policy.
4. KMS key (if configured) decryptable by the caller.

**For start-deployment:**
5. Configuration profile exists; latest hosted version passes
   Validators (schema).
6. Hosted configuration size <= 64 KB (or S3-backed profile).
7. Deployment strategy: `GrowthFactor * ReplicaMultiplier` in
   `[1, 100]`; `DeploymentDurationInMinutes >= 0`;
   `BakeTimeInMinutes >= 0`.
8. Every `MonitorList[].AlarmArn` resolves and is in `OK` state.
9. No active `DEPLOYING` deployment on the target environment.

**For define-strategy:**
5. `GrowthFactor` 1-100; `DeploymentDurationInMinutes` 0-1440;
   `BakeTimeInMinutes` 0-1440; `ReplicaMultiplier` 1-10 (defaults 1).
6. `DeploymentStrategyName` unique in account-region.
7. For all-at-once (`GrowthFactor=100`), warn that bake steps are
   skipped.

**For rollback (stop-deployment):**
5. Deployment `State: DEPLOYING` (rollback applies) or
   `State: ROLLING_BACK` (idempotent no-op).
6. A previous `COMPLETED` deployment exists as the rollback target
   (otherwise emit BLOCKED — no known-good to revert to).
7. CloudWatch alarms updated to reflect the rollback target.

**For create-profile:**
5. `Type` is one of `AWS.Freeform`, `AWS.AppConfig.FeatureFlags`.
6. Feature-flag type has a Validators entry pointing at a JSON schema.
7. Freeform type accepts any valid JSON <= 64 KB.

**For create-environment:**
5. Application exists.
6. Environment name unique within the application.

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected deployment duration: `ceil(100 / GrowthFactor) *
  (DeploymentDurationInMinutes + BakeTimeInMinutes) *
  ReplicaMultiplier` minutes.
- Expected side-effects (alarm transitions, fan-out to targets).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`start-deployment`, `stop-deployment`, `create-deployment-strategy`,
  `create-configuration-profile`, `delete-configuration-profile`),
  emit CONFIRM prompt. Do NOT execute until confirmed.
- Snapshot current state: `list-deployments --application-id <app>
  --environment-id <env> --output json > /tmp/<env>-backup-$(date +%s).json`.
- Execute the CLI.
- For multi-step deployments, poll `get-deployment` at each step
  boundary; the `State` transitions through `DEPLOYING` → `Baking`
  (if applicable) → `COMPLETED` or `ROLLING_BACK`.

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. `get-deployment` returns `State: COMPLETED` and
   `PercentageComplete: 100.00`.
2. CloudWatch alarms in `MonitorList` all `OK` at the end of bake.
3. At least one target host (Lambda extension poll, agent poll, or
   `GetConfiguration` direct) reports the new
   `ClientConfigurationVersion`.
4. `EventLog` (returned by `get-deployment`) shows no rollback events.
5. For Lambda extension integrations: a sample invocation confirms
   the new configuration is loaded (check function logs for the
   AppConfig extension's `Configuration loaded` message).
6. For CodeDeploy integrations: `codedeploy get-deployment` shows
   `status: Succeeded`.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common deployment patterns (boilerplate)

### Create application + environment + freeform profile (one-time setup)

```bash
aws appconfig create-application \
  --name "checkout-service" \
  --description "Checkout microservice configuration"

# Capture ApplicationId from the response.
APP_ID=$(aws appconfig list-applications --query 'Items[?Name==`checkout-service`].Id' --output text)

aws appconfig create-environment \
  --application-id $APP_ID \
  --name "prod" \
  --description "Production environment"

ENV_ID=$(aws appconfig list-environments --application-id $APP_ID --query 'Items[?Name==`prod`].Id' --output text)

aws appconfig create-configuration-profile \
  --application-id $APP_ID \
  --name "checkout-config" \
  --location-uri "hosted" \
  --type "AWS.Freeform" \
  --description "Freeform JSON configuration"

PROFILE_ID=$(aws appconfig list-configuration-profiles --application-id $APP_ID --query 'Items[?Name==`checkout-config`].Id' --output text)

# Upload the hosted configuration (<= 64 KB):
aws appconfig create-hosted-configuration-version \
  --application-id $APP_ID \
  --configuration-profile-id $PROFILE_ID \
  --content-type "application/json" \
  --content file://config.json
```

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

### Lambda extension (runtime feature flags without redeploy)

Add the AppConfig extension layer to the Lambda function, then set
environment variables:

```bash
aws lambda update-function-configuration \
  --function-name checkout-handler \
  --layers arn:aws:lambda:us-east-1:027253079308:layer:AWS-AppConfig-Extension:131 \
  --environment '{
    "Variables": {
      "AWS_APPCONFIG_EXTENSION_APPLICATION_NAME": "checkout-service",
      "AWS_APPCONFIG_EXTENSION_ENVIRONMENT": "prod",
      "AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE": "checkout-config",
      "AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS": "45"
    }
  }'
```

The function reads the configuration via HTTP GET to
`http://localhost:2772/applications/checkout-service/environments/prod/configurations/checkout-config`
— no AWS SDK call needed. The extension polls AppConfig every 45
seconds and caches; updates land within the polling interval without
a function redeploy.

## Diagnostic flows

### Deployment stuck in `DEPLOYING`

1. `get-deployment` — capture `State`, `PercentageComplete`, `EventLog`.
2. If `PercentageComplete` is below 100 and `EventLog` shows recent
   step transitions, the deployment is healthy — wait for the next
   step boundary (`DeploymentDurationInMinutes + BakeTimeInMinutes`).
3. If `EventLog` shows no transitions for > 2 × step duration:
   - The deployment strategy `GrowthFactor` may be 0 (invalid) —
     new start-deployment with a valid strategy.
   - The configuration profile may have been deleted mid-deployment
     — `State` will transition to `TERMINATED`. Fix the profile and
     re-deploy.
4. If targets are not receiving the new version despite 100%
   completion, the runtime poll interval (Lambda extension 45s,
   agent 60s) introduces lag — wait one poll cycle.

### Deployment auto-rolled back (`ROLLING_BACK` / `ROLLED_BACK`)

1. `get-deployment` — read `EventLog` for the rollback trigger.
2. The trigger is always a `MonitorList` alarm transitioning to
   `ALARM` during a bake window. Identify the alarm.
3. `cloudwatch describe-alarms` — capture the alarm's metric,
   threshold, and current value.
4. Decide: fix the configuration and re-deploy, or widen the alarm
   threshold (only if the alarm was over-sensitive).
5. If `ROLLED_BACK` with no prior `COMPLETED` deployment, targets
   are at an unknown state — issue a new start-deployment with the
   known-good configuration version.

### Deployment `TERMINATED`

1. `get-deployment` — read `EventLog` for the termination reason.
2. Common causes:
   - Configuration profile deleted mid-deployment.
   - Configuration data validation failure (schema Validators
     rejected the payload).
   - IAM regression: caller lost `appconfig:GetConfiguration`.
3. Remediation: fix the cause (re-create profile, fix payload, fix
   IAM), then issue a fresh `start-deployment`. A terminated
   deployment cannot be resumed.

## Output format (per operation)

```text
OPERATION: <create-application | create-environment | create-profile | define-strategy | start-deployment | stop-deployment | rollback | describe>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <application-id / environment-id / deployment-number, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <DEPLOYING | BAKING | COMPLETED | ROLLING_BACK | ROLLED_BACK | TERMINATED after apply>
PERCENTAGE_COMPLETE: <0.00 - 100.00>
NOTES: <strategy rationale, detection lag, alarm wiring caveats>
```

### Worked example — start linear deployment (READY)

```text
OPERATION: start-deployment
VERDICT: READY
TARGET: checkout-service / prod / deployment #14, us-east-1
PRE_CHECKS:
  - [PASS] Application checkout-service (id: abc123) exists
  - [PASS] Environment prod (id: env-456) State READY_FOR_DEPLOYMENT
  - [PASS] Configuration profile checkout-config (id: prof-789) type AWS.Freeform
  - [PASS] Hosted configuration version 7 size 3.2 KB < 64 KB; Validators pass
  - [PASS] Deployment strategy linear-20-percent-30min-bake: GrowthFactor 20, DeploymentDurationInMinutes 30, BakeTimeInMinutes 30 — 5-step canary, ~300 min wall-clock
  - [PASS] MonitorList alarm arn:aws:cloudwatch:us-east-1:111122223333:alarm:checkout-5xx currently OK
  - [PASS] Caller holds appconfig:StartDeployment, appconfig:GetDeployment
  - [PASS] list-deployments: no active DEPLOYING deployment on env-456
STEPS:
  1. CONFIRM: About to start-deployment #14 on checkout-service / prod in account 111122223333 region us-east-1. Linear 20% canary (5 steps, 30 min deploy + 30 min bake each, ~300 min total). Rollback alarm: checkout-5xx. Proceed? (yes/no)
  2. aws appconfig start-deployment --application-id abc123 --environment-id env-456 --deployment-strategy-id linear-20-percent-30min-bake --configuration-profile-id prof-789 --configuration-version 7 --description "Raise checkout timeout to 5000 ms (cutoff 2026-08)" --kms-key-identifier arn:aws:kms:us-east-1:111122223333:key/abc
  3. aws appconfig get-deployment --application-id abc123 --environment-id env-456 --deployment-number 14 (poll at each step boundary)
POST_VERIFY:
  - (pending execution) expect State COMPLETED, PercentageComplete 100.00
  - (pending execution) MonitorList alarm checkout-5xx remains OK through final bake
  - (pending execution) Lambda extension poll on checkout-handler reports ClientConfigurationVersion 7 within 45s of step completion
STATE: pending — will be DEPLOYING for ~300 min
PERCENTAGE_COMPLETE: 0.00
NOTES:
  - Strategy: 5-step linear canary (20/40/60/80/100). Each step deploys for 30 min, then bakes for 30 min before the next step. Total ~300 min.
  - Detection lag: Lambda extension polls every 45s — targets converge within 45s of each step boundary.
  - Rollback: triggered if checkout-5xx transitions to ALARM during any bake window. Rollback reverts to the prior COMPLETED deployment's configuration version.
```

### Worked example — rollback blocked (BLOCKED)

```text
OPERATION: rollback
VERDICT: BLOCKED
TARGET: checkout-service / prod / deployment #14, us-east-1
PRE_CHECKS:
  - [PASS] get-deployment returns deployment #14
  - [FAIL] Deployment State is COMPLETED, not DEPLOYING. StopDeployment / rollback applies only to an active DEPLOYING deployment.
  - [FAIL] No prior COMPLETED deployment exists for environment env-456 (this was the first deployment). Rollback has no known-good version to revert to.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: COMPLETED (cannot roll back)
PERCENTAGE_COMPLETE: 100.00
NOTES:
  - To revert, issue a new start-deployment referencing the previous configuration version. Capture the prior version via:
    aws appconfig list-hosted-configuration-versions --application-id abc123 --configuration-profile-id prof-789
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <create-application | create-environment | create-profile | define-strategy | start-deployment | stop-deployment | rollback | describe>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <application-id / environment-id / deployment-number, region>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on <application/environment/deployment> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <DEPLOYING | BAKING | COMPLETED | ROLLING_BACK | ROLLED_BACK | TERMINATED | pending>
PERCENTAGE_COMPLETE: <0.00 - 100.00 | pending>
NOTES: <strategy rationale — must state GrowthFactor / DeploymentDuration / BakeTime; detection lag; alarm wiring caveats>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or `[FAIL]` and a specific reason for each failure.
- NEVER emit `BakeTimeInMinutes: 0` for a production canary without flagging the silent-failure risk in NOTES.
- NEVER list a CLI command with placeholder flags in a READY plan — every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`, and never omit the CONFIRM gate as the first STEPS entry for state-changing operations.

## Anti-Patterns — NEVER do these things

- NEVER use `AppConfig.AllAtOnce` for a production configuration change without a CloudWatch alarm in `MonitorList`. All-at-once deploys to 100% of targets immediately; without an alarm, a bad configuration silently propagates.
- NEVER skip bake time (`BakeTimeInMinutes: 0`) on a multi-step canary. The bake window is the only window during which rollback alarms can fire between steps. Without bake, a failing configuration reaches 100% before alarms catch it.
- NEVER assume a `TERMINATED` deployment can be resumed. Terminated is terminal — issue a new `start-deployment` after fixing the root cause.
- NEVER deploy a feature-flag payload as `AWS.Freeform` or vice versa. The Validators schema is type-specific; a mismatch produces a confusing validation error at start-deployment time.
- NEVER use the Lambda extension without the `AWS_APPCONFIG_EXTENSION_*` environment variables. The extension preloads only when these variables are set; without them, `localhost:2772` returns 404.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before modification:** `list-deployments --application-id <app> --environment-id <env> --output json > /tmp/<env>-backup-$(date +%s).json`.
- **Verify rollback alarms** are in `OK` state before start-deployment.
- **Prefer additive configuration changes** (add a flag, add a key) over destructive (delete a flag, rename a key).
- **Validate configuration payload** against the profile schema before start-deployment.

## Expert heuristic: "Bake time is the rollback window"

Bake time is the ONLY window during which AppConfig can detect a
bad configuration via CloudWatch alarms and roll back automatically.

```
Deployment lifecycle
   ├─ Step 1: deploy 20% targets (DeploymentDurationInMinutes)
   │    └─ Bake: hold for BakeTimeInMinutes
   │         ├─ MonitorList alarm ALARM? → ROLLING_BACK (revert to last COMPLETED)
   │         └─ All alarms OK? → proceed to step 2
   ├─ Step 2: deploy 40% targets
   │    └─ Bake ...
   ...
   └─ Final step: deploy 100%, FinalBakeTimeInMinutes hold, then COMPLETED
```

**Bake time vs. deployment duration:**

| Parameter | Meaning | Effect |
|---|---|---|
| `DeploymentDurationInMinutes` | Time AppConfig takes to fan out to the next percentage of targets | Fan-out window per step |
| `BakeTimeInMinutes` | Hold time AFTER each step deploys, before next step | The only rollback window between steps |
| `FinalBakeTimeInMinutes` | Final hold after 100% before COMPLETED | Last rollback window |
| `GrowthFactor` | Percentage increase per step | Step count = ceil(100 / GrowthFactor) |

**Rollback target selection:**

- AppConfig reverts to the configuration version of the last
  `COMPLETED` deployment, not the immediately prior step.
- If no prior `COMPLETED` exists, rollback leaves targets in an
  undefined state. Always seed an environment with a known-good
  `COMPLETED` deployment before risky rollouts.

**Per-strategy root causes:**

| Strategy | What to check when rollback fires |
|---|---|
| `AppConfig.AllAtOnce` | Alarms did not have time to fire during rollout — switch to a canary with bake time |
| `AppConfig.Linear50PercentEvery30Minutes` | Two steps only; alarm fired at 50% — verify the alarm threshold matches the new configuration's expected band |
| Custom linear (5-step) | Step at which rollback fired indicates the blast radius (e.g., 60% = 60% of targets saw the bad config) |
| CodeDeploy-managed | Check `codedeploy get-deployment` for the rollback event and CodeDeploy lifecycle events |

**Lambda extension / agent integration:**

- Lambda extension caches and polls every 45 seconds minimum
  (`AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS`). A target
  Lambda function sees the new configuration within one polling
  interval after the step boundary.
- The AppConfig agent (for EC2 / ECS / EKS) polls every 60 seconds
  by default and writes the configuration to a local file
  (`/etc/aws-appconfig/agent/config.json` by default). The
  application reads the local file.
- Direct `GetConfiguration` API calls are bounded by the
  `NextPollConfiguration` token; do not poll more frequently than
  the token allows.

## Recent AWS features (2024-2026)

- **AppConfig Lambda extension (2024-2026):** the
  `AWS-AppConfig-Extension` Lambda layer caches configurations and
  polls AppConfig on a configurable interval (45 seconds minimum).
  Enables runtime feature flags / dynamic configuration without
  function redeploy. Layer ARN:
  `arn:aws:lambda:<region>:027253079308:layer:AWS-AppConfig-Extension:<version>`.
- **AppConfig agent (2024-2025):** the `aws-appconfig-agent` Docker
  container / systemd service caches configurations on EC2 / ECS /
  EKS hosts. Writes the active configuration to a local file; the
  application reads the file. Polls every 60 seconds.
- **AppConfig deployment to CodeDeploy (2024-2026):** CodeDeploy
  deployment groups can use `AppConfig.AllAtOnce`,
  `AppConfig.50Percent`, `AppConfig.Linear20PercentEvery30Minutes`,
  and similar deployment configs. CodeDeploy orchestrates
  pre/post-traffic hooks; AppConfig provides the configuration
  store.
- **Feature flag schema (2024-2026):** `AWS.AppConfig.FeatureFlags`
  profile type with a structured payload (`flags: { <name>: { ... } }`).
  Supports attribute-level validation, conditional flags, and
  percentage-based flag evaluation (variants).
- **KMS encryption for hosted configurations (2024-2025):**
  `KmsKeyIdentifier` on the application or configuration profile
  encrypts hosted configuration versions at rest. The Lambda
  extension and agent roles must have `kms:Decrypt` on the key.
- **Typed configuration profiles (2024-2025):** `Type: AWS.Freeform`
  or `Type: AWS.AppConfig.FeatureFlags`. Feature-flag profiles
  require a Validators JSON schema entry; freeform profiles accept
  any valid JSON up to 64 KB.
- **FinalBakeTimeInMinutes (2024-2025):** a separate final bake
  window after the last step completes, before the deployment
  enters `COMPLETED`. Use for a final rollback window on long
  rollouts.
- **Configuration profiles from S3 (2024-2025):** `LocationUri`
  can point at an S3 object (`s3://bucket/key`) for configurations
  larger than 64 KB. The S3 bucket must grant AppConfig read
  access via bucket policy.
- **AppConfig integration with EventBridge (2024-2026):**
  deployment state transitions emit EventBridge events
  (`AppConfig Deployment State Change`), enabling downstream
  automation on `COMPLETED`, `ROLLING_BACK`, `ROLLED_BACK`,
  `TERMINATED`.
- **AppConfig for Amazon ECS / EKS (2024-2025):** the AppConfig
  agent ships as a sidecar container; tasks / pods read the
  configuration from the agent's local file.

## Domain

AWS CloudOps / AppConfig Deployment Lifecycle & Configuration
Operations.

## AWS documentation

- **AWS AppConfig User Guide** — https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
- **AppConfig deployment strategies** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-deployment-strategy.html
- **AppConfig configuration profiles** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-profile.html
- **AppConfig working with CloudWatch alarms** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-retrieving-the-configuration.html
- **AppConfig Lambda extension** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-lambda-extensions.html
- **AppConfig agent** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-agent.html
- **AppConfig feature flags** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-feature-flags.html
- **AppConfig integration with CodeDeploy** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-codedeploy.html
- **AWS CLI AppConfig reference** — https://docs.aws.amazon.com/cli/latest/reference/appconfig/
- **AppConfig API Reference** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-API.html
