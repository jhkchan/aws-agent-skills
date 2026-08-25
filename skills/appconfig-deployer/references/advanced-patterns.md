# Advanced Patterns — AppConfig Deployer

Expert heuristics, integration patterns, and recent AWS features moved
verbatim from the SKILL.md body for progressive disclosure
(agentskills.io). Loaded on demand by the skill.

---

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
