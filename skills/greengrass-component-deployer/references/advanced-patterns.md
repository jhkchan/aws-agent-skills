# Advanced Patterns — Greengrass Component Deployer

Load-on-demand detail moved verbatim from SKILL.md.

## Step 7 — Secret manager integration (IoT role alias) — moved from SKILL.md

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

## Step 8 — Lambda as component — moved from SKILL.md

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

## Step 9 — Docker container as component — moved from SKILL.md

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

## Step 10 — Local volume mount — moved from SKILL.md

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

## Step 11 — Cloud-based deployment vs local deployment — moved from SKILL.md

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

## Step 12 — Core device setup — moved from SKILL.md

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

## Step 13 — Recent features — moved from SKILL.md

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
