---
name: greengrass-component-deployer
description: >-
  Deploys AWS IoT Greengrass v2 components with production defaults:
  component recipe YAML (lifecycle hooks: install, startup, shutdown),
  component versioning (semantic versioning, bump on recipe change),
  artifact storage (S3 bucket + presigned URLs), component dependencies
  (HARD vs SOFT dependency types), deployment to thing group (not
  individual devices), configuration merge (runtime parameters for
  per-device customization), IoT role alias for Secrets Manager access,
  Lambda functions as components (aws.lambda component dependency),
  Docker containers as components (aws.greengrass.DockerApplicationManager
  + aws.docker.Login), local volume mounts (docker volume / bind mount),
  cloud-based deployment vs local deployment (default deployment vs
  deployment job), and core device setup (Greengrass CLI, token exchange
  role). Emits a READY_TO_DEPLOY checklist with verification commands.
  Use when creating a Greengrass component, deploying to a thing group,
  packaging an artifact, writing a recipe, configuring a Lambda as a
  component, running a Docker container on the edge, or setting up
  secret manager integration. Triggers: create greengrass component,
  deploy greengrass component, greengrass recipe yaml, greengrass
  deployment thing group, greengrass configuration merge, greengrass
  lambda component, greengrass docker component, greengrass secret
  manager, greengrass core device setup, greengrass component version.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with greengrassv2
  and s3 access, plus IoT things/thing groups provisioned. Works with
  Terraform aws_greengrass_component_definition /
  aws_greengrass_deployment resources and CloudFormation
  AWS::GreengrassV2::Component / AWS::GreengrassV2::Deployment templates.
keywords:
  - aws
  - greengrass
  - greengrass v2
  - iot
  - edge
  - component
  - recipe
  - cloudops
  - deploy
  - provisioning
  - thing group
  - lifecycle
  - artifact
  - lambda
  - docker
  - secret manager
  - configuration merge
  - core device
tags:
  - aws
  - greengrass
  - greengrass-v2
  - iot
  - edge
  - cloudops
  - deploy
  - provisioning
  - component
  - recipe
  - lifecycle
  - lambda
  - docker
  - thing-group
  - configuration-merge
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - greengrass
    - greengrass-v2
    - iot
    - edge
    - cloudops
    - deploy
    - provisioning
    - component
    - recipe
    - lifecycle
    - lambda
    - docker
    - thing-group
    - configuration-merge
  dependencies:
    - aws-orchestrator
  keywords:
    - create greengrass component
    - deploy greengrass component
    - greengrass recipe yaml
    - greengrass deployment thing group
    - greengrass configuration merge
    - greengrass lambda component
    - greengrass docker component
    - greengrass secret manager
    - greengrass core device setup
    - greengrass component version
  when_to_use: >-
    Invoke when the user wants to create or deploy an AWS IoT Greengrass
    v2 component, write a component recipe with lifecycle hooks, store
    component artifacts in S3, manage component dependencies (hard vs
    soft), deploy a component to a thing group, use configuration merge
    for per-device runtime parameters, integrate Secrets Manager via IoT
    role alias, run a Lambda function as a component, run a Docker
    container as a component, configure local volume mounts, or set up
    a Greengrass core device. Do NOT invoke for Greengrass v1 (use v1
    skills), AWS IoT Core device management (no Greengrass), or AWS
    Panorama (different edge runtime).
---

# Greengrass Component Deployer

An AWS CloudOps agent skill that deploys AWS IoT Greengrass v2
components with correct defaults. The skill walks the operator
through component recipe creation (lifecycle hooks), versioning,
artifact storage (S3), dependency management (hard vs soft),
deployment targeting (thing groups, NOT individual devices),
configuration merge (runtime parameters), secret manager integration
via IoT role alias, Lambda and Docker as components, local volume
mounts, cloud-based vs local deployment, and core device setup,
captures all provisioning decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Greengrass component, deploy Greengrass component, Greengrass
recipe YAML, Greengrass deployment thing group, Greengrass
configuration merge, Greengrass Lambda component, Greengrass Docker
component, Greengrass secret manager, Greengrass core device setup,
Greengrass component version.

## STRICT output contract

When this skill is invoked with a Greengrass v2 component deployment
request (create a component, deploy to thing group, write a recipe,
package an artifact, configure Lambda or Docker as a component, set
up secrets, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `GREENGRASS_COMPONENT:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT
preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Component recipe (lifecycle hooks) | Core recipe model |
| Step 2 — Component versioning | Semantic versioning rules |
| Step 3 — Artifact storage (S3) | Artifact packaging |
| Step 4 — Component dependencies (hard vs soft) | Dependency chain |
| Step 5 — Deployment to thing group | Deployment targeting |
| Step 6 — Configuration merge | Per-device customization |
| Step 7 — Secret manager integration (IoT role alias) | Secrets on edge |
| Step 8 — Lambda as component | Lambda runtime on edge |
| Step 9 — Docker as component | Container runtime on edge |
| Step 10 — Local volume mount | Persistent storage on edge |
| Step 11 — Cloud-based vs local deployment | Deployment modes |
| Step 12 — Core device setup | Device prerequisites |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/recipe-and-lifecycle.md | Recipe + lifecycle detail |
| references/deployment-and-config.md | Deployment + config merge detail |

## Mindset

**One-line takeaway:** A Greengrass v2 component is a software
module that runs on an edge device. The component recipe defines
lifecycle hooks (install, startup, shutdown) as shell scripts.
Configuration merge allows per-device customization of runtime
parameters. Deployments target thing GROUPS, not individual devices
— use a thing group even for a single device so you can add devices
later without re-architecting.

Three misconceptions dominate Greengrass v2 misdesign at provisioning
time:

- **"Deploy the component to a single device."** While technically
  possible, Greengrass v2 deployments should target thing GROUPS, not
  individual devices. A thing group allows you to add or remove devices
  without modifying the deployment. If you deploy to a single thing
  and later need to add a second device, you must create a new
  deployment. Always create a thing group (even with one device) and
  target the group.

- **"The recipe lifecycle section is optional."** It is NOT. The
  lifecycle section defines what happens at install, startup, and
  shutdown. Without lifecycle hooks, the component is a no-op — it
  installs but does nothing. Every component MUST have at least a
  startup hook. The install hook downloads/extracts artifacts; the
  startup hook runs the component logic; the shutdown hook cleans up.

- **"Configuration merge is just default configuration."** It is NOT.
  Default configuration (in the recipe) applies to ALL deployments.
  Configuration merge is a deployment-level override that applies to
  a SPECIFIC deployment (and thus a specific thing group). This allows
  per-device or per-group customization without modifying the recipe.
  For example, the recipe defines `port: 8080` as default, and a
  deployment to a specific thing group merges `port: 8081` to override
  for that group.

## Configuration dependency graph (novel heuristic)

Greengrass v2 component configurations are NOT independent. The
recipe must exist before the component can be created. Artifacts
must be uploaded to S3 before the component version references them.
The core device must be provisioned and running before deployment.
The thing group must exist before the deployment targets it. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Component recipe | recipe YAML with lifecycle hooks; manifest with artifacts | recipe MUST reference S3 URIs for artifacts; local paths fail on remote devices | component version (ARN) |
| Component version | recipe YAML uploaded; artifact S3 URIs valid | version bump REQUIRED on recipe change; same version = no update | deployment target |
| S3 artifacts | S3 bucket exists; artifact uploaded; Greengrass token exchange role has s3:GetObject | presigned URLs NOT used by Greengrass; it uses the token exchange role to access S3 | artifact download on device |
| Thing group | IoT things exist; thing group created | thing group can be empty at deploy time but components won't run until devices join | deployment target |
| Deployment | component version exists; thing group exists; core devices running | deployment job is asynchronous; components deploy over minutes | component execution on devices |
| Configuration merge | deployment exists | merge keys MUST match the recipe's configuration schema; mismatched keys are silently ignored | per-device runtime parameters |
| IoT role alias | IAM role with secretsmanager:GetSecretValue; IoT role alias maps to the role; component references alias via SECRET_MANAGER_ROLE_ALIAS env var | the token exchange service rotates credentials automatically; no manual rotation needed | secret access on edge |
| Lambda component | aws.lambda artifact (ZIP); aws.lambda component version deployed as dependency; Lambda runtime specified in recipe | the Lambda ISO runtime is downloaded by the aws.lambda component, not bundled | Lambda execution on edge |
| Docker component | aws.greengrass.DockerApplicationManager deployed; aws.docker.Login for private registries; Docker image accessible | Docker daemon must be running on the core device; image pulled at startup, not install | container execution on edge |
| Core device | Greengrass v2 installed; token exchange role configured; IoT thing provisioned | core device MUST have the Greengrass CLI for local debugging | component deployment target |

**The configuration-merge row is the one a baseline model misses.**
Default configuration in the recipe applies to all deployments.
Configuration merge is a deployment-level override that allows per-
group customization. The procedure below forces an explicit decision
on whether merge is needed.

**Cross-dependency gotchas:**
- Component version must be bumped on EVERY recipe change. Creating
  a component version with the same semantic version as an existing
  one silently does nothing (no update deployed).
- Artifacts are referenced by S3 URI in the recipe manifest, and
  Greengrass uses the token exchange role (NOT presigned URLs) to
  download them. The role must have `s3:GetObject` on the artifact
  bucket.
- Lambda components require the `aws.lambda` component as a HARD
  dependency. Without it, the Lambda runtime is not available on the
  device.
- Docker components require `aws.greengrass.DockerApplicationManager`
  as a HARD dependency. Without it, Docker image management is not
  available.
- The thing group should be created BEFORE the deployment, even if
  empty. Devices can join later and automatically receive the
  deployment.

## Expert heuristic: recipe lifecycle hooks define everything

A baseline model says "write a recipe." The correct heuristic
recognizes that lifecycle hooks are the heart of the recipe. Each
hook is a shell command that runs at a specific lifecycle stage.

```text
Component lifecycle stages:
  Install  → runs ONCE when component is first deployed (or on version update)
             typically: extract artifacts, install dependencies, create directories
  Startup  → runs EVERY TIME the component starts (device boot, restart, recovery)
             typically: run the main logic, start a process, launch a server
  Shutdown → runs when the component stops (undeploy, device shutdown, update)
             typically: kill processes, flush buffers, release resources
  Recover  → OPTIONAL: runs if startup fails
             typically: retry logic, fallback behavior

Recovery timeout: if a startup script does not exit within 60s (default),
Greengrass considers the component failed and runs the recover hook.
```

**Key implication:** the startup hook should be a long-running
process (a daemon, a server, a loop). If the startup script exits
immediately, Greengrass considers the component "errored" and
repeatedly restarts it. For one-shot scripts, use the install hook
instead.

## Expert heuristic: thing group vs individual device targeting

A baseline model says "deploy to the device." The correct heuristic
recognizes that thing groups are the deployment target abstraction.

```text
Deployment targeting decision:
  ├── Single device, will never scale → thing group with 1 member (still recommended)
  ├── Single device, will scale later → thing group (add members later)
  ├── Multiple devices, same config   → thing group (single deployment)
  ├── Multiple devices, different config → thing group + configuration merge per subgroup
  └── Fleet-wide canary rollout       → thing group hierarchy (parent → child groups)

Why thing group even for 1 device:
  ├── Add devices later without creating a new deployment
  ├── Rollback applies to the group (not per-device)
  ├── Configuration merge targets the group
  └── Fleet metrics aggregate by group
```

**Key implication:** always create a thing group for deployment
targeting, even for a single device. This avoids re-architecting
when scaling.

## Expert heuristic: configuration merge vs default configuration

A baseline model says "put all config in the recipe." The correct
heuristic recognizes that configuration has two layers: default (in
recipe) and merge (in deployment).

```text
Configuration layers (later overrides earlier):
  1. Recipe default configuration → applies to ALL deployments of this component
  2. Deployment configuration merge → overrides defaults for THIS deployment's thing group
  3. Local configuration (Greengrass CLI) → overrides deployment merge for THIS device only

Example:
  Recipe default:     { port: 8080, logLevel: "info" }
  Deployment merge:   { port: 8081 }              ← overrides port for this group
  Local override:     { logLevel: "debug" }       ← overrides logLevel for this device only

Effective config on device: { port: 8081, logLevel: "debug" }
```

**Key implication:** use recipe defaults for baseline behavior and
configuration merge for per-group customization. This lets you deploy
the same component version to different groups with different
configurations.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 bucket for artifacts | Component artifacts stored in S3 | `aws s3 ls s3://<bucket>` |
| Token exchange role with s3:GetObject | Greengrass core device downloads artifacts via this role | Check IAM role policy |
| IoT thing exists | Core device registered as IoT thing | `aws iot describe-thing --thing-name <name>` |
| Thing group exists | Deployment targets thing groups | `aws iot describe-thing-group --thing-group-name <name>` |
| Core device running Greengrass v2 | Component runs on the core device | `aws greengrassv2 list-core-devices` |
| Component recipe with lifecycle hooks | Recipe defines install/startup/shutdown | Validate YAML structure |
| Component version bumped | Same version = no update deployed | Check existing component versions |
| Lambda runtime (if Lambda component) | aws.lambda component must be a dependency | Verify dependency in recipe |
| Docker ApplicationManager (if Docker) | Required for Docker image management | Verify dependency in recipe |
| IoT role alias (if secrets) | Maps IAM role for Secrets Manager access | `aws iot describe-role-alias --role-alias <name>` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Component recipe (lifecycle hooks)

The component recipe is a YAML file that defines the component's
metadata, lifecycle hooks, artifacts, and configuration schema.

**Minimal recipe structure:**

```yaml
---
RecipeFormatVersion: "2020-01-25"
ComponentName: com.example.MyComponent
ComponentVersion: "1.0.0"
ComponentDescription: "My first Greengrass component"
ComponentPublisher: Example
ComponentConfiguration:
  DefaultConfiguration:
    message: "Hello from Greengrass"
    interval: 5
Manifests:
  - Name: "linux-amd64"
    Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: s3://my-bucket/artifacts/my-script.py
        Unarchive: NONE
    Lifecycle:
      Install:
        Script: |
          mkdir -p {artifacts:decompressedPath}/my-component
          cp {artifacts:path}/my-script.py {artifacts:decompressedPath}/my-component/
      Startup:
        Script: |
          python3 {artifacts:decompressedPath}/my-component/my-script.py
      Shutdown:
        Script: |
          echo "Shutting down MyComponent"
```

**Lifecycle hook precedence:**

| Hook | When it runs | Exit code 0 | Exit code non-zero |
|---|---|---|---|
| Install | On first deploy or version update | Component proceeds to Startup | Component deployment fails |
| Startup | After install, on device boot, on restart | Component is RUNNING (stays running) | Component enters ERRORED state; recover hook runs |
| Shutdown | On undeploy, device shutdown, version update | Clean stop | Force kill after timeout |
| Recover | If startup fails (optional) | Component retries startup | Component stays ERRORED |

**Artifact path variables:**

| Variable | Expands to |
|---|---|
| `{artifacts:path}` | Path to the artifact as downloaded (file or directory) |
| `{artifacts:decompressedPath}` | Path to the decompressed artifact (for ZIP/TAR archives) |
| `{work:path}` | Component work directory (persistent, per-component) |
| `{configuration:/<key>}` | Configuration value for the given key |

## Step 2 — Component versioning

Greengrass v2 components use semantic versioning (`MAJOR.MINOR.PATCH`).
Every recipe change requires a version bump. Creating a component
version with the same version as an existing one is a no-op.

**Version bump rules:**

| Change type | Version bump | Example |
|---|---|---|
| Bug fix, no new features | PATCH | 1.0.0 → 1.0.1 |
| New feature, backward-compatible | MINOR | 1.0.1 → 1.1.0 |
| Breaking change | MAJOR | 1.1.0 → 2.0.0 |
| Recipe lifecycle change | MINOR or MAJOR | 1.1.0 → 1.2.0 |
| Artifact update only | PATCH | 1.1.0 → 1.1.1 |

**Create a component version:**

```bash
# Upload the recipe to S3 (or use inline)
aws greengrassv2 create-component-version \
  --inline-recipe fileb://recipe.yaml \
  --region us-east-1

# Or from S3
aws greengrassv2 create-component-version \
  --lambda-function '{"lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:my-func:1", "componentName": "com.example.MyLambda", "componentVersion": "1.0.0"}' \
  --region us-east-1
```

**Verify component version created:**

```bash
aws greengrassv2 describe-component \
  --arn "arn:aws:greengrass:us-east-1:123456789012:components:com.example.MyComponent:versions:1.0.0" \
  --region us-east-1
```

## Step 3 — Artifact storage (S3)

Component artifacts (scripts, binaries, models, archives) are stored
in S3. The recipe references them by S3 URI. Greengrass uses the
token exchange role on the core device to download artifacts (NOT
presigned URLs).

**Upload artifact to S3:**

```bash
aws s3 cp my-script.py s3://my-greengrass-artifacts/artifacts/com.example.MyComponent/1.0.0/my-script.py \
  --region us-east-1
```

**Token exchange role policy (must include s3:GetObject):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::my-greengrass-artifacts/*"
    }
  ]
}
```

**Artifact archive types:**

| Unarchive value | When to use |
|---|---|
| NONE | Single file (script, binary) |
| ZIP | Multiple files compressed as ZIP |
| TAR | Multiple files compressed as TAR |
| TAR_GZ | Multiple files compressed as TAR.GZ |

For ZIP/TAR archives, use `{artifacts:decompressedPath}` in lifecycle
scripts to reference the extracted files.

## Step 4 — Component dependencies (hard vs soft)

Components can depend on other components. There are two dependency
types:

| Dependency type | Behavior | Use case |
|---|---|---|
| HARD | If dependency fails, THIS component also fails | Required runtime (e.g., aws.lambda for Lambda components) |
| SOFT | If dependency fails, THIS component still starts | Optional features (e.g., a logging component) |

**Recipe with dependencies:**

```yaml
ComponentDependencies:
  - DependencyType: HARD
    ComponentRequire:
      ThingName: aws.lambda
      Version: "2.3.0"
  - DependencyType: SOFT
    ComponentRequire:
      ThingName: com.example.Logging
      Version: "1.0.0"
```

**Dependency resolution order:**

Greengrass resolves dependencies in topological order. HARD
dependencies are installed and started BEFORE the dependent
component. SOFT dependencies are started before but do not block.

## Step 5 — Deployment to thing group

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

## Step 6 — Configuration merge

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

## Step 7 — Secret manager integration (IoT role alias)

Greengrass components can access AWS Secrets Manager secrets via an
IoT role alias. The role alias maps an IoT credential to an IAM role
that has `secretsmanager:GetSecretValue` permission.

**Create IAM role for secret access:**

```bash
aws iam create-role \
  --role-name GreengrassSecretAccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "credentials.iot.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach Secrets Manager policy
aws iam put-role-policy \
  --role-name GreengrassSecretAccessRole \
  --policy-name SecretAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:*"
      }
    ]
  }'
```

**Create IoT role alias:**

```bash
aws iot create-role-alias \
  --role-alias MySecretRoleAlias \
  --role-arn arn:aws:iam::123456789012:role/GreengrassSecretAccessRole \
  --credential-duration-seconds 3600 \
  --region us-east-1
```

**Recipe referencing the role alias:**

```yaml
ComponentConfiguration:
  DefaultConfiguration:
    secretManagerRoleAlias: "MySecretRoleAlias"
    secretId: "my-database-credentials"

Manifests:
  - Lifecycle:
      Startup:
        Script: |
          # Greengrass automatically provides AWS credentials via the
          # IoT role alias. Access the secret using the AWS CLI or SDK.
          aws secretsmanager get-secret-value \
            --secret-id {configuration:/secretId} \
            --query SecretString --output text
```

**Critical:** the IoT role alias credential provider runs on the
core device and automatically rotates credentials. The component
does NOT need to manage credentials manually. Greengrass sets the
`AWS_CONTAINER_AUTHORIZATION_TOKEN` and `AWS_CONTAINER_CREDENTIALS_FULL_URI`
environment variables for the component.

## Step 8 — Lambda as component

Lambda functions can run on Greengrass core devices as components.
The `aws.lambda` component (managed by AWS) provides the Lambda
runtime on the edge device.

**Create Lambda component from function ARN:**

```bash
aws greengrassv2 create-component-version \
  --lambda-function '{
    "lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:my-edge-function:3",
    "componentName": "com.example.MyEdgeLambda",
    "componentVersion": "1.0.0",
    "componentPlatforms": [{"name": "Linux amd64", "attributes": {"os": "linux", "architecture": "amd64"}}]
  }' \
  --region us-east-1
```

**Recipe with Lambda dependency:**

```yaml
ComponentDependencies:
  - DependencyType: HARD
    ComponentRequire:
      ThingName: aws.lambda
      Version: "2.3.0"
```

**Lambda component configuration:**

| Parameter | Description | Default |
|---|---|---|
| lambdaExecutionParameters | Event sources, environment variables, timeout | N/A |
| maxInstances | Max concurrent instances on device | 0 (unlimited) |
| maxQueueSize | Max event queue size | 1000 |
| pinned | Whether the function is long-lived (true) or event-driven (false) | true |

**Example deployment with Lambda component:**

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{
    "com.example.MyEdgeLambda": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "MERGE": "{\"lambdaExecutionParameters\": {\"environmentVariables\": {\"LOG_LEVEL\": \"debug\"}}}"
      }
    },
    "aws.lambda": {
      "componentVersion": "2.3.0"
    }
  }' \
  --region us-east-1
```

## Step 9 — Docker container as component

Docker containers can run on Greengrass core devices as components.
The `aws.greengrass.DockerApplicationManager` component manages
Docker images (pull, run, stop).

**Prerequisites:**
- Docker must be installed and running on the core device.
- `aws.greengrass.DockerApplicationManager` must be deployed as a
  dependency.
- For private registries, use `aws.docker.Login` to authenticate.

**Recipe for Docker component:**

```yaml
---
RecipeFormatVersion: "2020-01-25"
ComponentName: com.example.MyDockerComponent
ComponentVersion: "1.0.0"
ComponentPublisher: Example
ComponentDependencies:
  - DependencyType: HARD
    ComponentRequire:
      ThingName: aws.greengrass.DockerApplicationManager
      Version: "2.0.0"
Manifests:
  - Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: "docker:nginx:latest"
        ArtifactType: DOCKER
    Lifecycle:
      Startup: |
        docker run -d --name my-nginx -p 8080:80 nginx:latest
      Shutdown: |
        docker stop my-nginx && docker rm my-nginx
```

**Private registry login component:**

```yaml
ComponentName: aws.docker.Login
ComponentVersion: "2.0.0"
# This is a managed AWS component — reference it as a dependency
# alongside DockerApplicationManager if using private registries
```

**Deploy Docker component:**

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{
    "com.example.MyDockerComponent": {
      "componentVersion": "1.0.0"
    },
    "aws.greengrass.DockerApplicationManager": {
      "componentVersion": "2.0.0"
    }
  }' \
  --region us-east-1
```

## Step 10 — Local volume mount

Docker components can mount local directories (volumes) on the edge
device for persistent storage.

**Recipe with volume mount:**

```yaml
Manifests:
  - Lifecycle:
      Startup: |
        docker run -d \
          --name my-data-processor \
          -v /greengrass/v2/work/com.example.MyDockerComponent/data:/data \
          -v /greengrass/v2/work/com.example.MyDockerComponent/config:/config \
          my-data-processor:latest
```

**Volume mount best practices:**

| Mount path | Purpose | Persistence |
|---|---|---|
| `{work:path}/data` | Component work directory | Persists across component restarts; cleared on undeploy |
| `/greengrass/v2/work/<component>/data` | Same as work:path | Same |
| Host path (e.g., `/mnt/data`) | External storage | Persists across undeploy (device-level) |

**Critical:** use `{work:path}` for component-scoped storage. This
ensures the path is unique per component and managed by Greengrass.
Hardcoded host paths (e.g., `/mnt/data`) require the path to exist
on the device.

## Step 11 — Cloud-based deployment vs local deployment

Greengrass v2 supports two deployment modes:

| Mode | How it works | When to use |
|---|---|---|
| Cloud-based (default) | Deploy via AWS cloud (create-deployment API). Components pushed from cloud to device. | Production, fleet management, centralized control |
| Local deployment | Deploy via Greengrass CLI on the device itself. Components run locally without cloud round-trip. | Development, debugging, air-gapped devices |

**Cloud-based deployment (production):**

```bash
# From the cloud (AWS CLI or console)
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{"com.example.MyComponent": {"componentVersion": "1.0.0"}}' \
  --region us-east-1
```

**Local deployment (development):**

```bash
# On the core device, using Greengrass CLI
# Deploy a local component for testing
sudo /greengrass/v2/bin/greengrass-cli deployment create \
  --merge "com.example.MyComponent=1.0.0" \
  --recipeDir /path/to/recipes \
  --artifactsDir /path/to/artifacts

# Check local deployment status
sudo /greengrass/v2/bin/greengrass-cli deployment status
```

**Default deployment (thing group default):**

A default deployment is a deployment that Greengrass automatically
applies to new devices when they join a thing group. This ensures
new devices get the correct component set without manual
intervention.

```bash
# Create a thing group with a default deployment
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/MyDeviceGroup" \
  --components '{"com.example.MyComponent": {"componentVersion": "1.0.0"}}' \
  --deployment-name "Default deployment for MyDeviceGroup" \
  --region us-east-1
```

## Step 12 — Core device setup

The core device must have Greengrass v2 installed and configured.

**Install Greengrass v2 on a Linux device:**

```bash
# Download the Greengrass installer
curl -s https://d2s8p88vqu9w66.cloudfront.net/releases/greengrass-nucleus-latest.zip \
  -o greengrass-nucleus-latest.zip
unzip greengrass-nucleus-latest.zip -d GreengrassInstaller

# Install Greengrass core (requires AWS credentials with provisioning permissions)
sudo java -Droot="/greengrass/v2" \
  -Dlog.store=FILE \
  -jar ./GreengrassInstaller/lib/Greengrass.jar \
  --aws-region us-east-1 \
  --thing-name MyCoreDevice \
  --thing-group-name MyDeviceGroup \
  --thing-policy-name GreengrassV2IoTThingPolicy \
  --tes-role-name GreengrassV2TokenExchangeRole \
  --tes-role-alias-name GreengrassV2TokenExchangeRoleAlias \
  --component-default-user ggc_user:ggc_group \
  --provision true \
  --setup-system-service true
```

**Verify core device is registered:**

```bash
aws greengrassv2 list-core-devices \
  --region us-east-1 \
  --query "coreDevices[?coreDeviceThingName=='MyCoreDevice']"
# Expected: coreDeviceStatus: HEALTHY
```

**Token exchange role (auto-created during provisioning):**

The installer creates a token exchange role that allows the core
device to interact with AWS services (S3, Secrets Manager, IoT).
This role needs additional policies for:
- `s3:GetObject` on artifact buckets
- `secretsmanager:GetSecretValue` for secret access
- `iot:*` for IoT operations

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **Greengrass v2 component management APIs (2023-2024):** Enhanced
  APIs for component version management, including batch operations
  for large fleets. The create-component-version API now supports
  inline recipes and Lambda function conversion.

- **Docker container improvements (2023-2024):** The
  aws.greengrass.DockerApplicationManager component now supports
  multi-architecture images and private registry authentication
  via aws.docker.Login with credential rotation.

- **Configuration merge validation (2023-2024):** Configuration
  validation policies now support custom validation scripts that
  run on the device before applying configuration changes. This
  prevents invalid configurations from breaking components.

- **Stream manager enhancements (2023-2024):** The Greengrass stream
  manager now supports data prioritization and batch flushing,
  improving real-time data processing on edge devices.

- **Fleet provisioning by claim (2023-2024):** Enhanced fleet
  provisioning flows allow devices to self-provision using a claim
  certificate, reducing manual device setup for large fleets.

- **CloudWatch metrics for Greengrass (2024-2025):** Automatic
  CloudWatch metric emission for component lifecycle events
  (install, startup, shutdown, error), enabling fleet-wide
  observability without custom instrumentation.

- **Greengrass CLI local deployment improvements (2024-2025):**
  The local CLI now supports component recipe validation before
  deployment, catching recipe errors before they reach the device.

## NEVER do these things

1. **NEVER deploy to an individual device when a thing group exists.**
   Deployments should target thing GROUPS, not individual devices.
   Even for a single device, create a thing group and target it.
   This allows scaling without re-architecting.

2. **NEVER skip the version bump on recipe changes.** Creating a
   component version with the same semantic version as an existing
   one is a no-op. The deployment will not update. Always bump the
   version on EVERY recipe or artifact change.

3. **NEVER use presigned URLs for artifacts.** Greengrass uses the
   token exchange role on the core device to download S3 artifacts.
   Presigned URLs expire and are not managed by Greengrass. Use the
   `s3://` URI format in the recipe and ensure the token exchange
   role has `s3:GetObject` permission.

4. **NEVER make the startup hook a one-shot script.** The startup
   hook should be a long-running process (daemon, server, loop). If
   the startup script exits immediately, Greengrass considers the
   component "errored" and repeatedly restarts it. For one-shot
   scripts, use the install hook.

5. **NEVER forget the aws.lambda dependency for Lambda components.**
   Lambda components require the `aws.lambda` component as a HARD
   dependency. Without it, the Lambda runtime is not available on
   the device and the component will fail to start.

6. **NEVER forget aws.greengrass.DockerApplicationManager for Docker
   components.** Docker components require this as a HARD dependency.
   Without it, Docker image management is not available.

7. **NEVER use hardcoded host paths for component storage.** Use
   `{work:path}` for component-scoped storage. Hardcoded host paths
   may not exist on the device and are not managed by Greengrass.

8. **NEVER assume configuration merge replaces default config.**
   MERGE deep-merges with existing configuration (nested keys are
   merged, not replaced). To remove a key, use RESET, not MERGE with
   null.

9. **NEVER skip the core device health check.** Before deploying,
   verify the core device is HEALTHY. A device in UNHEALTHY state
   will not receive deployments.

10. **NEVER create a deployment without failureDetectionPolicy.**
    Always set `failureDetectionPolicy.action` to `ROLLBACK` (the
    default) so failed deployments revert to the last known good
    state. `DO_NOTHING` leaves devices in a broken state.

## Output format

```text
GREENGRASS_COMPONENT: <component-name>@<version> → <thing-group>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Component recipe: <component-name>@<version> — lifecycle hooks defined (install, startup, shutdown)
  [✓|✗] Version bump: <previous-version> → <new-version>
  [✓|✗] Artifacts: S3 URIs in recipe — s3://<bucket>/<path>
  [✓|✗] Token exchange role: s3:GetObject on <bucket> — configured
  [✓|✗] Thing group: <group-name> (<device-count> devices)
  [✓|✗] Core device(s): <device-name> — HEALTHY
  [✓|✗] Dependencies: HARD [<list>], SOFT [<list>]
  [✓|✗] Configuration merge: <merged-keys or "none (recipe defaults only)">
  [✓|✗] Secret manager: IoT role alias <alias-name> — configured | not required
  [✓|✗] Component type: Generic | Lambda (arn:<lambda-arn>) | Docker (image:<image-name>)
  [✓|✗] Volume mount: {work:path}/<dir> | none
  [✓|✗] Deployment mode: Cloud-based (default deployment) | Local (Greengrass CLI)
  [✓|✗] Deployment policies: failureDetection=ROLLBACK, componentUpdate=NOTIFY_COMPONENTS
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws greengrassv2 describe-component --arn <component-arn> --region <region>
  aws greengrassv2 list-core-devices --region <region>
  aws greengrassv2 get-deployment --deployment-id <deployment-id> --region <region>
```

### Worked example — basic component deployment

```text
GREENGRASS_COMPONENT: com.example.MyComponent@1.0.0 → MyDeviceGroup
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Component recipe: com.example.MyComponent@1.0.0 — lifecycle hooks defined (install, startup, shutdown)
  [✓] Version bump: new component (1.0.0)
  [✓] Artifacts: S3 URIs in recipe — s3://my-greengrass-artifacts/artifacts/com.example.MyComponent/1.0.0/my-script.py
  [✓] Token exchange role: s3:GetObject on my-greengrass-artifacts — configured
  [✓] Thing group: MyDeviceGroup (1 device)
  [✓] Core device(s): MyCoreDevice — HEALTHY
  [✓] Dependencies: HARD [], SOFT []
  [✓] Configuration merge: message="Hello from deployment", logging.level="debug"
  [✓] Secret manager: not required
  [✓] Component type: Generic
  [✓] Volume mount: none
  [✓] Deployment mode: Cloud-based (default deployment)
  [✓] Deployment policies: failureDetection=ROLLBACK, componentUpdate=NOTIFY_COMPONENTS
  [✓] Tags: Environment=production, Application=edge-processor
VERIFICATION_COMMANDS:
  aws greengrassv2 describe-component --arn arn:aws:greengrass:us-east-1:123456789012:components:com.example.MyComponent:versions:1.0.0 --region us-east-1
  aws greengrassv2 list-core-devices --region us-east-1
  aws greengrassv2 get-deployment --deployment-id d-1234567890 --region us-east-1
```

## Error handling

### Component stuck in ERRORED state
- The startup script is likely exiting immediately (one-shot script
  in startup hook). Move one-shot logic to the install hook, or make
  the startup hook a long-running process. Check device logs at
  `/greengrass/v2/logs/<component>.log`.

### Deployment not reaching the device
- The core device may be UNHEALTHY or offline. Check
  `aws greengrassv2 list-core-devices` for device status. Verify the
  device is in the target thing group. Check network connectivity
  from the device to AWS IoT.

### Artifacts not downloading
- The token exchange role may lack `s3:GetObject` on the artifact
  bucket. Verify the IAM policy attached to the token exchange role
  includes the artifact bucket ARN. Check device logs for S3 access
  errors.

### Configuration merge not taking effect
- The merge keys may not match the recipe's configuration schema.
  Configuration merge only works for keys defined in
  `ComponentConfiguration.DefaultConfiguration`. Verify the merge
  JSON keys match the recipe schema.

### Lambda component fails to start
- The `aws.lambda` component may not be deployed. Verify it is listed
  as a HARD dependency in the recipe and deployed alongside the
  Lambda component. Check that the Lambda runtime is compatible with
  the device architecture.

### Docker container fails to start
- Docker may not be installed or running on the device. Verify
  `docker ps` works on the device. Ensure
  `aws.greengrass.DockerApplicationManager` is deployed. For private
  registries, deploy `aws.docker.Login`.

## Domain

AWS CloudOps / AWS IoT Greengrass v2 Component Deployment & Edge
Computing.

## AWS documentation

- **Greengrass v2 Developer Guide** — https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html
- **Component recipes** — https://docs.aws.amazon.com/greengrass/v2/developerguide/component-recipe-reference.html
- **Create component** — https://docs.aws.amazon.com/greengrass/v2/developerguide/create-components.html
- **Deploy components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/deploy-components.html
- **Configuration merge** — https://docs.aws.amazon.com/greengrass/v2/developerguide/configure-component-update.html
- **Lambda components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/lambda-functions.html
- **Docker components** — https://docs.aws.amazon.com/greengrass/v2/developerguide/run-docker-container.html
- **Secret manager integration** — https://docs.aws.amazon.com/greengrass/v2/developerguide/secrets-manager.html
- **Core device setup** — https://docs.aws.amazon.com/greengrass/v2/developerguide/setting-up.html
- **Greengrass CLI** — https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-cli-component.html
