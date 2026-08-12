# End-to-End Example: Greengrass v2 Component Deployment

A walkthrough showing how to use the `greengrass-component-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a temperature sensor component to a thing group
of factory devices. The component needs:

- Component: com.example.TemperatureSensor
- Version: 1.0.0 (new component)
- Artifact: Python script in S3
- Thing group: FactoryDevices (3 devices)
- Core device: MyFactoryGateway (HEALTHY)
- Lifecycle: install, startup, shutdown
- Configuration merge: interval=10, logLevel=debug
- Tags: Environment=production, Site=factory-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-greengrass-component
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Greengrass v2 component
      com.example.TemperatureSensor version 1.0.0 with
      install, startup, and shutdown hooks. Deploy to
      thing group FactoryDevices. Artifact is a Python
      script in S3. Config merge: interval=10, logLevel=debug."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a greengrass component"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
GREENGRASS_COMPONENT: com.example.TemperatureSensor@1.0.0 → FactoryDevices
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Component recipe: com.example.TemperatureSensor@1.0.0 — lifecycle hooks defined (install, startup, shutdown)
  [✓] Version bump: new component (1.0.0)
  [✓] Artifacts: S3 URIs in recipe — s3://my-greengrass-artifacts/artifacts/com.example.TemperatureSensor/1.0.0/sensor.py
  [✓] Token exchange role: s3:GetObject on my-greengrass-artifacts — configured
  [✓] Thing group: FactoryDevices (3 devices)
  [✓] Core device(s): MyFactoryGateway — HEALTHY
  [✓] Dependencies: HARD [], SOFT []
  [✓] Configuration merge: interval=10, logLevel=debug
  [✓] Secret manager: not required
  [✓] Component type: Generic
  [✓] Volume mount: none
  [✓] Deployment mode: Cloud-based (default deployment)
  [✓] Deployment policies: failureDetection=ROLLBACK, componentUpdate=NOTIFY_COMPONENTS
  [✓] Tags: Environment=production, Site=factory-1
VERIFICATION_COMMANDS:
  aws greengrassv2 describe-component --arn arn:aws:greengrass:us-east-1:123456789012:components:com.example.TemperatureSensor:versions:1.0.0 --region us-east-1
  aws greengrassv2 list-core-devices --region us-east-1
  aws greengrassv2 get-deployment --deployment-id <deployment-id> --region us-east-1
```

---

## Step 3 — Write the component recipe

```yaml
---
RecipeFormatVersion: "2020-01-25"
ComponentName: com.example.TemperatureSensor
ComponentVersion: "1.0.0"
ComponentDescription: "Temperature sensor reader for factory devices"
ComponentPublisher: Example
ComponentConfiguration:
  DefaultConfiguration:
    interval: 5
    logLevel: "info"
    outputPath: "/greengrass/v2/work/com.example.TemperatureSensor"
Manifests:
  - Name: "linux-amd64"
    Platform:
      architecture: amd64
      os: linux
    Artifacts:
      - URI: s3://my-greengrass-artifacts/artifacts/com.example.TemperatureSensor/1.0.0/sensor.py
        Unarchive: NONE
    Lifecycle:
      Install:
        Script: |
          echo "Installing TemperatureSensor 1.0.0"
          mkdir -p {work:path}/readings
      Startup:
        Script: |
          #!/bin/bash
          INTERVAL={configuration:/interval}
          LOG_LEVEL={configuration:/logLevel}
          OUTPUT={work:path}/readings
          python3 {artifacts:path}/sensor.py \
            --interval "$INTERVAL" \
            --log-level "$LOG_LEVEL" \
            --output "$OUTPUT"
      Shutdown:
        Script: |
          echo "Shutting down TemperatureSensor"
          pkill -f "sensor.py" || true
```

---

## Step 4 — Upload artifact and create component version

```bash
# Upload artifact to S3
aws s3 cp sensor.py \
  s3://my-greengrass-artifacts/artifacts/com.example.TemperatureSensor/1.0.0/sensor.py \
  --region us-east-1

# Create the component version from recipe
aws greengrassv2 create-component-version \
  --inline-recipe fileb://recipe.yaml \
  --region us-east-1
```

---

## Step 5 — Deploy to thing group with configuration merge

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/FactoryDevices" \
  --deployment-name "Deploy TemperatureSensor 1.0.0" \
  --components '{
    "com.example.TemperatureSensor": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {
        "MERGE": "{\"interval\": 10, \"logLevel\": \"debug\"}"
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

---

## Step 6 — Post-deployment verification

```bash
# Component version exists
aws greengrassv2 describe-component \
  --arn "arn:aws:greengrass:us-east-1:123456789012:components:com.example.TemperatureSensor:versions:1.0.0" \
  --region us-east-1

# Core devices are healthy
aws greengrassv2 list-core-devices \
  --region us-east-1 \
  --query "coreDevices[?coreDeviceThingName=='MyFactoryGateway']"

# Deployment status
aws greengrassv2 get-deployment \
  --deployment-id "<deployment-id>" \
  --region us-east-1

# On the device: check component is running
sudo /greengrass/v2/bin/greengrass-cli component list
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Deployment target | Individual thing | Thing group (FactoryDevices) | Thing groups allow scaling without re-architecting; new devices auto-receive deployment |
| Lifecycle hooks | Missing or only startup | Install + Startup + Shutdown | Without all three, component either does nothing (no install) or never cleans up (no shutdown) |
| Artifact access | Presigned URLs | Token exchange role + s3:GetObject | Presigned URLs expire; token exchange role is managed and rotated by Greengrass |
| Configuration merge | All config in recipe | Recipe defaults + deployment merge | Merge allows per-group customization without recipe changes |
| Version bump | Reuses 1.0.0 | Explicit version bump tracking | Same version = no update; Greengrass silently skips |
| Startup as long-running | One-shot script in startup | Long-running process | One-shot startup causes restart loop; Greengrass expects startup to stay alive |
| Deployment policies | No failure policy | ROLLBACK on failure | Without rollback, failed deployments leave devices broken |

---

## Related artifacts

- **Skill definition:** `skills/greengrass-component-deployer/SKILL.md`
- **Recipe and lifecycle guide:** `skills/greengrass-component-deployer/references/recipe-and-lifecycle.md`
- **Deployment and config guide:** `skills/greengrass-component-deployer/references/deployment-and-config.md`
- **Slash command:** `commands/aws/deploy-greengrass-component.md`
- **Eval suite:** `skills/greengrass-component-deployer/evals/evals.json`
- **Legacy test cases:** `skills/greengrass-component-deployer/eval/test-cases.yaml`
