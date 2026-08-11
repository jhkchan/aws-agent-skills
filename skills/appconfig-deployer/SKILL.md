---
name: appconfig-deployer
description: >-
  Provisions AWS AppConfig resources with production defaults: application
  creation, environments, configuration profiles (free form, JSON, YAML),
  deployment strategies (linear, exponential, all-at-once), bake time with
  CloudWatch alarms, deployment validation (Lambda validators), feature
  flags, dynamic JSON schema validation, configuration version management,
  rollback on alarm, and integration with Lambda/EventBridge. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when creating
  an AppConfig application, setting up configuration profiles, defining
  deployment strategies, enabling feature flags, adding Lambda validators,
  or configuring alarm-based rollback. Triggers: create appconfig
  application, appconfig deployment strategy, appconfig configuration
  profile, appconfig feature flags, appconfig lambda validator, appconfig
  rollback on alarm, appconfig bake time, appconfig environment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with appconfig access.
  Works with Terraform aws_appconfig_application /
  aws_appconfig_environment / aws_appconfig_configuration_profile /
  aws_appconfig_deployment_strategy / aws_appconfig_deployment /
  aws_appconfig_extension resources and CloudFormation
  AWS::AppConfig::Application / Environment / ConfigurationProfile /
  DeploymentStrategy / Deployment templates.
keywords:
  - aws
  - appconfig
  - feature flags
  - cloudops
  - deploy
  - provisioning
  - deployment strategy
  - linear
  - exponential
  - all-at-once
  - bake time
  - cloudwatch alarm
  - lambda validator
  - rollback
  - configuration profile
  - schema validation
tags:
  - aws
  - appconfig
  - feature-flags
  - cloudops
  - deploy
  - provisioning
  - deployment-strategy
  - lambda-validator
  - rollback
  - configuration-profile
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - appconfig
    - feature-flags
    - cloudops
    - deploy
    - provisioning
    - deployment-strategy
    - lambda-validator
    - rollback
    - configuration-profile
  dependencies:
    - aws-orchestrator
  keywords:
    - create appconfig application
    - appconfig deployment strategy
    - appconfig configuration profile
    - appconfig feature flags
    - appconfig lambda validator
    - appconfig rollback on alarm
    - appconfig bake time
    - appconfig environment
  when_to_use: >-
    Invoke when the user wants to create an AppConfig application, configure
    environments and configuration profiles, define deployment strategies
    (linear, exponential, all-at-once), set up feature flags, add Lambda
    validators for deployment validation, configure CloudWatch alarm-based
    rollback, manage configuration versions, or integrate AppConfig with
    Lambda and EventBridge. Do NOT invoke for AWS Systems Manager Parameter
    Store (use SSM skills), or for Secrets Manager (use secrets skills).
---

# AppConfig Deployer

An AWS CloudOps agent skill that provisions AWS AppConfig resources with
correct defaults. The skill walks the operator through application
creation, environment setup, configuration profiles (free form, JSON,
YAML), deployment strategies (linear, exponential, all-at-once), bake
time configuration with CloudWatch alarms, Lambda validators for
deployment validation, feature flags, JSON schema validation,
configuration version management, rollback on alarm, and integration
with Lambda/EventBridge. It captures deployment topology and strategy
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create AppConfig application, AppConfig deployment strategy, AppConfig
configuration profile, AppConfig feature flags, AppConfig Lambda
validator, AppConfig rollback on alarm, AppConfig bake time, AppConfig
environment.

## STRICT output contract

When this skill is invoked with an AppConfig-provisioning request
(create an application, configure a deployment strategy, set up a
configuration profile, enable feature flags, add validators, configure
alarm-based rollback, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `APPCONFIG:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[x]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Application creation | Core resource model |
| Step 2 — Environments | Environment lifecycle |
| Step 3 — Configuration profiles (free form, JSON, YAML) | Config data model |
| Step 4 — Deployment strategies (linear, exponential, all-at-once) | Rollout control |
| Step 5 — Bake time and CloudWatch alarms | Safe rollout monitoring |
| Step 6 — Lambda validators (deployment validation) | Pre-deploy validation |
| Step 7 — Feature flags and dynamic JSON schema | Flagged config |
| Step 8 — Configuration version management | Version lifecycle |
| Step 9 — Rollback on alarm | Automated safety |
| Step 10 — Integration with Lambda and EventBridge | Event-driven |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/deployment-strategies-and-alarms.md | Strategy + alarm detail |
| references/validators-and-feature-flags.md | Validator + flag detail |

## Mindset

**One-line takeaway:** AppConfig is a managed feature-flag and dynamic-
configuration service that safely rolls out configuration changes using
deployment strategies. A deployment strategy controls how fast a new
configuration reaches targets (linear, exponential, or all-at-once).
Bake time with CloudWatch alarms enables automatic rollback if the new
configuration causes errors. Lambda validators run before the deployment
starts to catch bad configurations before they reach any targets.

Three misconceptions dominate AppConfig misdesign at provisioning time:

- **"Deploying a configuration is instantaneous."** It is not. A
  deployment strategy controls the rollout rate. Linear deploys a
  percentage of targets every step. Exponential doubles the percentage
  each step. All-at-once deploys to 100% immediately. The growth
  factor, step duration, and bake time together define how safely the
  configuration reaches all targets. Skipping the deployment strategy
  means no controlled rollout — it is the equivalent of deploying
  without a safety net.

- **"Validators are optional nice-to-haves."** They are not. Lambda
  validators run BEFORE the deployment begins, validating the new
  configuration content. A failed validator blocks the deployment
  entirely — no targets receive the bad configuration. Without
  validators, a malformed JSON or a schema-violating flag value reaches
  targets during the rollout window, and rollback-on-alarm is the only
  defense. Validators are the first line of defense; alarm-based
  rollback is the second.

- **"Bake time is just a timer."** It is not. Bake time is the interval
  between each deployment step during which CloudWatch alarms are
  monitored. If ANY configured alarm fires during the bake time, the
  deployment is automatically rolled back. The growth factor determines
  how much traffic shifts per step; the bake time determines how long
  the system watches for errors before shifting the next batch. A short
  bake time with no alarms is a blind deployment. A proper bake time
  with the right alarms is the core safety mechanism.

## Configuration dependency graph (novel heuristic)

AppConfig configurations are NOT independent. The application must
exist before environments. Environments must exist before configuration
profiles can be deployed. Deployment strategies must be defined before
deployments. Validators must be attached to configuration profiles
before deployments can be validated. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Application | nothing — top-level container | application name must be unique within the account+region | environments, configuration profiles |
| Environment | application exists | environment name must be unique within the application | deployments |
| Configuration profile | application exists; environment is NOT required at creation | profile type (free form, JSON, YAML) is immutable after creation; validators attached at profile creation | configuration versions, deployments |
| Deployment strategy | nothing — reusable across applications | growth factor must be 1-100; bake time minimum is 0 (no bake); replicate must be 0-100 | deployments |
| Lambda validator | configuration profile exists; Lambda function exists | validator runs before EVERY deployment of that profile; a failing validator blocks deployment | deployment validation |
| Configuration version | configuration profile exists | content is uploaded as a versioned blob; versions are immutable after creation | deployments |
| Deployment | application, environment, configuration profile, configuration version, deployment strategy all exist | deployment starts the rollout; monitors CloudWatch alarms during bake time | live configuration changes |
| Feature flags | configuration profile with type AWS.Freeform using a feature flag schema | feature flag schema must be referenced at profile creation via KMS key ARN or location URI | dynamic flag management |
| CloudWatch alarm (bake time) | deployment strategy has bake time > 0; alarm exists and is configured on the deployment | alarms are checked by ARN during each bake window; missing alarm ARN means no monitoring for that metric | rollback on alarm |
| Rollback on alarm | deployment in progress; CloudWatch alarm fires during bake time | rollback reverts to the previous configuration version automatically | automated safety |

**The deployment-strategy-and-bake-time row is the one a baseline model
misses.** Creating the application and profile is necessary but NOT
sufficient. The deployment strategy determines the rollout speed and the
bake time determines the monitoring window. Without a proper strategy,
the configuration reaches all targets instantly with no safety net. The
Lambda validator is another commonly skipped configuration. The
procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- Configuration profile type is immutable after creation. A free-form
  profile CANNOT be converted to JSON or YAML later. Choose the type
  carefully at creation time.
- Lambda validators are attached to the configuration profile, not the
  deployment. They run before every deployment of that profile.
- The deployment strategy's bake time is the window during which
  CloudWatch alarms are monitored. A bake time of 0 means NO alarm
  monitoring during the rollout.
- Feature flags require a configuration profile with a specific schema
  URI. A standard JSON/YAML profile CANNOT host feature flags without
  the schema.
- Configuration versions are immutable. To update, create a new version
  and deploy it.

## Expert heuristic: deployment strategy growth factor + bake time

A baseline model says "create a deployment and start it." The correct
heuristic recognizes that the deployment strategy's growth factor,
replicate, and bake time together define the safety envelope.

```text
Deployment strategy parameters:
  Growth factor (1-100): percentage of targets to receive the new config per step
  Replicate (0-100): optional — replicate a subset for canary
  Bake time (minutes): monitoring window between steps (0 = no monitoring)
  Final percentage: must reach 100% for full deployment

Linear strategy:    Growth=20, Bake=10  → 20%/10min, 40%/10min, 60%/10min, 80%/10min, 100%/10min
Exponential strategy: Growth=2, Bake=10  → 2%/10min, 4%/10min, 8%/10min, 16%/10min, 32%/10min, 64%/10min, 100%/10min
All-at-once:        Growth=100, Bake=0   → 100% immediately, no bake monitoring

Key: bake time > 0 enables CloudWatch alarm monitoring during each step window.
     If ANY alarm fires during bake time, the deployment auto-rolls back.
     Bake time = 0 means NO alarm monitoring = blind deployment.
```

**Key implication:** the #1 cause of "my config broke production" is an
all-at-once deployment with no bake time and no alarms. Always use a
linear or exponential strategy with a meaningful bake time and at least
one CloudWatch alarm for error-rate monitoring.

## Expert heuristic: validator lifecycle and alarm-based rollback

Validators and alarms are complementary safety layers. Validators run
BEFORE deployment; alarms run DURING deployment.

```text
Safety layers for an AppConfig deployment:

Layer 1: Lambda validator (pre-deployment)
  → Runs when: deployment is initiated, before any target receives the config
  → Catches: malformed JSON, schema violations, invalid flag values, semantic errors
  → On failure: deployment is BLOCKED — no targets receive the bad config

Layer 2: CloudWatch alarm + bake time (during deployment)
  → Runs when: during each bake window between deployment steps
  → Catches: runtime errors caused by the new config (5xx spikes, latency, custom metrics)
  → On failure: deployment is AUTO-ROLLED BACK to the previous version

Layer 3: Manual rollback (post-deployment)
  → Operator initiates start-deployment with a previous configuration version
  → Use when: the deployment completed but problems are detected later
```

**Key implication:** a robust AppConfig deployment has BOTH a Lambda
validator (pre-deployment gate) AND at least one CloudWatch alarm
(during-deployment safety net). Skipping either layer removes a
critical defense.

## Expert heuristic: feature flag schema vs free-form configuration

Feature flags use a specific configuration profile schema that enables
dynamic flag management via the AppConfig API or agent integrations.
Free-form configurations are opaque blobs that AppConfig treats as
versioned text.

```text
Configuration profile types:
  AWS.Freeform        → free-form configuration (text, JSON, YAML — no schema enforcement)
  AWS.AppConfig.JSON  → JSON configuration with optional schema validation
  AWS.AppConfig.YAML  → YAML configuration with optional schema validation

Feature flags:
  Created as a configuration profile with type AWS.Freeform but with a
  feature flag schema URI (e.g., s3://bucket/flags-schema.json)
  → Enables dynamic flag management via StartConfigurationSession API
  → Supports flag-level attributes (enabled, percentage, variant)
  → Schema validates flag structure at deployment time

JSON schema validation:
  Attach a JSON schema to a JSON/YAML configuration profile
  → Schema is validated at configuration version creation time
  → Ensures all deployed versions conform to the expected structure
  → Caught before deployment — not during bake time
```

**Key implication:** feature flags are NOT just JSON configurations.
They use a specific schema that enables the AppConfig feature flag
agent and API. A standard JSON profile without the schema does NOT
support flag-level operations.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Application name or ID | The application is the top-level container | `aws appconfig list-applications` |
| Environment name or ID | Deployments target a specific environment | `aws appconfig list-environments --application-id <id>` |
| Configuration profile type decided | Profile type (free form, JSON, YAML) is immutable after creation | Assess config format requirements |
| Deployment strategy parameters | Growth factor, bake time, and replicate define the rollout safety | `aws appconfig list-deployment-strategies` |
| CloudWatch alarm ARNs (if bake time > 0) | Alarms are monitored during bake time for auto-rollback | `aws cloudwatch describe-alarms` |
| Lambda validator function ARN (if using validators) | Validator runs before deployment to validate config content | `aws lambda get-function --function-name <name>` |
| IAM permissions for AppConfig actions | appconfig:CreateApplication, CreateEnvironment, CreateConfigurationProfile, etc. | `aws iam list-attached-role-policies` |
| KMS key ARN (if encrypting configuration data) | AppConfig can use a customer-managed KMS key for encryption | `aws kms describe-key --key-id <id>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Application creation

The AppConfig application is the top-level container for environments,
configuration profiles, and deployments.

```bash
APP_ID=$(aws appconfig create-application \
  --name "my-app-config" \
  --description "Configuration management for my application" \
  --query 'Id' --output text)
```

## Step 2 — Environments

Each application has one or more environments (e.g., development,
staging, production). Deployments target a specific environment.

```bash
ENV_ID=$(aws appconfig create-environment \
  --application-id "$APP_ID" \
  --name "production" \
  --description "Production environment" \
  --query 'Id' --output text)
```

## Step 3 — Configuration profiles (free form, JSON, YAML)

Configuration profiles hold the configuration content. The profile type
(free form, JSON, YAML) is immutable after creation.

```bash
# Free-form configuration profile
PROFILE_ID_FF=$(aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "feature-flags" \
  --location-uri "hosted" \
  --type "AWS.Freeform" \
  --query 'Id' --output text)

# JSON configuration profile with schema validation
PROFILE_ID_JSON=$(aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "app-settings" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --query 'Id' --output text)
```

**Feature flag profile** uses `--type "AWS.Freeform"` with a KMS key
for encryption. See `references/validators-and-feature-flags.md` for
the full feature flag schema example.

**Critical:** the profile type is immutable. A free-form profile cannot
later become a JSON profile. Choose carefully.

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

## Step 6 — Lambda validators (deployment validation)

Lambda validators run BEFORE the deployment begins. They validate the
configuration content and block deployment if validation fails. See
`references/validators-and-feature-flags.md` for a full validator
function example with semantic validation patterns.

**Attach the validator to a configuration profile:**

```bash
aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "validated-config" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators '[{"Type":"LAMBDA","Content":"'$(aws lambda get-function --function-name config-validator --query Configuration.FunctionArn --output text)'"}]'
```

**Critical:** validators run on EVERY deployment of that profile. A
failing validator blocks the deployment entirely.

## Step 7 — Feature flags and dynamic JSON schema

Feature flags enable dynamic configuration management. They use a
specific configuration profile schema that supports flag-level
operations.

**Create a feature flag schema:**

```json
{
  "flags": {
    "newCheckoutFlow": {
      "enabled": true,
      "percentage": 25
    },
    "betaDashboard": {
      "enabled": false,
      "percentage": 0
    }
  }
}
```

**JSON schema validation for configuration profiles:**

For JSON/YAML profiles, attach a JSON schema to validate structure:

```bash
aws appconfig create-configuration-profile \
  --application-id "$APP_ID" \
  --name "schema-validated-config" \
  --location-uri "hosted" \
  --type "AWS.AppConfig.JSON" \
  --validators '[{"Type":"JSON_SCHEMA","Content":"{\"type\":\"object\",\"properties\":{\"timeout\":{\"type\":\"number\",\"minimum\":1,\"maximum\":300}},\"required\":[\"timeout\"]}"}]'
```

**Key:** JSON schema validation catches structural errors at version
creation time. Lambda validators catch semantic errors at deployment
time. Both are complementary.

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

## Step 10 — Integration with Lambda and EventBridge

AppConfig integrates with Lambda and EventBridge for event-driven
configuration updates.

**Lambda integration ( AppConfig extension ):**

AppConfig provides a pre-built Lambda extension that enables Lambda
functions to retrieve configuration without SDK calls.

```bash
# Enable the AppConfig Lambda extension
aws lambda update-function-configuration \
  --function-name "my-function" \
  --environment '{"Variables":{"AWS_APPCONFIG_EXTENSION_APPLICATION_ID":"'${APP_ID}'","AWS_APPCONFIG_EXTENSION_ENVIRONMENT_ID":"'${ENV_ID}'","AWS_APPCONFIG_EXTENSION_CONFIGURATION_PROFILE_ID":"'${PROFILE_ID_JSON}'"}}'
```

**EventBridge integration:**

AppConfig emits events to EventBridge on deployment state changes:

```json
{
  "source": ["aws.appconfig"],
  "detail-type": [
    "AppConfig Deployment State Change"
  ],
  "detail": {
    "state": ["BAKING", "DEPLOYING", "COMPLETE", "ROLLED_BACK", "ROLLED_BACK"]
  }
}
```

**Key:** EventBridge rules can trigger notifications or remediation
Lambda functions on deployment state changes, especially on
ROLLED_BACK.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **AppConfig feature flag agent (2023-2024):** AWS introduced the
  AppConfig Agent for Lambda and ECS, providing a local HTTP interface
  for configuration retrieval with caching and token management.

- **KMS encryption for hosted configurations (2023-2024):** Hosted
  configuration versions now support customer-managed KMS keys for
  encryption at rest.

- **Exponential growth type (2023-2024):** Deployment strategies now
  support exponential growth, doubling the percentage of targets each
  step for faster initial validation (canary-like behavior).

- **Deletion protection (2024-2025):** AppConfig added deletion
  protection for environments, preventing accidental environment
  deletion when deployments are in progress.

- **Terraform provider improvements (2023-2024):** The Terraform
  `aws_appconfig_extension`, `aws_appconfig_extension_association`, and
  `aws_appconfig_hosted_configuration_version` resources now support
  full lifecycle management of validators, extensions, and hosted
  versions.

- **AppConfig deployment alarm enhancements (2024-2025):** AWS enhanced
  the alarm monitoring during bake time, including support for
  composite alarms and alarm-based deployment rollback with more
  granular monitoring intervals.

## NEVER do these things

1. **NEVER use all-at-once deployment with bake time 0 in production.**
   All-at-once with no bake time provides NO alarm monitoring. Any
   configuration error reaches all targets instantly with no safety net.
   Always use linear or exponential with a meaningful bake time for
   production.

2. **NEVER skip the Lambda validator.** Validators run BEFORE deployment
   and catch malformed configurations, schema violations, and semantic
   errors. Without a validator, bad configurations reach targets during
   the rollout window, and alarm-based rollback is the only defense.

3. **NEVER assume the configuration profile type can be changed later.**
   The profile type (free form, JSON, YAML) is immutable after creation.
   Choose the type carefully at creation time based on the configuration
   format and schema requirements.

4. **NEVER deploy without at least one CloudWatch alarm during bake
   time.** Bake time > 0 with no alarms is a blind deployment. At
   minimum, monitor error rate (5XX), latency, and application-specific
   error metrics.

5. **NEVER confuse feature flags with standard JSON configurations.**
   Feature flags use a specific schema URI that enables the AppConfig
   feature flag agent and flag-level API operations. A standard JSON
   profile without the schema does NOT support flag-level operations.

6. **NEVER assume JSON schema validation replaces Lambda validators.**
   JSON schema validates structure (types, required fields, ranges) at
   version creation time. Lambda validators validate semantics (business
   logic, cross-field dependencies) at deployment time. Both are needed.

7. **NEVER forget that configuration versions are immutable.** To
   update a configuration, create a NEW version and deploy it. The old
   version remains available for rollback.

8. **NEVER deploy without verifying the environment.** Each environment
   (dev, staging, production) is independent. Deploying to the wrong
   environment is a common operational error. Always verify the
   environment ID before starting a deployment.

9. **NEVER use bake time 0 for production deployment strategies.** Bake
   time 0 means AppConfig does NOT monitor any CloudWatch alarms during
   the rollout. The entire purpose of a controlled rollout is to detect
   errors early — without bake time, there is no detection window.

10. **NEVER assume rollback-on-alarm covers post-deployment errors.**
    Automatic rollback only works DURING the deployment (while in BAKING
    or DEPLOYING state). Once the deployment is COMPLETE, rollback
    requires manual initiation with a previous configuration version.

## Output format

```text
APPCONFIG: <application-name> (<application-id>) / <environment-name> (<environment-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Application: <name> (<id>)
  [✓|✗] Environment: <name> (<id>)
  [✓|✗] Configuration profile: <name> (<id>) — type: <AWS.Freeform|AWS.AppConfig.JSON|AWS.AppConfig.YAML>
  [✓|✗] Configuration version: <version-number>
  [✓|✗] Deployment strategy: <name> (<id>) — <LINEAR|EXPONENTIAL> growth=<factor>% bake=<minutes>min
  [✓|✗] Lambda validator: <function-name> (<arn>) | None
  [✓|✗] JSON schema validation: enabled | disabled
  [✓|✗] Feature flags: enabled (schema URI: <uri>) | disabled
  [✓|✗] CloudWatch alarms: <alarm-name> (<arn>) [monitored during bake time]
  [✓|✗] KMS encryption: enabled (<key-arn>) | AWS-managed
  [✓|✗] Rollback on alarm: enabled (auto-rollback during bake time) | disabled (bake time = 0)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws appconfig get-application --application-id <id>
  aws appconfig list-environments --application-id <id>
  aws appconfig get-configuration-profile --application-id <id> --configuration-profile-id <id>
  aws appconfig get-deployment-strategy --deployment-strategy-id <id>
  aws appconfig get-deployment --application-id <id> --environment-id <id> --deployment-number <num>
```

### Worked example — linear deployment with validators and alarms

```text
APPCONFIG: my-app-config (abc12345) / production (def67890)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Application: my-app-config (abc12345)
  [✓] Environment: production (def67890)
  [✓] Configuration profile: app-settings (ghi11111) — type: AWS.AppConfig.JSON
  [✓] Configuration version: 3
  [✓] Deployment strategy: linear-20pct-10min (jkl22222) — LINEAR growth=20% bake=10min
  [✓] Lambda validator: config-validator (arn:aws:lambda:us-east-1:123456789012:function:config-validator)
  [✓] JSON schema validation: enabled
  [✓] Feature flags: disabled
  [✓] CloudWatch alarms: appconfig-deploy-error-rate (arn:aws:cloudwatch:us-east-1:123456789012:alarm:appconfig-deploy-error-rate) [monitored during bake time]
  [✓] KMS encryption: AWS-managed
  [✓] Rollback on alarm: enabled (auto-rollback during bake time)
  [✓] Tags: Environment=production, Application=my-app
VERIFICATION_COMMANDS:
  aws appconfig get-application --application-id abc12345
  aws appconfig list-environments --application-id abc12345
  aws appconfig get-configuration-profile --application-id abc12345 --configuration-profile-id ghi11111
  aws appconfig get-deployment-strategy --deployment-strategy-id jkl22222
  aws appconfig get-deployment --application-id abc12345 --environment-id def67890 --deployment-number 1
```

## Error handling

- **Deployment blocked by validator:** the Lambda validator returned
  non-200. Check function logs, fix the config content, create a new
  version, and retry.
- **Deployment rolled back automatically:** a CloudWatch alarm fired
  during bake time. Check alarm metrics and logs, fix the config,
  create a new version, and retry.
- **Configuration version creation fails:** JSON schema validation
  failed at creation time. Ensure the config content conforms to the
  schema constraints.
- **Deployment stuck in BAKING:** the deployment is in the bake window
  monitoring alarms. Verify the strategy configuration and alarm
  thresholds if this persists.
- **Environment not found:** the environment ID does not exist within
  the application. Verify the application/environment ID pairing.

## Domain

AWS CloudOps / AWS AppConfig Dynamic Configuration and Feature Flag
Provisioning.

## AWS documentation

- **AppConfig User Guide** — https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
- **Deployment strategies** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-deployment-strategy.html
- **Working with validators** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-profile-validator.html
- **Feature flags** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-storage.html
- **Rollback on alarm** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-rolling-back.html
