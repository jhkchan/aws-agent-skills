# End-to-end usage scenario: appconfig-deployment-operator

A walkthrough showing the skill planning a 5-step linear canary
deployment (`GrowthFactor=20`, 30 min deploy + 30 min bake) with a
CloudWatch rollback alarm wired, plus the Lambda extension
runtime integration. This exercises Step 0 (target capture),
Step 1 (pre-flight), Step 2 (start-deployment), and Step 4
(post-verify with alarm health).

## Input (user prompt)

> Start deployment "checkout-timeout-2026-08" in `us-east-1` for
> application "checkout-service" (id `abc123`), environment "prod"
> (id `env-456`), configuration profile "checkout-config"
> (id `prof-789`, type `AWS.Freeform`), configuration version 7.
> Strategy: `linear-20-percent-30min-bake` (GrowthFactor 20, 30 min
> deploy, 30 min bake, 30 min final bake). Rollback alarm:
> `arn:aws:cloudwatch:us-east-1:111122223333:alarm:checkout-5xx`
> (currently OK). The checkout-handler Lambda function uses the
> AppConfig extension; confirm convergence within one poll cycle.

## Skill output

```text
OPERATION: start-deployment
VERDICT: READY
TARGET: checkout-service / prod / deployment #14, us-east-1
PRE_CHECKS:
  - [PASS] Application checkout-service (id: abc123) exists
  - [PASS] Environment prod (id: env-456) State READY_FOR_DEPLOYMENT
  - [PASS] Configuration profile checkout-config (id: prof-789)
    type AWS.Freeform; latest hosted version 7 size 3.2 KB < 64 KB
  - [PASS] Deployment strategy linear-20-percent-30min-bake:
    GrowthFactor 20, DeploymentDurationInMinutes 30,
    BakeTimeInMinutes 30, FinalBakeTimeInMinutes 30 — 5-step
    canary, ~330 min wall-clock
  - [PASS] MonitorList alarm
    arn:aws:cloudwatch:us-east-1:111122223333:alarm:checkout-5xx
    currently OK
  - [PASS] Caller holds appconfig:StartDeployment,
    appconfig:GetDeployment
  - [PASS] list-deployments: no active DEPLOYING deployment on
    env-456
  - [PASS] KMS key arn:aws:kms:us-east-1:111122223333:key/abc
    decryptable by caller
STEPS:
  1. CONFIRM: About to start-deployment #14 on checkout-service /
     prod in account 111122223333 region us-east-1. Linear 20%
     canary (5 steps, 30 min deploy + 30 min bake each, 30 min
     final bake, ~330 min total). Rollback alarm: checkout-5xx.
     Proceed? (yes/no)
  2. aws appconfig start-deployment \
       --application-id abc123 \
       --environment-id env-456 \
       --deployment-strategy-id linear-20-percent-30min-bake \
       --configuration-profile-id prof-789 \
       --configuration-version 7 \
       --description "Raise checkout timeout to 5000 ms (cutoff 2026-08)" \
       --kms-key-identifier arn:aws:kms:us-east-1:111122223333:key/abc
  3. aws appconfig get-deployment --application-id abc123 \
       --environment-id env-456 --deployment-number 14
     (poll at each step boundary — every 60 min)
POST_VERIFY:
  - [PASS] (pending execution) expect State COMPLETED,
    PercentageComplete 100.00
  - [PASS] (pending execution) MonitorList alarm checkout-5xx
    remains OK through final bake
  - [PASS] (pending execution) Lambda extension poll on
    checkout-handler reports ClientConfigurationVersion 7 within
    45s of each step boundary
STATE: pending — will be DEPLOYING for ~330 min
PERCENTAGE_COMPLETE: 0.00
NOTES:
  - Strategy: 5-step linear canary (20/40/60/80/100). Each step
    deploys for 30 min, then bakes for 30 min. Final bake 30 min.
    Total ~330 min.
  - Detection lag: Lambda extension polls every 45s — targets
    converge within 45s of each step boundary.
  - Rollback: triggered if checkout-5xx transitions to ALARM
    during any bake window. Rollback reverts to the prior
    COMPLETED deployment's configuration version.
```

## What the skill caught that a generic assistant misses

1. **Bake time as the rollback window.** A generic assistant picks
   `AppConfig.AllAtOnce` for simplicity. The skill uses a 5-step
   canary with 30-min bake so the rollback alarm has five windows
   to catch a regression before reaching 100%.
2. **Alarm health pre-check.** A generic assistant skips the
   `describe-alarms` check and the deployment auto-rolls back on
   step 1. The skill verifies the alarm is `OK` before
   start-deployment.
3. **`State: READY_FOR_DEPLOYMENT` gate.** A generic assistant
   assumes the environment is ready. The skill checks the state
   explicitly.
4. **KMS decryptability.** A generic assistant omits the KMS
   pre-check; the Lambda extension silently serves stale cache
   when the role lacks `kms:Decrypt`. The skill verifies.
5. **Lambda extension convergence.** A generic assistant claims
   "deployed" at `PercentageComplete: 100`. The skill notes the
   45-second polling lag before targets see the new version.

## Slash-command invocation

```
/aws:operate-appconfig-deployment
```

Or via the orchestrator:

```
/aws:pipeline
You: "start checkout-timeout-2026-08 on checkout-service / prod"
```

The orchestrator emits `[Phase: Operate | Skills routed:
appconfig-deployment-operator]` and hands off to this skill for
the VERDICT.

## Related scenarios

The same skill handles:

- **All-at-once deployment** (`AppConfig.AllAtOnce`) — dev /
  sandbox only; no bake, no rollback window. Flag as risky.
- **Rollback via `stop-deployment`** — triggers `ROLLING_BACK`
  if a prior `COMPLETED` exists.
- **AppConfig Lambda extension adoption** — set
  `AWS_APPCONFIG_EXTENSION_*` env vars, attach the extension
  layer, read via `localhost:2772`.
- **CodeDeploy-managed AppConfig deployment** — use
  `AppConfig.50Percent` or `AppConfig.Linear20PercentEvery30Minutes`
  as the `deployment-config-name` with
  `deploymentStyle.deploymentOption = WITH_TRAFFIC_CONTROL`.
- **Feature-flag profile** — `Type: AWS.AppConfig.FeatureFlags`
  with a Validators JSON schema; structured flag payload.
- **TERMINATED recovery** — fix the cause (deleted profile,
  validation failure, IAM regression), then issue a fresh
  `start-deployment`. Terminated deployments cannot be resumed.
