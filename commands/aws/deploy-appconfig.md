---
description: Provision AWS AppConfig resources with production-grade defaults (application, environments, configuration profiles, deployment strategies with linear/exponential/all-at-once growth, Lambda validators, feature flags, JSON schema validation, CloudWatch alarm-based rollback, configuration version management, Lambda/EventBridge integration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create appconfig application"
  - "deploy appconfig"
  - "appconfig deployment strategy"
  - "appconfig configuration profile"
  - "appconfig feature flags"
  - "appconfig lambda validator"
  - "appconfig rollback on alarm"
  - "appconfig bake time"
  - "appconfig environment"
  - "create feature flags"
  - "dynamic configuration"
  - "appconfig"
routes_to: appconfig-deployer
---

# /aws:deploy-appconfig

Activate the `appconfig-deployer` skill and provision AWS AppConfig
resources with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Application creation (top-level container)
2. Environments (dev, staging, production)
3. Configuration profiles (free form, JSON, YAML)
4. Deployment strategies (linear, exponential, all-at-once)
5. Bake time and CloudWatch alarms (safe rollout monitoring)
6. Lambda validators (pre-deployment validation)
7. Feature flags and dynamic JSON schema (flagged config)
8. Configuration version management (immutable versions)
9. Rollback on alarm (automated safety)
10. Integration with Lambda and EventBridge (event-driven)
11. Recent features (KMS encryption, exponential growth, agent)

## When to use

- You need to create an AppConfig application.
- You are defining a deployment strategy (linear, exponential, all-at-once).
- You need to set up configuration profiles (JSON, YAML, free form).
- You want to add Lambda validators for pre-deployment validation.
- You are setting up feature flags with dynamic JSON schema.
- You need CloudWatch alarm-based rollback during bake time.
- You want to integrate AppConfig with Lambda or EventBridge.

## When NOT to use

- **SSM Parameter Store** — different service for simple key-value
  parameters.
- **Secrets Manager** — for secrets, not dynamic configuration.
- **AWS Step Functions** — for workflow orchestration, not config.
- **Auditing existing AppConfig resources** — use AppConfig audit skills.

## How to invoke

### Slash command

```
/aws:deploy-appconfig
```

Then provide: application name, environment name, configuration
profile name and type, deployment strategy parameters (growth type,
growth factor, bake time), validator function ARN, CloudWatch alarm
ARNs, feature flag requirements, KMS key ARN (if encrypting), tags.

### Natural language

Any of these routes to the same skill:

- "create an AppConfig application with a linear deployment strategy"
- "set up AppConfig feature flags with exponential rollout"
- "configure CloudWatch alarm-based rollback for AppConfig"
- "add a Lambda validator to my AppConfig configuration profile"
- "create an AppConfig deployment strategy with bake time"

### CLI routing

```bash
node cli/bin/cli.js route "create an appconfig deployment"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create AppConfig
resources. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-appconfig

     Create an AppConfig application named my-app-config.
     Environment: production. Configuration profile: app-settings
     (JSON). Deployment strategy: linear, 20% growth, 10-minute
     bake. Attach a Lambda validator. Configure a CloudWatch alarm
     for rollback.

Skill:
  APPCONFIG: my-app-config / production
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Configuration profile: app-settings — JSON
    [✓] Deployment strategy: LINEAR growth=20% bake=10min
    [✓] Lambda validator: config-validator
    [✓] CloudWatch alarms: appconfig-deploy-error-rate
  VERIFICATION_COMMANDS:
    aws appconfig get-application --application-id <id>
    aws appconfig get-deployment-strategy --deployment-strategy-id <id>
```

## References

- Skill definition: `skills/appconfig-deployer/SKILL.md`
- Deployment strategies guide: `skills/appconfig-deployer/references/deployment-strategies-and-alarms.md`
- Validators and feature flags guide: `skills/appconfig-deployer/references/validators-and-feature-flags.md`
- Eval suite: `skills/appconfig-deployer/evals/evals.json`
