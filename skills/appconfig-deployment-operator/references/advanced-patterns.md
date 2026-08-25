# Advanced Patterns — AppConfig Deployment Operator

Step-0 expert knowledge, the bake-time rollback-window heuristic, and
recent AWS features moved verbatim from the SKILL.md body for
progressive disclosure (agentskills.io). Loaded on demand by the skill.

---

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
