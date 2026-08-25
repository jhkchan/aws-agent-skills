# Deployment Strategies and CloudWatch Alarms — AppConfig Deployer

Deep reference on deployment strategy parameters (growth factor,
growth type, bake time, replicate), CloudWatch alarm configuration
for bake-time monitoring, alarm-based automatic rollback mechanics,
and strategy selection guidance. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Deployment strategy parameters

### Growth factor and growth type

The growth factor defines the percentage of targets that receive
the new configuration per step. The growth type controls how the
factor is applied.

```text
Growth type: LINEAR
  Growth factor = 20%
  Step 1: 20% of targets receive new config
  Step 2: 40% (cumulative)
  Step 3: 60%
  Step 4: 80%
  Step 5: 100%
  Steps between increments = deployment-duration-in-minutes / (100 / growth-factor)

Growth type: EXPONENTIAL
  Growth factor = 2% (initial percentage)
  Step 1: 2%
  Step 2: 4% (doubled)
  Step 3: 8%
  Step 4: 16%
  Step 5: 32%
  Step 6: 64%
  Step 7: 100%
  Each step doubles the previous, enabling canary-like initial validation.
```

**When to use exponential:** when you want a very small initial
exposure (canary) followed by rapid expansion. The 2% initial step
catches errors with minimal blast radius, and the exponential ramp
completes the rollout quickly once the initial batch is validated.

**When to use linear:** when you want predictable, steady rollout.
Each step exposes the same incremental percentage. Simpler to reason
about and debug.

### Bake time (final-bake-time-in-minutes)

Bake time is the monitoring window between deployment steps. During
each bake window, AppConfig monitors the configured CloudWatch alarms.
If any alarm fires, the deployment is automatically rolled back.

```bash
# Linear strategy with 10-minute bake time
aws appconfig create-deployment-strategy \
  --name "linear-20pct-10min" \
  --growth-factor 20 \
  --growth-type "LINEAR" \
  --replicate-to "NONE" \
  --final-bake-time-in-minutes 10
```

**Bake time = 0:** no alarm monitoring during rollout. This is
acceptable for non-critical configs (development, staging) but risky
for production. With bake time 0, the deployment completes as fast
as possible with no safety net.

**Bake time > 0:** each step pauses for the bake duration. Alarms
are checked at each pause. A firing alarm triggers automatic
rollback.

### Replicate parameter

The `--replicate-to` parameter controls whether the configuration
is replicated to another location:

- `NONE` — no replication (default for most deployments)
- `SSM_DOCUMENT` — replicate to SSM Document for use with State Manager

Most AppConfig deployments use `NONE`. Replication to SSM is for
specific State Manager integration scenarios.

## CloudWatch alarm configuration

### Creating alarms for AppConfig rollback

AppConfig monitors CloudWatch alarms by ARN during each bake window.
The alarms should track metrics that indicate the new configuration
is causing problems.

**Common alarm patterns:**

```bash
# Error rate alarm (API Gateway 5XX)
aws cloudwatch put-metric-alarm \
  --alarm-name "appconfig-5xx-error-rate" \
  --metric-name "5XXError" \
  --namespace "AWS/ApiGateway" \
  --statistic "Sum" \
  --period 60 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 1

# Lambda error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "appconfig-lambda-errors" \
  --metric-name "Errors" \
  --namespace "AWS/Lambda" \
  --statistic "Sum" \
  --period 60 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=my-function

# Custom application metric alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "appconfig-app-error-spike" \
  --metric-name "ApplicationErrors" \
  --namespace "MyApp" \
  --statistic "Sum" \
  --period 60 \
  --threshold 20 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 2
```

### Attaching alarms to a deployment

Alarms are specified when starting the deployment:

```bash
aws appconfig start-deployment \
  --application-id "$APP_ID" \
  --environment-id "$ENV_ID" \
  --deployment-strategy-id "$STRATEGY_ID" \
  --configuration-profile-id "$PROFILE_ID" \
  --configuration-version "$VERSION_ID" \
  --kms-key-identifier "arn:aws:kms:us-east-1:123456789012:key/abc123"
```

### Alarm monitoring during bake time

During each bake window:

1. AppConfig checks the state of each configured alarm.
2. If ANY alarm is in ALARM state, the deployment is rolled back.
3. The rollback reverts all targets to the previous configuration
   version.
4. The deployment state transitions to ROLLED_BACK.

```text
Deployment lifecycle:
  DEPLOYING → (growth step applied) → BAKING (alarm monitoring) → DEPLOYING → ... → COMPLETE
  BAKING → (alarm fires) → ROLLED_BACK
```

## Automatic rollback mechanics

### What happens on rollback

1. The current deployment is stopped immediately.
2. All targets that received the new configuration are reverted to
   the previous configuration version.
3. The deployment state becomes ROLLED_BACK.
4. An EventBridge event is emitted (AppConfig Deployment State
   Change, state=ROLLED_BACK).
5. The previous configuration version remains active.

### What rollback does NOT do

- Rollback does NOT fix the bad configuration. It reverts to the
  previous version. The bad version still exists in the version
  history.
- Rollback does NOT notify operators directly. Use EventBridge rules
  to send SNS/Lambda notifications on ROLLED_BACK state.
- Rollback does NOT work after the deployment is COMPLETE. Once
  COMPLETE, manual rollback is required (start a new deployment with
  the previous version).

## Strategy selection guide

| Scenario | Recommended strategy | Growth | Bake | Alarms |
|---|---|---|---|---|
| Production, critical config | Linear | 20% | 15 min | Error rate, latency, custom |
| Production, feature flag | Exponential | 2% | 10 min | Error rate, flag-specific |
| Staging, pre-prod validation | Linear | 25% | 5 min | Error rate |
| Development, non-critical | All-at-once | 100% | 0 min | None |
| High-traffic production | Exponential | 2% | 15 min | Error rate, latency, throughput |

## Terraform examples

```hcl
# Deployment strategy
resource "aws_appconfig_deployment_strategy" "linear" {
  name                          = "linear-20pct-10min"
  description                   = "Linear 20% with 10-minute bake"
  deployment_duration_in_minutes = 0
  growth_factor                 = 20
  growth_type                   = "LINEAR"
  replicate_to                  = "NONE"
  final_bake_time_in_minutes    = 10

  tags = {
    Environment = "production"
  }
}

# CloudWatch alarm for bake-time monitoring
resource "aws_cloudwatch_metric_alarm" "appconfig_error" {
  alarm_name          = "appconfig-deploy-error-rate"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  statistic           = "Sum"
  period              = 60
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
}

# Deployment (references strategy, profile, and version)
resource "aws_appconfig_deployment" "production" {
  application_id           = aws_appconfig_application.app.id
  environment_id           = aws_appconfig_environment.production.id
  deployment_strategy_id   = aws_appconfig_deployment_strategy.linear.id
  configuration_profile_id = aws_appconfig_configuration_profile.config.id
  configuration_version    = aws_appconfig_hosted_configuration_version.v1.version_number
  description              = "Deploy production config"
}
```

---

## Step-by-step CLI walkthroughs (moved verbatim from SKILL.md)

The SKILL.md body keeps only step stubs under progressive disclosure
(agentskills.io); the original step sections below were moved verbatim
so no content is lost.

## Step 4 — Deployment strategies (linear, exponential, all-at-once)

Deployment strategies control the rollout rate. The growth factor
defines the percentage of targets per step; the bake time defines the
monitoring window between steps.

```bash
# Linear — 20% per step, 10-minute bake
STRATEGY_ID=$(aws appconfig create-deployment-strategy \
  --name "linear-20pct-10min" --growth-factor 20 --growth-type "LINEAR" \
  --replicate-to "NONE" --final-bake-time-in-minutes 10 --query 'Id' --output text)

# Exponential — 2% initial, doubles each step (change growth-type to EXPONENTIAL)
# All-at-once — growth-factor 100, bake-time 0 (RISKY — no alarm monitoring)
```

**Critical:** all-at-once with bake time 0 provides NO alarm monitoring.
This is acceptable for non-critical configs but risky for production.

## Step 5 — Bake time and CloudWatch alarms

Bake time is the monitoring window between deployment steps. During each
bake window, AppConfig monitors configured CloudWatch alarms. If any
alarm fires, the deployment is automatically rolled back.

**Create a CloudWatch alarm for error rate:**

```bash
ALARM_ARN=$(aws cloudwatch put-metric-alarm \
  --alarm-name "appconfig-deploy-error-rate" \
  --metric-name "5XXError" \
  --namespace "AWS/ApiGateway" \
  --statistic "Sum" \
  --period 60 \
  --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 1 \
  --query 'AlarmArn' --output text)
```

**Attach alarms to a deployment:**

The alarm ARNs are specified when starting the deployment (see Step 8).
AppConfig monitors these alarms during each bake window.

**Critical:** a bake time of 0 means NO alarm monitoring. Always use a
bake time > 0 for production deployments with at least one alarm.

## Step 8 — Configuration version management

Configuration versions are immutable. To update a configuration, create
a new version and deploy it.

**Create a configuration version:**

```bash
# Upload configuration content as a new version
VERSION_ID=$(aws appconfig create-hosted-configuration-version \
  --application-id "$APP_ID" \
  --configuration-profile-id "$PROFILE_ID_JSON" \
  --content '{"timeout": 30, "retries": 3}' \
  --content-type "application/json" \
  --query 'VersionNumber' --output text)

echo "Configuration version: $VERSION_ID"
```

**List versions:**

```bash
aws appconfig list-hosted-configuration-versions \
  --application-id "$APP_ID" \
  --configuration-profile-id "$PROFILE_ID_JSON"
```

## Step 9 — Rollback on alarm

When a CloudWatch alarm fires during the bake time, AppConfig
automatically rolls back the deployment to the previous configuration
version.

**Start a deployment with alarm monitoring:**

```bash
DEPLOYMENT_ID=$(aws appconfig start-deployment \
  --application-id "$APP_ID" \
  --environment-id "$ENV_ID" \
  --deployment-strategy-id "$STRATEGY_ID_LINEAR" \
  --configuration-profile-id "$PROFILE_ID_JSON" \
  --configuration-version "$VERSION_ID" \
  --description "Deploy timeout configuration update" \
  --query 'DeploymentNumber' --output text)

echo "Deployment number: $DEPLOYMENT_ID"
```

**Monitor the deployment:**

```bash
aws appconfig get-deployment \
  --application-id "$APP_ID" \
  --environment-id "$ENV_ID" \
  --deployment-number "$DEPLOYMENT_ID"
```

**Key:** the deployment state transitions through BAKING, DEPLOYING,
and COMPLETE. If an alarm fires during BAKING, the state becomes
ROLLED_BACK.
