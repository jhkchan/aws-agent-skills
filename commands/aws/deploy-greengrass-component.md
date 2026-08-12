---
description: Deploy an AWS IoT Greengrass v2 component with production-grade defaults (component recipe with lifecycle hooks, S3 artifacts, thing group targeting, configuration merge, hard/soft dependencies, Lambda and Docker as components, secret manager integration via IoT role alias). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create greengrass component"
  - "deploy greengrass component"
  - "greengrass recipe"
  - "greengrass deployment"
  - "greengrass thing group"
  - "greengrass configuration merge"
  - "greengrass lambda component"
  - "greengrass docker component"
  - "greengrass secret manager"
  - "greengrass core device"
  - "greengrass component version"
  - "greengrass v2 component"
  - "edge component"
routes_to: greengrass-component-deployer
---

# /aws:deploy-greengrass-component

Activate the `greengrass-component-deployer` skill and deploy an AWS
IoT Greengrass v2 component with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Component recipe (lifecycle hooks: install, startup, shutdown)
2. Component versioning (semantic version bump on every change)
3. Artifact storage (S3 URI + token exchange role with s3:GetObject)
4. Component dependencies (HARD vs SOFT dependency types)
5. Deployment to thing group (NOT individual devices)
6. Configuration merge (per-group runtime parameter overrides)
7. Secret manager integration (IoT role alias for Secrets Manager)
8. Lambda as component (aws.lambda HARD dependency)
9. Docker as component (DockerApplicationManager HARD dependency)
10. Local volume mount ({work:path} convention)
11. Cloud-based vs local deployment (default vs Greengrass CLI)
12. Core device setup (Greengrass v2 installed, token exchange role)
13. Recent features (Docker improvements, config validation, metrics)

## When to use

- You need to create a Greengrass v2 component with a recipe.
- You need to deploy a component to a thing group.
- You need to package artifacts for edge deployment.
- You need configuration merge for per-device customization.
- You need to run a Lambda function on the edge.
- You need to run a Docker container on the edge.
- You need secret manager integration on edge devices.
- You need to set up a Greengrass core device.

## How to invoke

### Slash command

```
/aws:deploy-greengrass-component
```

Then provide: component name, version, lifecycle hooks (install/
startup/shutdown), artifact S3 URIs, thing group name, core device
name, dependencies (if any), configuration merge (if any), Lambda
or Docker details (if applicable), tags.

### Natural language

Any of these routes to the same skill:

- "create a greengrass component with install and startup hooks"
- "deploy a greengrass component to my thing group"
- "run a lambda function as a greengrass component"
- "run a docker container on my greengrass device"
- "set up secret manager access for my edge component"

### CLI routing

```bash
node cli/bin/cli.js route "create a greengrass component"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or deploy
Greengrass v2 components. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-greengrass-component

     Create a Greengrass v2 component
     com.example.TemperatureSensor version 1.0.0
     with install, startup, and shutdown hooks.
     Deploy to thing group FactoryDevices.
     Artifact: s3://my-bucket/sensor.py.
     Config merge: interval=10, logLevel=debug.

Skill:
  GREENGRASS_COMPONENT: com.example.TemperatureSensor@1.0.0 → FactoryDevices
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Recipe: lifecycle hooks defined (install, startup, shutdown)
    [✓] Artifacts: s3://my-bucket/sensor.py
    [✓] Thing group: FactoryDevices
    [✓] Config merge: interval=10, logLevel=debug
    [✓] Deployment policies: ROLLBACK
  VERIFICATION_COMMANDS:
    aws greengrassv2 describe-component --arn <component-arn> --region us-east-1
    aws greengrassv2 get-deployment --deployment-id <deployment-id> --region us-east-1
```

## References

- Skill definition: `skills/greengrass-component-deployer/SKILL.md`
- Recipe and lifecycle guide: `skills/greengrass-component-deployer/references/recipe-and-lifecycle.md`
- Deployment and config guide: `skills/greengrass-component-deployer/references/deployment-and-config.md`
- Eval suite: `skills/greengrass-component-deployer/evals/evals.json`
