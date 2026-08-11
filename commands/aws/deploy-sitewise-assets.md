---
description: Deploy AWS IoT SiteWise industrial data infrastructure with production-grade defaults (asset model with measurement/transform/metric/attribute properties, parent-child hierarchies, SiteWise Edge gateway on Greengrass, OPC-UA source configuration with node-to-alias mappings, data ingestion via BatchPutAssetPropertyValue, dashboards and portals with Identity Center SSO, threshold alarms with duration). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create iot sitewise asset model"
  - "deploy sitewise asset"
  - "sitewise asset hierarchy"
  - "sitewise edge gateway"
  - "opc-ua source sitewise"
  - "batchputassetpropertyvalue"
  - "sitewise dashboard"
  - "sitewise portal"
  - "sitewise alarm"
  - "asset property alias"
  - "sitewise identity center"
  - "iot sitewise"
  - "industrial asset model"
routes_to: sitewise-asset-deployer
---

# /aws:deploy-sitewise-assets

Activate the `sitewise-asset-deployer` skill and deploy AWS IoT
SiteWise industrial data infrastructure with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Asset model property types (measurement, transform, metric, attribute)
2. Asset hierarchy (parent-child, defined in parent model)
3. Gateway and SiteWise Edge (Greengrass V2 platform)
4. OPC-UA source configuration (node-to-alias mappings)
5. Data ingestion (BatchPutAssetPropertyValue via alias or property ID)
6. Asset property aliases (unique, hierarchical naming)
7. Dashboards (project and portal)
8. Alarms (threshold rules with duration)
9. Time series storage and CloudWatch integration
10. Identity Center for portal SSO access
11. Recent features (composite models, Modbus, hysteresis alarms)

## When to use

- You need to model industrial assets in SiteWise.
- You are creating asset models with measurement/transform/metric/
  attribute properties.
- You are building parent-child asset hierarchies.
- You are deploying a SiteWise Edge gateway on Greengrass.
- You need OPC-UA source configuration.
- You need asset property aliases for external ingestion.
- You are creating SiteWise dashboards and portals.
- You need threshold-based alarms with duration.
- You need Identity Center SSO for portal access.

## When NOT to use

- **AWS IoT Core** — device connectivity and messaging, not asset
  modeling. Use IoT Core skills for thing registration and MQTT.
- **AWS IoT TwinMaker** — digital twin scene composition, not
  industrial data ingestion. Use TwinMaker skills for 3D visualization.
- **AWS IoT Events** — event detection on sensor patterns, not
  threshold alarms on asset properties. Use IoT Events for complex
  state machine detection.
- **Generic CloudWatch alarms** — use CloudWatch skills for
  infrastructure metrics, not SiteWise asset property alarms.

## How to invoke

### Slash command

```
/aws:deploy-sitewise-assets
```

Then provide: asset model name, property definitions (type, name,
dataType, unit), hierarchy structure, gateway name and Greengrass
core device, OPC-UA endpoint and node mappings, aliases, dashboard/
portal details, alarm thresholds, tags.

### Natural language

Any of these routes to the same skill:

- "create a SiteWise asset model for a wind turbine"
- "set up an OPC-UA source in SiteWise"
- "create a SiteWise dashboard and portal"
- "configure SiteWise alarms with thresholds"
- "deploy a SiteWise Edge gateway on Greengrass"

### CLI routing

```bash
node cli/bin/cli.js route "create a sitewise asset model"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to deploy SiteWise
industrial data infrastructure. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-sitewise-assets

     Create a SiteWise asset model "Pump Station" with FlowRate,
     Pressure, Temperature measurements. Transform TemperatureF.
     OPC-UA gateway at opc.tcp://10.0.1.50:4840. SSO portal.

Skill:
  SITEWISE: Pump Station (model-aaa111)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Property types: measurement(3), transform(1)
    [✓] Gateway: Plant Gateway — RUNNING
    [✓] OPC-UA source: opc.tcp://10.0.1.50:4840, 3 node mappings
    [✓] Aliases: /plant/area1/pump1/*
    [✓] Portal: Plant Portal — auth mode SSO
  VERIFICATION_COMMANDS:
    aws iotsitewise describe-asset-model --asset-model-id <model-id>
    aws iotsitewise describe-gateway --gateway-id <gateway-id>
```

## References

- Skill definition: `skills/sitewise-asset-deployer/SKILL.md`
- Asset models and properties: `skills/sitewise-asset-deployer/references/asset-models-and-properties.md`
- Gateway and ingestion: `skills/sitewise-asset-deployer/references/gateway-and-ingestion.md`
- Eval suite: `skills/sitewise-asset-deployer/evals/evals.json`
