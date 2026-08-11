# End-to-End Example: SiteWise Asset Deployment

A walkthrough showing how to use the `sitewise-asset-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a SiteWise industrial monitoring system for a pump
station with OPC-UA data ingestion, a transform for unit conversion,
threshold alarms, and a portal for operators. The deployment needs:

- Asset model: "Pump Station" with 4 measurements, 1 transform, 1
  metric, 2 attributes
- Gateway: "Plant Gateway" on Greengrass V2 core device
- OPC-UA source: opc.tcp://10.0.1.50:4840 with 4 node mappings
- Aliases: /plant/area1/pump1/*
- Alarm: HighVibration (Vibration GT 5.0 mm/s for 10 minutes)
- Portal: "Plant Portal" with SSO auth mode
- Account: 123456789012, Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-sitewise-assets
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a SiteWise asset model for Pump Station with
      FlowRate, Pressure, Temperature, Vibration measurements,
      TemperatureF transform, HourlyAvgFlow metric, and a
      HighVibration alarm. OPC-UA gateway at opc.tcp://10.0.1.50:4840.
      SSO portal for operators."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a sitewise asset model with opcua"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SITEWISE: Pump Station (model-aaa111) → Pump-001 (asset-bbb222)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Asset model: Pump Station (model-aaa111) — ACTIVE
  [✓] Property types: measurement(4), transform(1), metric(1), attribute(2)
  [✓] Transform expressions: validated (TemperatureF = Temperature * 9/5 + 32)
  [✓] Metric processing configs: validated (HourlyAvgFlow=3600s)
  [✓] Asset(s) created: Pump-001 (asset-bbb222) — ACTIVE
  [✓] Gateway: Plant Gateway (gw-ccc333) — RUNNING
  [✓] OPC-UA source: PLC-Primary — endpoint opc.tcp://10.0.1.50:4840, 4 node mappings
  [✓] Asset property aliases: 4 aliases set (/plant/area1/pump1/*)
  [✓] Data ingestion path: OPC-UA → gateway → measurement properties
  [✓] Storage configuration: warm tier (365 days), disassociated data ENABLED
  [✓] Dashboard: Pump Station Overview in project Plant Monitoring
  [✓] Portal: Plant Portal — auth mode SSO, alarms ENABLED
  [✓] Identity Center: configured for portal (ssoins-12345)
  [✓] Alarms: 1 threshold alarm (HighVibration > 5.0 mm/s, 10 min)
  [✓] CloudWatch integration: ingestion metrics monitored
  [✓] Tags: Environment=production, Site=PlantA
VERIFICATION_COMMANDS:
  aws iotsitewise describe-asset-model --asset-model-id model-aaa111
  aws iotsitewise describe-asset --asset-id asset-bbb222
  aws iotsitewise describe-gateway --gateway-id gw-ccc333
  aws iotsitewise list-assets --filter TOPLEVEL --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the asset model with all property types
MODEL_ID=$(aws iotsitewise create-asset-model \
  --asset-model-name "Pump Station" \
  --asset-model-properties '[
    {"name":"FlowRate","dataType":"DOUBLE","unit":"m3/s","type":"measurement"},
    {"name":"Pressure","dataType":"DOUBLE","unit":"kPa","type":"measurement"},
    {"name":"Temperature","dataType":"DOUBLE","unit":"C","type":"measurement"},
    {"name":"Vibration","dataType":"DOUBLE","unit":"mm/s","type":"measurement"},
    {"name":"TemperatureF","dataType":"DOUBLE","unit":"F","type":"transform",
     "expression":"Temperature * 9/5 + 32"},
    {"name":"HourlyAvgFlow","dataType":"DOUBLE","unit":"m3/s","type":"metric",
     "expression":"avg(FlowRate)","window":{"tumbling":{"interval":"1h"}}},
    {"name":"Manufacturer","dataType":"STRING","type":"attribute"},
    {"name":"SerialNumber","dataType":"STRING","type":"attribute"}
  ]' \
  --asset-model-alarms '[
    {"alarmState":{"stateConfiguration":{"alarmType":"THRESHOLD",
     "threshold":{"comparisonOperator":"GT","value":{"doubleValue":5.0},
     "durationInMinutes":10,"propertyId":"vibration-prop-id"}}}}
  ]' \
  --query 'assetModelId' --output text)

# Step 2: Wait for model to become ACTIVE
aws iotsitewise wait asset-model-active --asset-model-id "$MODEL_ID"

# Step 3: Create the asset
ASSET_ID=$(aws iotsitewise create-asset \
  --asset-name "Pump-001" \
  --asset-model-id "$MODEL_ID" \
  --query 'assetId' --output text)

# Wait for asset to become ACTIVE
aws iotsitewise wait asset-active --asset-id "$ASSET_ID"

# Step 4: Set aliases on each measurement property
aws iotsitewise update-asset-property \
  --asset-id "$ASSET_ID" --property-id "$FLOWRATE_PROP_ID" \
  --property-alias "/plant/area1/pump1/flowRate"

aws iotsitewise update-asset-property \
  --asset-id "$ASSET_ID" --property-id "$TEMPERATURE_PROP_ID" \
  --property-alias "/plant/area1/pump1/temperature"

# Step 5: Create the gateway
GATEWAY_ID=$(aws iotsitewise create-gateway \
  --gateway-name "Plant Gateway" \
  --gateway-platform greengrassV2CoreDevice=GreengrassCore-001 \
  --query 'gatewayId' --output text)

# Step 6: Configure OPC-UA source with node-to-alias mappings
aws iotsitewise put-gateway-capability-configuration \
  --gateway-id "$GATEWAY_ID" \
  --capability-namespace "iotsitewise:opcuacollector:1" \
  --capability-configuration file://opcua-config.json

# Step 7: Create portal project and dashboard
PROJECT_ID=$(aws iotsitewise create-project \
  --project-name "Plant Monitoring" \
  --portal-id "$PORTAL_ID" \
  --query 'projectId' --output text)

DASHBOARD_ID=$(aws iotsitewise create-dashboard \
  --dashboard-name "Pump Station Overview" \
  --project-id "$PROJECT_ID" \
  --dashboard-definition file://dashboard-definition.json \
  --query 'dashboardId' --output text)
```

---

## Step 4 — Post-deployment verification

```bash
# Verify model is ACTIVE and has correct property types
aws iotsitewise describe-asset-model \
  --asset-model-id "$MODEL_ID" \
  --query 'assetModelProperties[*].{Name:name,Type:type}' \
  --output table

# Verify asset is ACTIVE and has aliases
aws iotsitewise describe-asset \
  --asset-id "$ASSET_ID" \
  --query 'assetStatus.state' --output text
# Expected: ACTIVE

# Verify gateway is RUNNING
aws iotsitewise describe-gateway \
  --gateway-id "$GATEWAY_ID" \
  --query 'gatewayStatus.state' --output text
# Expected: RUNNING

# Verify data is flowing (check recent property values)
aws iotsitewise batch-get-asset-property-value \
  --entries '[{
    "entryId": "check-001",
    "assetId": "'"$ASSET_ID"'",
    "propertyId": "'"$FLOWRATE_PROP_ID"'"
  }]'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Property types | All properties treated the same | Explicit measurement/transform/metric/attribute typing | Only measurements accept external data; wrong type = no ingestion |
| OPC-UA mappings | Gateway created without node mappings | nodePathMappings configured with aliases | Without mappings, gateway connects but ingests nothing |
| Aliases | Not set (uses property ID only) | Alias-based ingestion for scale | Avoids DescribeAsset per data point; required for IoT Core rules |
| Hierarchy | Tries to create at asset runtime | Hierarchy defined in parent model | Must be in model definition; cannot add at runtime |
| Alarm duration | No duration (fires on every spike) | durationInMinutes set | Without duration, alarm is noisy and fires on transient spikes |
| Portal SSO | Missing Identity Center check | Prerequisite verified | Portal creation fails without Identity Center |
| Storage config | Uses defaults | Warm tier retention explicitly set | Defaults may not meet retention requirements |

---

## Related artifacts

- **Skill definition:** `skills/sitewise-asset-deployer/SKILL.md`
- **Asset models and properties guide:** `skills/sitewise-asset-deployer/references/asset-models-and-properties.md`
- **Gateway and ingestion guide:** `skills/sitewise-asset-deployer/references/gateway-and-ingestion.md`
- **Slash command:** `commands/aws/deploy-sitewise-assets.md`
- **Eval suite:** `skills/sitewise-asset-deployer/evals/evals.json`
- **Legacy test cases:** `skills/sitewise-asset-deployer/eval/test-cases.yaml`
