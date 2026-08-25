---
name: sitewise-asset-deployer
description: 'Deploys AWS IoT SiteWise industrial data infrastructure with production defaults: asset model creation (measurement, metric, transform, attribute property types), asset hierarchy (parent-child composition), SiteWise Edge gateway on IoT Greengrass, data ingestion via BatchPutAssetPropertyValue, OPC-UA source configuration, asset property aliases, dashboards, threshold alarms, warm-tier storage, and Identity Center portal access. Emits a READY_TO_DEPLOY checklist with verification commands. Use when modeling industrial assets, ingesting OPC-UA telemetry, creating dashboards, configuring alarms, deploying Edge gateways, or setting up aliases. Triggers: create iot sitewise asset model, sitewise asset hierarchy, sitewise edge gateway, opc-ua source sitewise, batchputassetpropertyvalue, sitewise dashboard portal, sitewise alarm, asset property alias, sitewise identity center.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with iot-sitewise access (and greengrassv2 access if deploying Edge gateway). Works with Terraform aws_iotsitewise_asset_model / aws_iotsitewise_asset / aws_iotsitewise_gateway resources and CloudFormation AWS::IoTSiteWise::AssetModel / Asset / Gateway templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, iot-sitewise, cloudops, deploy, industrial, provisioning, asset-model, opc-ua, edge-gateway, dashboard, alarm, identity-center
  dependencies: aws-orchestrator
  keywords: aws, iot sitewise, asset model, asset hierarchy, cloudops, deploy, provisioning, opc-ua, measurement, transform, metric, attribute, gateway, greengrass, batchputassetpropertyvalue, alias, dashboard, portal, alarm, identity center
  when_to_use: Invoke when the user wants to model industrial assets in AWS IoT SiteWise, create asset models with measurement/metric/transform/ attribute properties, build parent-child asset hierarchies, deploy SiteWise Edge gateways on IoT Greengrass, configure OPC-UA source data ingestion, set up asset property aliases for external data feeds, create dashboards and portals, configure threshold-based alarms, or integrate SiteWise with CloudWatch and Identity Center. Do NOT invoke for AWS IoT Core (device connectivity), AWS IoT TwinMaker (digital twins), or AWS IoT Events (event detection) unless the task specifically involves SiteWise asset modeling.
---

# AWS IoT SiteWise Asset Deployer

An AWS CloudOps agent skill that deploys AWS IoT SiteWise industrial
data infrastructure with correct defaults. The skill walks the operator
through asset model design (four property types), hierarchy composition,
gateway and OPC-UA configuration, data ingestion paths, aliases,
dashboards, alarms, and access control, captures modeling and ingestion
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create IoT SiteWise asset model, SiteWise asset hierarchy, SiteWise Edge
gateway, OPC-UA source SiteWise, BatchPutAssetPropertyValue, SiteWise
dashboard portal, SiteWise alarm, asset property alias, SiteWise
Identity Center.

## STRICT output contract

When this skill is invoked with a SiteWise-provisioning request
(create an asset model, build an asset hierarchy, deploy a gateway,
configure OPC-UA ingestion, set up dashboards or alarms, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `SITEWISE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Asset model property types | Core model design |
| Step 2 — Asset hierarchy (parent-child) | Model composition |
| Step 3 — Gateway and SiteWise Edge | Edge data collection |
| Step 4 — OPC-UA source configuration | Industrial protocol setup |
| Step 5 — Data ingestion (BatchPutAssetPropertyValue) | Cloud ingestion path |
| Step 6 — Asset property aliases | External data binding |
| Step 7 — Dashboards (project and portal) | Visualization |
| Step 8 — Alarms (threshold rules) | Operational alerting |
| Step 9 — Time series storage and CloudWatch | Data persistence |
| Step 10 — Identity Center for portal access | Access control |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/asset-models-and-properties.md | Property type detail |
| references/gateway-and-ingestion.md | Gateway + ingestion detail |

## Mindset

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#mindset) — the three misconceptions (property types, gateway mapping, alias necessity).
Load that reference on demand before executing this section.

## Configuration dependency graph (novel heuristic)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-novel-heuristic) — 10-row dependency table, hierarchy-in-the-model rule, cross-dependency gotchas.
Load that reference on demand before executing this section.

## Expert heuristic: asset model inheritance for standardization

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-asset-model-inheritance-for-standardization) — wind-turbine standardization model and fleet inheritance pattern.
Load that reference on demand before executing this section.

## Expert heuristic: OPC-UA data flow to asset properties

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-opc-ua-data-flow-to-asset-properties) — five-hop OPC-UA to gateway to property to dashboard data-flow trace.
Load that reference on demand before executing this section.

## Expert heuristic: transform expressions for derived metrics

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-transform-expressions-for-derived-metrics) — transform expression syntax, supported functions, and worked formulas.
Load that reference on demand before executing this section.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| IAM permissions for SiteWise | All SiteWise API calls require iotsitewise:* or specific actions | `aws iotsitewise list-asset-models` |
| Greengrass core device (if using Edge gateway) | Gateway platform is Greengrass V2; needs a registered core device | `aws greengrassv2 list-core-devices` |
| OPC-UA server endpoint reachable (if using OPC-UA) | Gateway must connect to the OPC-UA server | Confirm endpoint from SCADA/PLC admin |
| Identity Center instance (if creating a portal) | Portal SSO requires Identity Center | `aws sso-admin list-instances` |
| SiteWise storage configuration | Warm tier must be configured to store data | `aws iotsitewise describe-storage-configuration` |
| AWS Region supports SiteWise | SiteWise is not available in all regions | `aws iotsitewise describe-default-encryption-configuration` |
| Property type decisions finalized | Wrong property types break data flow | Confirm measurement vs transform vs metric vs attribute per data point |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Asset model property types

SiteWise asset models define four property types. Each has a distinct
purpose and data-flow behavior.

| Property type | Receives external data? | Derives from other properties? | Aggregates over time? | Stores static metadata? |
|---|---|---|---|---|
| Measurement | YES (the only ingest target) | No | No | No |
| Transform | No | YES (formula on measurements, near-real-time) | No | No |
| Metric | No | YES (formula on measurements/transforms, time-windowed) | YES (configurable interval) | No |
| Attribute | No | No | No | YES (string, integer, boolean, double) |

**Measurement properties** are the data ingestion target. OPC-UA
sources and BatchPutAssetPropertyValue write to measurements. Each
measurement has a data type: STRING, INTEGER, DOUBLE, BOOLEAN.

**Transform properties** apply a formula to the current value of
referenced measurements/transforms on each data point. They compute
near-real-time derived values (e.g., unit conversions, efficiency
ratios). The expression references other properties by name or ID.

**Metric properties** aggregate data over a specified time window using
a processing configuration (interval in seconds, forward/backward time
window). Metrics compute rolling aggregates (e.g., hourly average,
daily total, 15-minute max).

**Attribute properties** store static metadata about the asset (serial
number, location, rated capacity). They do NOT have time series data.

## Step 2 — Asset hierarchy (parent-child)

→ Moved to [references/asset-models-and-properties.md](references/asset-models-and-properties.md#step-2--asset-hierarchy-parent-child) — parent-model hierarchy CLI, create-asset, wait asset-active, associate-assets.
Load that reference on demand before executing this section.

## Step 3 — Gateway and SiteWise Edge

→ Moved to [references/gateway-and-ingestion.md](references/gateway-and-ingestion.md#step-3--gateway-and-sitewise-edge) — create-gateway CLI, gateway states, Edge connector component.
Load that reference on demand before executing this section.

## Step 4 — OPC-UA source configuration

→ Moved to [references/gateway-and-ingestion.md](references/gateway-and-ingestion.md#step-4--opc-ua-source-configuration) — capability configuration CLI and the full OPC-UA source JSON with nodePathMappings.
Load that reference on demand before executing this section.

## Step 5 — Data ingestion (BatchPutAssetPropertyValue)

For cloud-direct ingestion (bypassing the gateway), use
BatchPutAssetPropertyValue. This is used by IoT Core rules, Lambda
functions, or external integrations.

**Ingest via property alias (recommended for scale):**

```bash
aws iotsitewise batch-put-asset-property-value \
  --entries '[{
    "entryId": "entry-001",
    "propertyAlias": "/factory/line1/turbine1/temperature",
    "propertyValues": [{
      "value": {"doubleValue": 72.5},
      "timestamp": {"timeInSeconds": 1722816000, "offsetInNanos": 0},
      "quality": "GOOD"
    }]
  }]'
```

**Ingest via property ID and asset ID:**

```bash
aws iotsitewise batch-put-asset-property-value \
  --entries '[{
    "entryId": "entry-001",
    "assetId": "asset-aaa11122",
    "propertyId": "prop-bbb22233",
    "propertyValues": [{
      "value": {"doubleValue": 72.5},
      "timestamp": {"timeInSeconds": 1722816000, "offsetInNanos": 0},
      "quality": "GOOD"
    }]
  }]'
```

**Alias-based ingestion is preferred for scale** because it avoids a
prior DescribeAsset lookup to resolve property IDs. IoT Core rule SQL
actions can write directly to aliases.

**Batch limits:** up to 10 entries per call, up to 10 property values
per entry. For high throughput, use multiple calls or a buffering layer
(Kinesis + Lambda).

## Step 6 — Asset property aliases

Aliases map a string path to a specific asset property. They enable
external ingestion without property ID resolution.

**Set an alias on an asset property:**

```bash
aws iotsitewise update-asset-property \
  --asset-id "$TURBINE_ID" \
  --property-id "$TEMPERATURE_PROP_ID" \
  --property-alias "/factory/line1/turbine1/temperature" \
  --property-notification-state ENABLED
```

**Alias naming convention:** use hierarchical paths that mirror the
physical topology:

```text
/<company>/<site>/<area>/<equipment>/<property>
  /acme/hoover/line1/turbine1/temperature
  /acme/hoover/line1/turbine1/rpm
  /acme/hoover/line1/turbine1/powerOutput
```

**Critical:** aliases must be unique across the entire AWS account.
Duplicate aliases cause BatchPutAssetPropertyValue to write to the
wrong asset property.

## Step 7 — Dashboards (project and portal)

→ Moved to [references/portals-dashboards-and-access.md](references/portals-dashboards-and-access.md#step-7--dashboards-project-and-portal) — create-project / create-dashboard / create-portal CLI and the portal IAM role.
Load that reference on demand before executing this section.

## Step 8 — Alarms (threshold rules)

Alarms monitor asset property values against threshold rules and fire
when conditions are met. Alarms are defined at the MODEL level and
inherited by all assets created from the model.

**Alarm definition in the asset model:**

```json
{
  "id": "alarm-high-temp",
  "name": "High Temperature Alarm",
  "alarmState": {
    "stateConfiguration": {
      "alarmType": "THRESHOLD",
      "threshold": {
        "comparisonOperator": "GT",
        "value": {
          "doubleValue": 80.0
        },
        "durationInMinutes": 5,
        "propertyId": "measurement-temperature-id"
      }
    }
  }
}
```

**Comparison operators:** `GT` (greater than), `LT` (less than),
`GTE` (greater than or equal), `LTE` (less than or equal),
`EQ` (equal), `NEQ` (not equal).

**Duration:** the threshold condition must persist for
`durationInMinutes` before the alarm transitions to ALARM state.
Without a duration, the alarm fires on every threshold breach (noisy).

**Alarm states:** `NORMAL`, `ALARM`, `ACKNOWLEDGED`, `SNOOZE_DISABLED`.

**Alarm can trigger:** IoT Core topics, Lambda functions (via alarm
state change events), or portal notifications.

## Step 9 — Time series storage and CloudWatch integration

→ Moved to [references/gateway-and-ingestion.md](references/gateway-and-ingestion.md#step-9--time-series-storage-and-cloudwatch-integration) — put-storage-configuration, warm tier, ingestion and gateway CloudWatch metrics.
Load that reference on demand before executing this section.

## Step 10 — Identity Center for portal access

→ Moved to [references/portals-dashboards-and-access.md](references/portals-dashboards-and-access.md#step-10--identity-center-for-portal-access) — SSO portal creation, create-access-policy CLI, project roles.
Load that reference on demand before executing this section.

## Step 11 — Recent features

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-11--recent-features) — composite models, Modbus, ingestion throughput, dashboard versioning, alarm hysteresis, IdC maturity.
Load that reference on demand before executing this section.

## NEVER do these things

1. **NEVER define hierarchies on the asset instance.** Hierarchies are
   declared in the PARENT asset model's `assetModelHierarchies`. You
   cannot create parent-child relationships between arbitrary assets at
   runtime — the model must define the hierarchy structure first.

2. **NEVER ingest data into a transform or metric property.** Only
   MEASUREMENT properties accept external data. Transforms and metrics
   derive their values from measurements. Attempting to write to a
   transform/metric via BatchPutAssetPropertyValue fails silently or
   returns an error.

3. **NEVER create assets from a model that is not ACTIVE.** Model
   creation is asynchronous. Poll `describe-asset-model` until status
   is ACTIVE before creating assets. Assets created from a CREATING
   model fail with a validation error.

4. **NEVER use duplicate asset property aliases.** Aliases must be
   unique across the entire AWS account. Duplicate aliases cause
   BatchPutAssetPropertyValue to write to the wrong asset. Always
   verify alias uniqueness before setting.

5. **NEVER omit the nodePathMappings in OPC-UA source configuration.**
   Without node-to-alias mappings, the gateway connects to the OPC-UA
   server but ingests nothing. This is the #1 cause of "gateway
   connected but no data" issues.

6. **NEVER create a portal without Identity Center configured (for SSO
   mode).** Portal creation with `portalAuthMode: SSO` fails if
   Identity Center is not set up in the account. Verify the Identity
   Center instance exists before creating an SSO portal.

7. **NEVER define alarms without a duration.** Without a
   `durationInMinutes`, the alarm fires on every threshold breach
   (including momentary spikes). Always set a duration that represents
   a meaningful sustained condition.

8. **NEVER assume the gateway auto-deploys to any Greengrass device.**
   The gateway platform parameter must reference a REGISTERED Greengrass
   V2 core device. The core device must be online and running Greengrass
   V2 with the SiteWise Edge connector component.

9. **NEVER forget the portal IAM role.** The portal role is what
   SiteWise assumes to read asset data on behalf of portal users.
   Without the role (or with insufficient permissions), portal
   dashboards show no data.

10. **NEVER skip storage configuration.** Without
    `put-storage-configuration`, data ingestion succeeds but data is
    not retained in the warm tier (or uses defaults that may not meet
    retention requirements). Configure the warm tier retention
    explicitly.

## Output format (STRICT output contract)

When this skill is invoked, the agent MUST respond with the block defined
below using the literal all-caps labels `SITEWISE:`, `VERDICT:`,
`CHECKLIST:`, `VERIFICATION_COMMANDS:`, `FORBIDDEN:`, and
`DECISION_TREE:`. Do NOT preface the checklist with prose, headings, or
disclaimers — emit the block as the first lines of the response.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### Literal output labels

```text
SITEWISE: <asset-model-name> (<asset-model-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Measurement properties: <name(DOUBLE|INTEGER|STRING|BOOLEAN), ...>
  [✓|✗] Transform properties: <name = expression, ...>
  [✓|✗] Metric properties: <name(expression, interval), ...>
  [✓|✗] Attribute properties: <name(type), ...>
  [✓|✗] Asset hierarchy: <parent-model> → <child-model> via <hierarchy-name>
  [✓|✗] Asset(s): <name> (<id>) — ACTIVE
  [✓|✗] Gateway: <name> (<id>) — RUNNING
  [✓|✗] OPC-UA source: <name> — endpoint <opc.tcp://...>, <N> node mappings
  [✓|✗] Aliases: <N> set (<prefix>/*)
  [✓|✗] Ingestion path: OPC-UA → gateway → measurement properties
  [✓|✗] Storage: warm tier (<N> days), disassociated data ENABLED
  [✓|✗] Alarms: <N> threshold alarms (<names>)
  [✓|✗] Tags: <key=value>
VERIFICATION_COMMANDS:
  aws iotsitewise describe-asset-model --asset-model-id <model-id>
  aws iotsitewise describe-asset --asset-id <asset-id>
  aws iotsitewise describe-gateway --gateway-id <gateway-id>
```

### FORBIDDEN — NEVER do these

1. NEVER ingest data into a transform or metric property — only
   MEASUREMENT properties receive external data via
   BatchPutAssetPropertyValue or OPC-UA sources. Writing to a
   transform/metric fails silently or returns an error.

2. NEVER define hierarchies on the asset instance — hierarchies are
   declared in the PARENT asset model's `assetModelHierarchies` array.
   Runtime parent-child association requires a pre-existing model-level
   hierarchy definition.

3. NEVER create assets from a model that is not ACTIVE — model creation
   is asynchronous. Poll `describe-asset-model` until `status=ACTIVE`.
   Assets created from a CREATING model fail with a validation error.

4. NEVER use duplicate asset property aliases — aliases must be unique
   across the entire AWS account. Duplicates cause
   BatchPutAssetPropertyValue to write to the wrong asset property.

5. NEVER omit `nodePathMappings` in OPC-UA source configuration —
   without node-to-alias mappings the gateway connects but ingests
   nothing. This is the #1 cause of "gateway connected but no data."

6. NEVER define threshold alarms without `durationInMinutes` — without a
   duration the alarm fires on every transient sensor spike.

7. NEVER skip `put-storage-configuration` — without it ingestion
   succeeds but data is not retained in the warm tier.

### Worked example — pump-motor model with OPC-UA ingestion

Scenario: industrial pump motor monitored via OPC-UA. Temperature sensor
feeds a measurement; shaft frequency is transformed to RPM; hourly
efficiency ratio is computed as a metric.

```text
SITEWISE: Pump-Motor Model (model-pm7a3x9)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Measurement properties: Temperature(DOUBLE,°C), MotorPower(DOUBLE,kW), ShaftFrequency(DOUBLE,Hz)
  [✓] Transform properties: RPM = ShaftFrequency * 60, TempF = Temperature * 9/5 + 32
  [✓] Metric properties: HourlyAvgEfficiency(AVG(RPM/MotorPower), 3600s), HourlyMaxTemp(MAX(Temperature), 3600s)
  [✓] Attribute properties: SerialNumber(STRING), Manufacturer(STRING), RatedPower(DOUBLE kW)
  [✓] Asset hierarchy: Pump Station Model → Pump-Motor Model via "Contains Motors"
  [✓] Asset(s): PM-001 (asset-pm8b4y2) — ACTIVE
  [✓] Gateway: Plant-Floor-Gateway (gw-3c7d8e1) — RUNNING
  [✓] OPC-UA source: PLC-MotorController — endpoint opc.tcp://10.20.30.40:4840, 3 node mappings
  [✓] Aliases: 3 set (/acme/plant1/pumpstation1/pm001/*)
  [✓] Ingestion path: OPC-UA → gateway → measurement properties (Temperature, MotorPower, ShaftFrequency)
  [✓] Storage: warm tier (365 days), disassociated data ENABLED
  [✓] Alarms: 2 threshold alarms (HighTemp>85C/5min, LowEfficiency<0.4/10min)
  [✓] Tags: Environment=production, Plant=Plant1, AssetType=PumpMotor
VERIFICATION_COMMANDS:
  aws iotsitewise describe-asset-model --asset-model-id model-pm7a3x9
  aws iotsitewise describe-asset --asset-id asset-pm8b4y2
  aws iotsitewise describe-gateway --gateway-id gw-3c7d8e1
  aws iotsitewise list-assets --filter TOPLEVEL --region us-east-1
```


→ Deploy commands for this worked example moved to [references/worked-examples.md](references/worked-examples.md#worked-example-deploy-commands--pump-motor-model) — create-asset-model with all four property types, wait + create-asset, alias setup, put-gateway-capability-configuration with nodePathMappings.
Load that reference on demand before executing this section.

### Decision tree

```text
What type of property is needed for this data point?
├─ Raw sensor data from OPC-UA or BatchPutAssetPropertyValue?
│  → MEASUREMENT (DOUBLE | INTEGER | STRING | BOOLEAN) — only ingest target
├─ Formula computed per data point in near-real-time?
│  → TRANSFORM (expression references measurement/transform properties)
├─ Time-windowed aggregation over multiple data points?
│  → METRIC (expression + tumbling interval in seconds)
└─ Static metadata about the asset (serial, manufacturer)?
   → ATTRIBUTE (no time series)

Need parent-child asset relationship?
  → Declare hierarchy in PARENT MODEL's assetModelHierarchies (NOT on asset)
  → Poll model until ACTIVE → create parent asset → associate-assets

Need external data ingestion?
  ├─ Via gateway (edge)?
  │  → OPC-UA source with nodePathMappings → set aliases on measurements
  └─ Via cloud API (IoT Core, Lambda)?
     → Set alias on measurement → BatchPutAssetPropertyValue by alias

Model stuck in CREATING?
  → Check transform/metric expressions for syntax errors or circular refs
```

## Error handling

→ Moved to [references/error-handling.md](references/error-handling.md#error-handling) — five failure deep dives (CREATING stall, gateway ERROR, empty dashboards, portal role, alarm never fires).
Load that reference on demand before executing this section.


## References (load on demand)

- [references/asset-models-and-properties.md](references/asset-models-and-properties.md) — property-type semantics and asset-model design detail, incl. Step 2 hierarchy CLI (create-asset-model with assetModelHierarchies, associate-assets).
- [references/gateway-and-ingestion.md](references/gateway-and-ingestion.md) — gateway architecture, OPC-UA and ingestion detail, incl. Step 3 gateway creation, Step 4 OPC-UA source JSON, Step 9 storage / CloudWatch CLI.
- [references/portals-dashboards-and-access.md](references/portals-dashboards-and-access.md) — Step 7 dashboard / portal creation CLI and Step 10 Identity Center SSO + access-policy wiring.
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset (three misconceptions), configuration dependency graph, expert heuristics (model inheritance, OPC-UA data flow, transform expressions), Step 11 recent features.
- [references/worked-examples.md](references/worked-examples.md) — worked-example deploy commands (Pump-Motor Model: create-asset-model with all four property types, aliases, put-gateway-capability-configuration).
- [references/error-handling.md](references/error-handling.md) — failure deep dives (model stuck CREATING, gateway ERROR, no dashboard data, portal role gaps, alarm never fires).

## Domain

AWS CloudOps / AWS IoT SiteWise Industrial Data Modeling & Asset
Management.

## AWS documentation

- **IoT SiteWise User Guide** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/
- **Asset models** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/asset-models.html
- **Asset properties** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/asset-properties.html
- **Transforms and metrics** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/transforms-and-metrics.html
- **Asset hierarchies** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/asset-hierarchies.html
- **SiteWise Edge gateways** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/sw-edge.html
- **OPC-UA sources** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/configure-sources.html
- **BatchPutAssetPropertyValue** — https://docs.aws.amazon.com/iot-sitewise/latest/APIReference/API_BatchPutAssetPropertyValue.html
- **Dashboards and portals** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/dashboards.html
- **Alarms** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/alarms.html
- **Identity Center integration** — https://docs.aws.amazon.com/iot-sitewise/latest/userguide/monitor-with-portals.html
