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
| references/deployment-strategies-and-rollback.md | Strategy, rollback, CodeDeploy detail | On demand |
| references/lambda-extension-and-runtime-integration.md | Extension, agent, flag schema detail | On demand |
| references/advanced-patterns.md | Step-0 expert knowledge + heuristics + recent features | On demand |
| references/diagnostic-commands.md | Pre-flight + diagnostic runbooks | On demand |
| references/worked-examples.md | Secondary worked example + setup boilerplate | On demand |

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

Command listing: [diagnostic-commands.md](references/diagnostic-commands.md). The seven live-account pre-flight CLIs (list-applications through describe-alarms) plus the metadata-gate table mapping Environment.State, profile Type, MonitorList alarms, DEPLOYING state, and 64 KB size to their blocking effects.
Run before classification; malformed input emits `VERDICT: ERROR`.

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AppConfig behaviors

Expert-knowledge deep dive: [advanced-patterns.md](references/advanced-patterns.md). Eleven non-obvious behaviors — GetConfiguration as runtime source of truth, bake-after-step timing, all-at-once fan-out tail, rollback target semantics, Lambda extension env vars, CodeDeploy traffic routers, restrictive flag schema, 64 KB limit, KmsKeyIdentifier, TERMINATED semantics, StopDeployment past the rollback point.
Loaded on demand — Step 1 below encodes the actionable pre-check rules.

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

Boilerplate: [worked-examples.md](references/worked-examples.md). create-application, create-environment, create-configuration-profile (AWS.Freeform), create-hosted-configuration-version (<= 64 KB), with Id capture via list-* --query.
One-time setup pattern.

### Create a linear deployment strategy with bake time (5-step canary)

Boilerplate: [deployment-strategies-and-rollback.md](references/deployment-strategies-and-rollback.md). create-deployment-strategy for a 5-step linear canary (GrowthFactor 20, 30 min deploy + 30 min bake).
GrowthFactor=20 LINEAR yields 20/40/60/80/100; total ~5 x (30+30) = 300 minutes.

### Start a deployment with rollback alarms

Boilerplate: [deployment-strategies-and-rollback.md](references/deployment-strategies-and-rollback.md). start-deployment with strategy / profile / version / KMS flags populated.
MonitorList alarms are set via SDK or console (the CLI does not accept them) or watched via describe-alarms polling.

### CodeDeploy-managed AppConfig deployment (canary)

Boilerplate: [deployment-strategies-and-rollback.md](references/deployment-strategies-and-rollback.md). create-deployment-group with --deployment-config-name AppConfig.50Percent and BLUE_GREEN / WITH_TRAFFIC_CONTROL.
CodeDeploy orchestrates pre/post-traffic hooks; AppConfig provides the configuration store.

### Lambda extension (runtime feature flags without redeploy)

Boilerplate: [lambda-extension-and-runtime-integration.md](references/lambda-extension-and-runtime-integration.md). Add the AWS-AppConfig-Extension layer and AWS_APPCONFIG_EXTENSION_* env vars; the function reads http://localhost:2772.
Updates land within the 45-second polling interval without a function redeploy.

## Diagnostic flows

Command runbooks: [diagnostic-commands.md](references/diagnostic-commands.md). Stuck DEPLOYING (EventLog step analysis), ROLLING_BACK / ROLLED_BACK (alarm trigger identification), and TERMINATED (terminal causes + fresh start-deployment).
Each runbook lists the exact get-deployment / describe-alarms probes and the decision at each branch.

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

Secondary example: [worked-examples.md](references/worked-examples.md). Rollback blocked (BLOCKED) — StopDeployment applies only to DEPLOYING, and no prior COMPLETED means no known-good version to revert to.
Includes the list-hosted-configuration-versions remediation for a manual revert.

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

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Bake time is the ONLY rollback window — lifecycle diagram, DeploymentDuration vs Bake vs FinalBake table, rollback-target selection, per-strategy root causes, extension/agent polling.
Seed an environment with a known-good COMPLETED deployment before risky rollouts.

## Recent AWS features (2024-2026)

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Lambda extension layer, AppConfig agent (EC2/ECS/EKS), CodeDeploy configs, feature-flag schema, KMS, typed profiles, FinalBakeTimeInMinutes, S3-backed profiles, EventBridge state events, ECS/EKS sidecar (2024-2026).
Loaded on demand when the task calls for the newest capabilities.

## References (load on demand)

- [Deployment strategies and rollback](references/deployment-strategies-and-rollback.md) — strategy parameter semantics, rollback model, CloudWatch alarm wiring, CodeDeploy integration, diagnostic runbooks
- [Lambda extension and runtime integration](references/lambda-extension-and-runtime-integration.md) — extension architecture, AppConfig agent, direct GetConfiguration, feature flag schema, runtime pitfalls
- [Advanced patterns](references/advanced-patterns.md) — Step-0 non-obvious behaviors, bake-time rollback-window heuristic, recent AWS features 2024-2026
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight CLI listing, metadata gate table, stuck DEPLOYING / ROLLING_BACK / TERMINATED runbooks
- [Worked examples](references/worked-examples.md) — rollback-blocked (BLOCKED) worked example, create application / environment / profile boilerplate

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
