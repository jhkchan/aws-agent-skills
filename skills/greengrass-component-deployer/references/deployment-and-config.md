# Deployment and Configuration Merge — Greengrass Component Deployer

Deep reference on deployment targeting (thing groups vs individual
things), configuration merge semantics (MERGE vs RESET, deep-merge
behavior), deployment policies (failure detection, component update,
validation), IoT role alias for Secrets Manager, and cloud-based vs
local deployment. Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## Deployment targeting

### Thing group vs individual thing

Greengrass v2 deployments target an ARN. The ARN can be a thing
group or an individual thing.

```text
Thing group ARN:
  arn:aws:iot:<region>:<account>:thinggroup/<group-name>

Individual thing ARN:
  arn:aws:iot:<region>:<account>:thing/<thing-name>
```

**Always use thing groups.** Even for a single device, a thing group
allows:

- Adding devices later without creating a new deployment.
- Configuration merge targeting the group.
- Fleet metrics aggregation by group.
- Rollback applied to the group.

### Thing group hierarchy

Thing groups support parent-child hierarchies. A deployment to a
parent group cascades to all child groups.

```bash
# Create parent group
aws iot create-thing-group --thing-group-name FactoryFloor

# Create child group under parent
aws iot create-thing-group \
  --thing-group-name LineA \
  --parent-group-name FactoryFloor

# Add devices to child group
aws iot add-thing-to-thing-group \
  --thing-name DeviceA1 \
  --thing-group-name LineA
```

**Deployment inheritance:** a deployment to `FactoryFloor` applies
to all devices in `LineA` (child). A deployment to `LineA` only
applies to devices in `LineA`. Child deployments override parent
deployments for the same component.

### Default deployment

When a new device joins a thing group that has an existing
deployment, Greengrass automatically applies that deployment to the
new device. This is the default deployment behavior — no manual
action needed.

```bash
# This deployment becomes the default for the thing group
# New devices joining MyDeviceGroup will automatically receive it
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{"com.example.MyComponent": {"componentVersion": "1.0.0"}}' \
  --region us-east-1
```

## Configuration merge semantics

### Three configuration layers

```text
Layer 1: Recipe DefaultConfiguration
  → defined in the recipe YAML
  → applies to ALL deployments of this component
  → baseline configuration

Layer 2: Deployment Configuration Merge
  → defined in the create-deployment API call
  → overrides defaults for THIS deployment's thing group
  → MERGE: deep-merges with existing config
  → RESET: resets specified keys to recipe defaults

Layer 3: Local Configuration (Greengrass CLI)
  → set on the device itself via greengrass-cli
  → overrides deployment merge for THIS device only
  → used for debugging and per-device tweaks

Effective configuration on the device = Layer 1 → Layer 2 → Layer 3
(each layer overrides the previous)
```

### MERGE: deep-merge behavior

MERGE deep-merges with existing configuration. Nested keys are
merged recursively, not replaced.

```bash
# Recipe default:
# { "logging": { "level": "info", "maxSizeMB": 10 } }

# Deployment merge:
"configurationUpdate": {
  "MERGE": "{\"logging\": {\"level\": \"debug\"}}"
}

# Result on device:
# { "logging": { "level": "debug", "maxSizeMB": 10 } }
# (maxSizeMB is preserved because merge is deep)
```

### RESET: revert to recipe defaults

RESET removes deployment overrides for specified keys, reverting
them to recipe defaults.

```bash
# Reset the logging.level key to its recipe default ("info")
"configurationUpdate": {
  "RESET": ["logging.level"]
}
```

### Combined MERGE and RESET

You can combine MERGE and RESET in the same deployment:

```bash
"configurationUpdate": {
  "MERGE": "{\"sampleRate\": 2000}",
  "RESET": ["logging.level"]
}
```

### Accessing configuration in lifecycle scripts

Configuration values are available in lifecycle scripts via the
`{configuration:/key}` syntax:

```bash
# Simple key
RATE={configuration:/sampleRate}

# Nested key
LOG_LEVEL={configuration:/logging/level}

# Boolean
ENABLE_COMPRESSION={configuration:/features/enableCompression}
```

### Configuration validation

Greengrass validates configuration updates on the device before
applying them. If validation fails, the deployment rolls back.

```bash
# Deployment with validation policy
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{
    "com.example.MyComponent": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "MERGE": "{\"sampleRate\": 2000}"
      }
    }
  }' \
  --deployment-policies '{
    "configurationValidationPolicy": {
      "timeoutInSeconds": 120
    },
    "failureDetectionPolicy": {
      "action": "ROLLBACK"
    }
  }'
```

## Deployment policies

### Failure detection policy

| Action | Behavior | When to use |
|---|---|---|
| ROLLBACK | Reverts to last known good deployment | Production (default) |
| DO_NOTHING | Leaves devices in current state | Debugging only |

```bash
# Production-safe deployment with rollback
--deployment-policies '{
  "failureDetectionPolicy": {
    "action": "ROLLBACK"
  }
}'
```

### Component update policy

| Action | Behavior |
|---|---|
| NOTIFY_COMPONENTS | Greengrass notifies all components to prepare for update (graceful) |
| SKIP_NOTIFY_COMPONENTS | Skips notification (immediate, may interrupt) |

```bash
# Graceful update with 120s timeout
--deployment-policies '{
  "componentUpdatePolicy": {
    "timeoutInSeconds": 120,
    "action": "NOTIFY_COMPONENTS"
  }
}'
```

## IoT role alias for Secrets Manager

### How it works

```text
1. Create IAM role with secretsmanager:GetSecretValue permission
2. Create IoT role alias that maps to the IAM role
3. Configure the IoT thing's role alias
4. Greengrass token exchange service provides temporary credentials
5. Components use credentials to access Secrets Manager

Flow:
  Component → Greengrass token exchange service → IoT credentials endpoint
  → IoT role alias → IAM role → Secrets Manager → secret value
```

### Setup

```bash
# 1. Create IAM role
aws iam create-role \
  --role-name GreengrassSecretAccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "credentials.iot.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 2. Attach Secrets Manager policy
aws iam put-role-policy \
  --role-name GreengrassSecretAccessRole \
  --policy-name SecretAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:*"
    }]
  }'

# 3. Create IoT role alias
aws iot create-role-alias \
  --role-alias GreengrassSecretAlias \
  --role-arn arn:aws:iam::123456789012:role/GreengrassSecretAccessRole \
  --credential-duration-seconds 3600
```

### Component accessing secrets

In the component recipe, reference the secret ID and use the AWS CLI
or SDK to fetch it. Greengrass automatically provides credentials
via environment variables:

```yaml
ComponentConfiguration:
  DefaultConfiguration:
    secretId: "my-database-credentials"

Manifests:
  - Lifecycle:
      Startup:
        Script: |
          # Greengrass sets AWS_CONTAINER_CREDENTIALS_FULL_URI
          # The AWS SDK/CLI automatically uses these credentials
          SECRET=$(aws secretsmanager get-secret-value \
            --secret-id {configuration:/secretId} \
            --query SecretString --output text \
            --region us-east-1)
          echo "Got secret (length: ${#SECRET})"
```

## Cloud-based vs local deployment

### Cloud-based deployment (production)

```bash
# From AWS cloud — pushes to all devices in the thing group
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{"com.example.MyComponent": {"componentVersion": "1.0.0"}}' \
  --region us-east-1
```

**Characteristics:**
- Centralized control from AWS cloud.
- Components fetched from S3 via token exchange role.
- Deployment status tracked in AWS (get-deployment API).
- Supports rollback, configuration merge, deployment policies.
- Asynchronous — takes minutes depending on device connectivity.

### Local deployment (development)

```bash
# On the core device itself — immediate, no cloud round-trip
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --merge "com.example.MyComponent=1.0.0" \
  --recipeDir /home/user/recipes \
  --artifactsDir /home/user/artifacts

# Check status
sudo /greengrass/v2/bin/greengrass-cli deployment status

# Remove a component locally
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --remove "com.example.MyComponent"
```

**Characteristics:**
- Immediate — no cloud round-trip.
- Uses local recipe and artifact files (not S3).
- No deployment policies (no rollback).
- Overridden by the next cloud-based deployment.
- Used for development, debugging, and air-gapped devices.

### When to use which

| Scenario | Mode |
|---|---|
| Production deployment | Cloud-based |
| Fleet rollout | Cloud-based (thing group) |
| Development / debugging | Local (fast iteration) |
| Air-gapped device | Local (no cloud connectivity) |
| Testing a new recipe | Local (validate before cloud publish) |

## Deployment job lifecycle

```text
Deployment job states:
  CREATED → IN_PROGRESS → COMPLETED
                       → FAILED (rollback triggered if ROLLBACK policy)

  CREATED:       deployment job created, not yet sent to devices
  IN_PROGRESS:   deployment sent to devices, devices processing
  COMPLETED:     all devices successfully deployed
  FAILED:        one or more devices failed; ROLLBACK reverts them
```

Monitor deployment status:

```bash
# Check deployment status
aws greengrassv2 get-deployment \
  --deployment-id "$DEPLOYMENT_ID" \
  --region us-east-1

# List recent deployments for a target
aws greengrassv2 list-deployments \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --region us-east-1

# Check per-device deployment status
aws iot get-thing-shadow \
  --thing-name MyCoreDevice \
  --shadow-name AWSManagedGreengrassV2Deployment \
  --region us-east-1
```

## Terraform deployment example

```hcl
resource "aws_greengrass_deployment" "prod" {
  target_arn    = "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup"
  deployment_name = "Deploy MyComponent 1.0.0"

  components {
    key   = "com.example.MyComponent"
    value {
      component_version = "1.0.0"

      configuration_update {
        merge = jsonencode({
          sampleRate = 2000
          logging    = { level = "debug" }
        })
      }
    }
  }

  deployment_policies {
    failure_detection_policy {
      action = "ROLLBACK"
    }
    component_update_policy {
      timeout_in_seconds = 120
      action              = "NOTIFY_COMPONENTS"
    }
  }
}
```

## Step 5 — Deployment to thing group — moved from SKILL.md

Deployments target thing GROUPS, not individual devices. A thing
group can contain one or more IoT things (core devices).

**Create a thing group:**

```bash
aws iot create-thing-group \
  --thing-group-name MyDeviceGroup \
  --region us-east-1
```

**Add a thing to the group:**

```bash
aws iot add-thing-to-thing-group \
  --thing-name MyCoreDevice \
  --thing-group-name MyDeviceGroup \
  --region us-east-1
```

**Create a deployment:**

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --deployment-name "Deploy MyComponent 1.0.0" \
  --components '{
    "com.example.MyComponent": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "MERGE": "{\"message\": \"Hello from deployment\"}"
      }
    }
  }' \
  --deployment-policies '{
    "componentUpdatePolicy": {
      "timeoutInSeconds": 60,
      "action": "NOTIFY_COMPONENTS"
    },
    "configurationValidationPolicy": {
      "timeoutInSeconds": 60
    },
    "failureDetectionPolicy": {
      "action": "ROLLBACK"
    }
  }' \
  --region us-east-1
```

**Verify deployment status:**

```bash
DEPLOYMENT_ID="<deployment-id from create-deployment output>"

aws greengrassv2 get-deployment \
  --deployment-id "$DEPLOYMENT_ID" \
  --region us-east-1
# Expected: deploymentStatus: ACTIVE, COMPLETED
```

**Deployment policies:**

| Policy | Options | Default |
|---|---|---|
| ComponentUpdatePolicy | NOTIFY_COMPONENTS (graceful), SKIP_NOTIFY_COMPONENTS (immediate) | NOTIFY_COMPONENTS with 60s timeout |
| ConfigurationValidationPolicy | timeoutInSeconds for validation | 60s |
| FailureDetectionPolicy | ROLLBACK (revert on failure), DO_NOTHING | ROLLBACK |

## Step 6 — Configuration merge — moved from SKILL.md

Configuration merge allows per-deployment customization of component
parameters. The recipe defines default configuration; the deployment
can merge overrides.

**Recipe default configuration:**

```yaml
ComponentConfiguration:
  DefaultConfiguration:
    message: "Hello from Greengrass"
    interval: 5
    logging:
      level: "info"
      path: "/var/log/my-component"
```

**Deployment configuration merge:**

```bash
# Override message and logging.level for this deployment
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{
    "com.example.MyComponent": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "MERGE": "{\"message\": \"Custom message for this group\", \"logging\": {\"level\": \"debug\"}}"
      }
    }
  }' \
  --region us-east-1
```

**Merge semantics:**

- MERGE: Deep-merges with existing configuration (nested keys are
  merged, not replaced).
- RESET: Resets specified keys to recipe defaults (removes deployment
  overrides).

```bash
# Reset message to recipe default
"configurationUpdate": {
  "RESET": ["message"]
}
```

**Accessing configuration in lifecycle scripts:**

```bash
# In a lifecycle script, reference configuration via {configuration:/key}
Script: |
  MESSAGE={configuration:/message}
  INTERVAL={configuration:/interval}
  echo "$MESSAGE at interval $INTERVAL"
```
