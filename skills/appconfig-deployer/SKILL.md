---
name: appconfig-deployer
description: 'Provisions AWS AppConfig resources with production defaults: application creation, environments, configuration profiles (free form, JSON, YAML), deployment strategies (linear, exponential, all-at-once), bake time with CloudWatch alarms, deployment validation (Lambda validators), feature flags, dynamic JSON schema validation, configuration version management, rollback on alarm, and integration with Lambda/EventBridge. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an AppConfig application, setting up configuration profiles, defining deployment strategies, enabling feature flags, adding Lambda validators, or configuring alarm-based rollback. Triggers: create appconfig application, appconfig deployment strategy, appconfig configuration profile, appconfig feature flags, appconfig lambda validator, appconfig rollback on alarm, appconfig bake time, appconfig environment.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with appconfig access. Works with Terraform aws_appconfig_application / aws_appconfig_environment / aws_appconfig_configuration_profile / aws_appconfig_deployment_strategy / aws_appconfig_deployment / aws_appconfig_extension resources and CloudFormation AWS::AppConfig::Application / Environment / ConfigurationProfile / DeploymentStrategy / Deployment templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, appconfig, feature-flags, cloudops, deploy, provisioning, deployment-strategy, lambda-validator, rollback, configuration-profile
  dependencies: aws-orchestrator
  keywords: aws, appconfig, feature flags, cloudops, deploy, provisioning, deployment strategy, linear, exponential, all-at-once, bake time, cloudwatch alarm, lambda validator, rollback, configuration profile, schema validation
  when_to_use: Invoke when the user wants to create an AppConfig application, configure environments and configuration profiles, define deployment strategies (linear, exponential, all-at-once), set up feature flags, add Lambda validators for deployment validation, configure CloudWatch alarm-based rollback, manage configuration versions, or integrate AppConfig with Lambda and EventBridge. Do NOT invoke for AWS Systems Manager Parameter Store (use SSM skills), or for Secrets Manager (use secrets skills).
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
| references/advanced-patterns.md | Heuristics + integration + recent features |
| references/error-handling.md | Failure remedies |

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

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Growth factor (1-100), replicate, and bake time together define the safety envelope; bake > 0 enables CloudWatch alarm monitoring between steps.
The #1 cause of "my config broke production" is all-at-once with no bake time and no alarms — use linear/exponential with a meaningful bake and an error-rate alarm.

## Expert heuristic: validator lifecycle and alarm-based rollback

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Three safety layers: Lambda validator BEFORE deployment (blocks bad config), CloudWatch alarm + bake time DURING (auto-rollback), manual rollback AFTER completion.
A robust deployment has BOTH a validator and at least one alarm — skipping either removes a critical defense.

## Expert heuristic: feature flag schema vs free-form configuration

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Profile types AWS.Freeform / AWS.AppConfig.JSON / AWS.AppConfig.YAML; feature flags are Freeform profiles with a feature-flag schema URI enabling flag-level API operations.
Feature flags are NOT just JSON configurations — a standard JSON profile without the schema does NOT support flag-level operations.

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

CLI walkthrough: [deployment-strategies-and-alarms.md](references/deployment-strategies-and-alarms.md). create-deployment-strategy with --growth-factor, --growth-type LINEAR|EXPONENTIAL, --final-bake-time-in-minutes.
All-at-once (growth 100, bake 0) provides NO alarm monitoring — acceptable for non-critical configs, risky for production.

## Step 5 — Bake time and CloudWatch alarms

CLI walkthrough: [deployment-strategies-and-alarms.md](references/deployment-strategies-and-alarms.md). put-metric-alarm (e.g., 5XX error rate); alarm ARNs are specified at start-deployment and monitored during each bake window.
A bake time of 0 means NO alarm monitoring — always bake > 0 for production with at least one alarm.

## Step 6 — Lambda validators (deployment validation)

CLI walkthrough: [validators-and-feature-flags.md](references/validators-and-feature-flags.md). Attach via --validators Type=LAMBDA on the configuration profile.
Validators run on EVERY deployment of that profile; a failing validator blocks the deployment entirely.

## Step 7 — Feature flags and dynamic JSON schema

CLI walkthrough: [validators-and-feature-flags.md](references/validators-and-feature-flags.md). Feature flag schema (enabled/percentage attributes) plus JSON_SCHEMA validators on JSON/YAML profiles.
JSON schema catches structural errors at version creation; Lambda validators catch semantic errors at deployment — both are complementary.

## Step 8 — Configuration version management

CLI walkthrough: [deployment-strategies-and-alarms.md](references/deployment-strategies-and-alarms.md). create-hosted-configuration-version uploads immutable versioned content; list-hosted-configuration-versions enumerates it.
To update a configuration, create a NEW version and deploy it — old versions remain available for rollback.

## Step 9 — Rollback on alarm

CLI walkthrough: [deployment-strategies-and-alarms.md](references/deployment-strategies-and-alarms.md). start-deployment with strategy + version, then get-deployment to watch BAKING → DEPLOYING → COMPLETE.
If an alarm fires during BAKING the state becomes ROLLED_BACK automatically.

## Step 10 — Integration with Lambda and EventBridge

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). AppConfig Lambda extension (env-var config retrieval, no SDK calls) and EventBridge rules on "AppConfig Deployment State Change" events.
Trigger notifications or remediation functions on state changes, especially ROLLED_BACK.

## Step 11 — Recent features

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). AppConfig Agent (Lambda/ECS local HTTP interface), KMS for hosted configs, exponential growth type, deletion protection, Terraform extension resources, composite-alarm rollback (2023-2026).
Loaded on demand when the task calls for the newest capabilities.

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

Deep dive: [error-handling.md](references/error-handling.md). Remedies for the five common failure modes.
Validator-blocked deployments, automatic rollbacks, schema failures at version creation, stuck BAKING states, environment-not-found.

## References (load on demand)

- [Deployment strategies and alarms](references/deployment-strategies-and-alarms.md) — growth/bake-time parameters, strategy selection, CloudWatch alarm setup, version management, automatic rollback mechanics (Steps 4, 5, 8, 9 CLI walkthroughs in detail)
- [Validators and feature flags](references/validators-and-feature-flags.md) — Lambda validator functions and attachment, feature flag schema and management, JSON schema validation (Steps 6, 7 CLI walkthroughs in detail)
- [Advanced patterns](references/advanced-patterns.md) — strategy/validator/flag expert heuristics, Lambda + EventBridge integration (Step 10), recent AWS features 2023-2026 (Step 11)
- [Error handling](references/error-handling.md) — validator blocks, auto-rollback, schema failures, stuck BAKING, environment-not-found

## Domain

AWS CloudOps / AWS AppConfig Dynamic Configuration and Feature Flag
Provisioning.

## AWS documentation

- **AppConfig User Guide** — https://docs.aws.amazon.com/appconfig/latest/userguide/what-is-appconfig.html
- **Deployment strategies** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-deployment-strategy.html
- **Working with validators** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-profile-validator.html
- **Feature flags** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-storage.html
- **Rollback on alarm** — https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-rolling-back.html
