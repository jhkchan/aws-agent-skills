---
name: sitewise-asset-deployer
description: >-
  Deploys AWS IoT SiteWise industrial data infrastructure with production
  defaults: asset model creation (measurement, metric, transform,
  attribute property types), asset hierarchy (parent-child composition),
  SiteWise Edge gateway on IoT Greengrass, data ingestion via
  BatchPutAssetPropertyValue, OPC-UA source configuration, asset property
  aliases, dashboards, threshold alarms, warm-tier storage, and Identity
  Center portal access. Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when modeling industrial assets, ingesting
  OPC-UA telemetry, creating dashboards, configuring alarms, deploying
  Edge gateways, or setting up aliases. Triggers: create iot sitewise
  asset model, sitewise asset hierarchy, sitewise edge gateway, opc-ua
  source sitewise, batchputassetpropertyvalue, sitewise dashboard
  portal, sitewise alarm, asset property alias, sitewise identity center.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with iot-sitewise
  access (and greengrassv2 access if deploying Edge gateway). Works
  with Terraform aws_iotsitewise_asset_model / aws_iotsitewise_asset /
  aws_iotsitewise_gateway resources and CloudFormation
  AWS::IoTSiteWise::AssetModel / Asset / Gateway templates.
keywords:
  - aws
  - iot sitewise
  - asset model
  - asset hierarchy
  - cloudops
  - deploy
  - provisioning
  - opc-ua
  - measurement
  - transform
  - metric
  - attribute
  - gateway
  - greengrass
  - batchputassetpropertyvalue
  - alias
  - dashboard
  - portal
  - alarm
  - identity center
tags:
  - aws
  - iot-sitewise
  - cloudops
  - deploy
  - industrial
  - provisioning
  - asset-model
  - opc-ua
  - edge-gateway
  - dashboard
  - alarm
  - identity-center
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
    - iot-sitewise
    - cloudops
    - deploy
    - industrial
    - provisioning
    - asset-model
    - opc-ua
    - edge-gateway
    - dashboard
    - alarm
    - identity-center
  dependencies:
    - aws-orchestrator
  keywords:
    - create iot sitewise asset model
    - sitewise asset hierarchy
    - sitewise edge gateway
    - opc-ua source sitewise
    - batchputassetpropertyvalue
    - sitewise dashboard portal
    - sitewise alarm
    - asset property alias
    - sitewise identity center
  when_to_use: >-
    Invoke when the user wants to model industrial assets in AWS IoT
    SiteWise, create asset models with measurement/metric/transform/
    attribute properties, build parent-child asset hierarchies, deploy
    SiteWise Edge gateways on IoT Greengrass, configure OPC-UA source
    data ingestion, set up asset property aliases for external data
    feeds, create dashboards and portals, configure threshold-based
    alarms, or integrate SiteWise with CloudWatch and Identity Center.
    Do NOT invoke for AWS IoT Core (device connectivity), AWS IoT
    TwinMaker (digital twins), or AWS IoT Events (event detection)
    unless the task specifically involves SiteWise asset modeling.
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

**One-line takeaway:** IoT SiteWise models physical industrial assets
as digital asset models. Each model has four property types:
measurement (raw sensor data), transform (formula-based derived
values), metric (aggregated computations), and attribute (static
metadata). Models are composed into hierarchies for parent-child
relationships (e.g., a factory contains production lines, each line
contains machines). Data flows from OPC-UA sources through a gateway
(or via direct BatchPutAssetPropertyValue API calls) to asset
properties, which are then visualized in dashboards and monitored by
alarms.

Three misconceptions dominate SiteWise misdesign at provisioning time:

- **"All properties are the same."** They are not. Measurement
  properties capture raw sensor data (temperature, pressure, RPM) and
  are the ONLY property type that receives external data directly.
  Transform properties apply formulas to measurements in near-real-time
  (e.g., Celsius-to-Fahrenheit, efficiency calculations). Metric
  properties aggregate data over time windows (e.g., hourly average,
  daily total). Attribute properties store static metadata (serial
  number, manufacturer, location). Using the wrong property type breaks
  data flow: you cannot ingest data into a transform or metric, and
  attributes do not support time series at all.

- **"The gateway can collect from any source without configuration."**
  It cannot. A SiteWise Edge gateway running on IoT Greengrass
  requires explicit OPC-UA source configuration: the server endpoint,
  node ID paths (NamePath or NodeName), and the mapping of each OPC-UA
  node to a specific asset model property. Without the node-to-property
  mapping, the gateway connects to the OPC-UA server but ingests
  nothing. The mapping is the #1 cause of "my gateway is connected but
  no data appears" tickets.

- **"Asset property aliases are optional."** They are required for the
  direct ingestion path. BatchPutAssetPropertyValue can ingest data
  using either a property ID or an alias. Aliases are the ONLY way to
  ingest data into a property without first resolving the property ID
  (critical for high-throughput external ingestion from IoT Core rules
  or Lambda functions). Without aliases, external ingestion requires a
  prior DescribeAsset lookup to get the property ID — an extra API call
  per asset that throttles at scale.

## Configuration dependency graph (novel heuristic)

SiteWise configurations are NOT independent. The asset model must exist
before assets. The gateway must exist before OPC-UA source
configuration. Aliases must be set before external ingestion. Dashboards
need projects; portals need projects. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Asset model | None (standalone definition) | model status must be ACTIVE before asset creation; a model in CREATING state blocks asset creation | assets and hierarchies |
| Asset (from model) | asset model must be ACTIVE | asset status must be ACTIVE before data ingestion or alias operations | data ingestion, aliases, dashboards |
| Asset hierarchy | parent and child asset models both exist; hierarchy definition is IN the model (not the asset) | hierarchy child model must be specified in the parent model's hierarchy definitions; adding a hierarchy AFTER model creation requires a model update or new version | parent-child composition |
| Gateway (Edge on Greengrass) | Greengrass core device exists; gateway platform is IoT Greengrass V2 | gateway must be in SYNCING or RUNNING state before source configuration | OPC-UA source configuration |
| OPC-UA source | gateway exists and is active | source must be DISCONNECTED to modify; NamePath/NodeName mapping must reference valid OPC-UA node IDs; incorrect mappings silently ingest nothing | data flow to asset properties |
| Asset property alias | asset and property exist | alias must be unique within the AWS account; format convention is `/company/site/asset/property` | external ingestion via BatchPutAssetPropertyValue without property ID lookup |
| Dashboard project | None (standalone) | project must exist before creating dashboards or portals within it | dashboards and portals |
| Dashboard | project exists; asset exists (for data binding) | dashboard widgets bind to asset property IDs; broken bindings show no data | visualization |
| Portal | project exists; Identity Center store configured | portal requires Identity Center (SSO) — without it, portal creation fails; portal access requires per-user project role assignment | web-based visualization access |
| Alarm (threshold) | asset and property exist; alarm is defined at the MODEL level (propagates to assets) | alarm state changes are detected by comparing the property value against threshold rules; alarm must be enabled on the specific asset instance | operational alerting |

**The hierarchy-in-the-model row is the one a baseline model misses.**
Asset hierarchies are defined in the parent asset MODEL, not in the
asset instance. You cannot create a parent-child relationship between
two arbitrary assets at runtime — the relationship must be declared in
the model's `assetModelHierarchies` array. This means changing the
hierarchy structure requires a new model version. The procedure below
forces an explicit hierarchy design decision at model creation time.

**Cross-dependency gotchas:**
- A model must be in ACTIVE status before you can create an asset from
  it. Model creation is asynchronous; poll `describe-asset-model` until
  status is ACTIVE.
- Hierarchy definitions are in the parent model. If you discover a new
  parent-child relationship after assets are created, you must create a
  new model version with the hierarchy, then update assets to the new
  version.
- OPC-UA source configuration maps OPC-UA nodes to asset model
  PROPERTIES (not assets). The property must exist in the model
  referenced by the gateway's capability configuration.
- Aliases must be unique across the entire AWS account. Duplicate
  aliases cause BatchPutAssetPropertyValue to write to the wrong asset.
- Alarms are defined at the MODEL level. Each asset created from the
  model inherits the alarm definition, but the alarm must be ENABLED
  per-asset (default state is enabled, but can be overridden).

## Expert heuristic: asset model inheritance for standardization

A baseline model says "create one model per asset." The correct
heuristic recognizes that SiteWise's power comes from model reuse —
define a model once, create many assets from it, and every asset
inherits the same properties, transforms, metrics, and alarm
definitions.

```text
Standardization model:
  Wind Turbine Model (defined once)
    ├── measurement: WindSpeed (m/s), RPM, PowerOutput (kW), Temperature (C)
    ├── transform: TemperatureF = Temperature * 9/5 + 32
    ├── transform: Efficiency = PowerOutput / (WindSpeed^3 * 0.5 * rho * A)
    ├── metric: HourlyAvgPower = AVG(PowerOutput, 1h)
    ├── metric: DailyTotalEnergy = SUM(PowerOutput, 24h)
    ├── attribute: Manufacturer, SerialNumber, RatedCapacity
    ├── alarm: HighTemp (Temperature > 80C for 5 minutes)
    └── alarm: LowEfficiency (Efficiency < 0.3 for 15 minutes)

  Assets created from the model:
    ├── Wind Turbine #1 (WT-001) — inherits all properties, transforms, metrics, alarms
    ├── Wind Turbine #2 (WT-002) — inherits all properties, transforms, metrics, alarms
    └── Wind Turbine #3 (WT-003) — inherits all properties, transforms, metrics, alarms

  Hierarchy:
    Wind Farm Model (parent)
      └── hierarchy: "contains" → Wind Turbine Model (child)

    Wind Farm Asset (WF-North)
      └── children: WT-001, WT-002, WT-003
```

**Key implication:** model inheritance ensures every asset has the
same property definitions, derived calculations, and alarm rules. This
eliminates drift between assets of the same type and enables fleet-wide
aggregation metrics at the hierarchy level.

## Expert heuristic: OPC-UA data flow to asset properties

The data flow from an OPC-UA source to a SiteWise asset property
traverses multiple components. Understanding this path is essential for
troubleshooting "no data" issues.

```text
OPC-UA data flow:
  1. OPC-UA server (industrial PLC, SCADA, or gateway device)
     → exposes a node tree: Objects/Device/Temperature = 72.5
  2. SiteWise Edge gateway (on Greengrass core device)
     → connects to OPC-UA server via endpoint (opc.tcp://...)
     → OPC-UA source configuration maps:
       NodeName "Objects/Device/Temperature" → property "Temperature"
       (in asset model referenced by gateway's capability)
  3. Gateway reads the OPC-UA node value
     → writes to SiteWise via BatchPutAssetPropertyValue
     → targets the property via the alias or property ID
  4. SiteWise stores the data point in the time series
     → property is a measurement → stores raw value with timestamp
     → transform/metric properties derive from measurements
  5. Dashboard widgets bound to the property display the value
     → alarm rules evaluate the property value against thresholds
```

**Key implication:** the OPC-UA node-to-property mapping is the critical
link. If the mapping references the wrong node path, the gateway reads
a value but writes it to the wrong property (or fails silently). Always
verify the NamePath/NodeName matches the OPC-UA server's address space.

## Expert heuristic: transform expressions for derived metrics

Transform properties use SQL-like expressions to derive values from
measurement properties in near-real-time. The expression syntax follows
specific rules that differ from standard SQL.

```text
Transform expression syntax:
  - References to measurement properties use their property IDs or names
  - Supports: arithmetic (+, -, *, /), math functions (max, min, avg, sum,
    abs, sqrt, exp, ln, log, pow, round, ceil, floor), trigonometry (sin,
    cos, tan, asin, acos, atan), conditional (if, case)
  - Supports time-series functions: earliest, latest, deref (for multi-
    data type handling)
  - NO direct SQL queries; the expression operates on the current value
    of the referenced properties

Examples:
  TemperatureF = Temperature * 9/5 + 32
  Efficiency = PowerOutput / (max(WindSpeed * WindSpeed * WindSpeed, 0.1) * 0.5 * 1.225 * 7853)
  Status = if(Temperature > 80, 'OVERHEATING', if(Temperature > 60, 'WARNING', 'NORMAL'))
  QualityAdjustedPower = PowerOutput * if(Quality == 'GOOD', 1.0, 0.5)
```

**Key implication:** transforms compute on each incoming data point
(near-real-time). For time-windowed aggregations (hourly average, daily
total), use METRIC properties instead — they use the same expression
syntax but aggregate over a specified time interval and processing
configuration.

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

Asset hierarchies define parent-child relationships between assets.
Hierarchies are defined in the PARENT asset model, not in the asset
instance.

**Hierarchy definition in the parent model:**

```bash
# Create parent model with hierarchy definition
aws iotsitewise create-asset-model \
  --asset-model-name "Wind Farm" \
  --asset-model-properties file://wind-farm-properties.json \
  --asset-model-hierarchies '[
    {
      "name": "Contains Turbines",
      "childAssetModelId": "wind-turbine-model-id"
    }
  ]'
```

**Create parent asset and associate children:**

```bash
# Create the parent asset (from parent model)
FARM_ID=$(aws iotsitewise create-asset \
  --asset-name "Wind Farm North" \
  --asset-model-id "$FARM_MODEL_ID" \
  --query 'assetId' --output text)

# Wait for asset to become ACTIVE (poll describe-asset)
aws iotsitewise wait asset-active --asset-id "$FARM_ID"

# Associate child assets via the hierarchy
aws iotsitewise associate-assets \
  --asset-id "$FARM_ID" \
  --hierarchy-id "$HIERARCHY_ID" \
  --child-asset-id "$TURBINE_1_ID"

aws iotsitewise associate-assets \
  --asset-id "$FARM_ID" \
  --hierarchy-id "$HIERARCHY_ID" \
  --child-asset-id "$TURBINE_2_ID"
```

**Critical:** the hierarchy definition (name + child model ID) lives in
the parent model. You cannot create a hierarchy relationship between
arbitrary assets at runtime — the parent model must declare which child
model it accepts.

## Step 3 — Gateway and SiteWise Edge

SiteWise Edge gateway runs on IoT Greengrass V2 and collects data from
industrial sources (OPC-UA, Modbus) at the edge, then forwards to
SiteWise in the cloud.

**Create a gateway:**

```bash
GATEWAY_ID=$(aws iotsitewise create-gateway \
  --gateway-name "Factory Floor Gateway" \
  --gateway-platform greengrassV2CoreDevice=MyGreengrassCoreDevice \
  --query 'gatewayId' --output text)
```

**Gateway states:**
- `PENDING` — created, not yet syncing
- `SYNCING` — downloading configuration from SiteWise
- `RUNNING` — active, collecting and forwarding data
- `ERROR` — check gateway logs on the Greengrass core device

**Gateway capability:** the gateway runs the "SiteWise Edge" IoT
Greengrass component (`aws.iotsitewise.EdgeConnector`), which is
auto-deployed to the Greengrass core device when the gateway is
created.

## Step 4 — OPC-UA source configuration

OPC-UA sources are configured per-gateway. Each source connects to an
OPC-UA server and maps its nodes to asset model properties.

**Create an OPC-UA source:**

```bash
SOURCE_ID=$(aws iotsitewise create-gateway \
  --gateway-id "$GATEWAY_ID" \
  --gateway-capability-namespace "iotsitewise:opcuacollector:1" \
  --gateway-capability-configuration file://opcua-source-config.json \
  --query 'gatewayCapabilitySummaries[0].capabilitySyncStatus' --output text)
```

**OPC-UA source configuration JSON structure:**

```json
{
  "sources": [
    {
      "name": "PLC-Primary",
      "endpoint": {
        "certificateTrust": {
          "type": "TrustAny"
        },
        "endpointUri": "opc.tcp://192.168.1.100:4840",
        "securityPolicy": "BASIC256",
        "messageSecurityMode": "SIGN_AND_ENCRYPT"
      },
      "nodePathMappings": [
        {
          "assetPropertyAlias": "/factory/line1/turbine1/temperature",
          "nodePath": "Objects/Device/Temperature"
        },
        {
          "assetPropertyAlias": "/factory/line1/turbine1/rpm",
          "nodePath": "Objects/Device/RPM"
        }
      ],
      "measurementDataStreamPrefix": "/factory/line1"
    }
  ]
}
```

**Critical:** the `nodePathMappings` array maps OPC-UA node paths to
asset property aliases. Each alias must match an alias set on an asset
property (Step 6). The gateway reads the OPC-UA node and writes the
value to the matching alias.

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

SiteWise dashboards visualize asset property data. Dashboards live in
projects. Portals aggregate projects and provide web-based access.

**Create a project:**

```bash
PROJECT_ID=$(aws iotsitewise create-project \
  --project-name "Wind Farm Monitoring" \
  --portal-id "$PORTAL_ID" \
  --query 'projectId' --output text)
```

**Create a dashboard:**

```bash
DASHBOARD_ID=$(aws iotsitewise create-dashboard \
  --dashboard-name "Turbine WT-001 Overview" \
  --project-id "$PROJECT_ID" \
  --dashboard-definition file://dashboard-definition.json \
  --query 'dashboardId' --output text)
```

**Dashboard definition JSON** contains widget configurations (line
charts, bar charts, KPIs, status grids) bound to asset property IDs.

**Create a portal (requires Identity Center):**

```bash
PORTAL_ID=$(aws iotsitewise create-portal \
  --portal-name "Acme Wind Farm Portal" \
  --portal-contact-email "ops@acme.com" \
  --role-arn "$PORTAL_ROLE_ARN" \
  --portal-auth-mode "IAM" \
  --alarms-enabled \
  --query 'portalId' --output text)
```

**Critical:** portal creation requires an IAM role that SiteWise
assumes to read asset data on behalf of portal users. The role must
have `iotsitewise:BatchGetAssetPropertyAggregates`,
`iotsitewise:BatchGetAssetPropertyValue`, and
`iotsitewise:BatchGetAssetPropertyValueHistory` permissions.

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

SiteWise stores measurement data in its own time series storage (the
SiteWise warm tier). Data is queryable via
`BatchGetAssetPropertyValueHistory` (historical) and
`BatchGetAssetPropertyAggregates` (aggregated).

**Storage configuration:**

```bash
aws iotsitewise put-storage-configuration \
  --storage-type "SITE_WISE" \
  --disassociated-data-storage "ENABLED" \
  --retention-period "{\"warmRetentionInDays\": 365}"
```

**Warm tier:** stores the last N days of data (configurable, default
depends on tier). Cold storage (SiteWise Edge or S3 export) is used
for longer retention.

**CloudWatch integration:** SiteWise publishes operational metrics to
CloudWatch, including:
- Ingestion metrics: `IngestionState` (Active/ActiveWithFailures),
  `AssetPropertyReportedValueCount`.
- Gateway metrics: `GatewayConnectivity`, `GatewayDataIngress`.

These metrics enable CloudWatch alarms for ingestion health monitoring.

## Step 10 — Identity Center for portal access

SiteWise portals use Identity Center (SSO) for user authentication when
`portalAuthMode` is `SSO`.

**Configure Identity Center for portal:**

```bash
# Portal with SSO auth mode
PORTAL_ID=$(aws iotsitewise create-portal \
  --portal-name "Acme Wind Farm Portal" \
  --portal-contact-email "ops@acme.com" \
  --role-arn "$PORTAL_ROLE_ARN" \
  --portal-auth-mode "SSO" \
  --query 'portalId' --output text)
```

**Assign users/groups to portal projects:**

```bash
# Assign a user or group to a project with a role
aws iotsitewise create-access-policy \
  --access-policy-identity '{
    "iam": {"arn": "arn:aws:iam::123456789012:role/SiteWisePortalViewer"}
  }' \
  --access-policy-permission '{
    "project": {"permission": "VIEWER", "projectId": "'"$PROJECT_ID"'"}
  }' \
  --access-policy-resource '{
    "portal": {"id": "'"$PORTAL_ID"'"}
  }'
```

**Project roles:** `ADMINISTRATOR` (full control), `EDITOR` (create/edit
dashboards), `VIEWER` (read-only).

**Critical:** portal access requires both an Identity Center user AND
an access policy. Without the access policy, the user can authenticate
but sees no projects.

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Asset model composite models (2023-2024):** Composite models enable
  grouping related properties and alarms into reusable units. A
  composite model can be included in multiple asset models, enabling
  modular model composition (e.g., an "ElectricalModule" with voltage,
  current, power measurements used across multiple asset types).

- **SiteWise Edge Modbus support (2023-2024):** In addition to OPC-UA,
  SiteWise Edge gateways now support Modbus TCP sources, broadening
  industrial protocol coverage for legacy devices.

- **BatchPutAssetPropertyValue performance improvements (2023-2024):**
  Increased throughput limits for BatchPutAssetPropertyValue, supporting
  higher data ingestion rates for large-scale industrial deployments.

- **Dashboard governance (2024-2025):** Dashboard definitions now
  support versioning, enabling controlled updates to production
  dashboards without disrupting viewers.

- **Alarm advanced parameters (2024-2025):** Alarms now support
  hysteresis thresholds (different thresholds for alarm set and alarm
  clear), reducing alarm flapping for noisy signals.

- **Identity Center integration maturity (2024-2025):** Simplified
  portal SSO setup with automatic Identity Center group synchronization
  for project access policies.

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

Deploy commands:

```bash
# 1. Create the asset model with all four property types
aws iotsitewise create-asset-model \
  --asset-model-name "Pump-Motor Model" \
  --asset-model-properties '[
    {"name":"Temperature","dataType":"DOUBLE","type":{"measurement":{}}},
    {"name":"MotorPower","dataType":"DOUBLE","type":{"measurement":{}}},
    {"name":"ShaftFrequency","dataType":"DOUBLE","type":{"measurement":{}}},
    {"name":"RPM","dataType":"DOUBLE","type":{"transform":{"expression":"ShaftFrequency * 60","variables":[{"name":"ShaftFrequency","value":{"propertyId":"<shaft-freq-prop-id>"}}]}}},
    {"name":"TempF","dataType":"DOUBLE","type":{"transform":{"expression":"Temperature * 9 / 5 + 32","variables":[{"name":"Temperature","value":{"propertyId":"<temp-prop-id>"}}]}}},
    {"name":"HourlyAvgEfficiency","dataType":"DOUBLE","type":{"metric":{"expression":"avg(RPM / MotorPower)","variables":[{"name":"RPM","value":{"propertyId":"<rpm-prop-id>"}},{"name":"MotorPower","value":{"propertyId":"<motorpower-prop-id>"}}],"window":{"tumbling":{"interval":"1h"}}}}},
    {"name":"SerialNumber","dataType":"STRING","type":{"attribute":{}}},
    {"name":"Manufacturer","dataType":"STRING","type":{"attribute":{}}}
  ]'

# 2. Wait for model ACTIVE, then create asset
aws iotsitewise wait asset-model-active --asset-model-id model-pm7a3x9
aws iotsitewise create-asset --asset-name "PM-001" --asset-model-id model-pm7a3x9

# 3. Set aliases on measurement properties for OPC-UA ingestion
aws iotsitewise update-asset-property \
  --asset-id asset-pm8b4y2 \
  --property-id <temperature-prop-id> \
  --property-alias "/acme/plant1/pumpstation1/pm001/temperature"

# 4. Configure OPC-UA source on gateway with nodePathMappings
aws iotsitewise put-gateway-capability-configuration \
  --gateway-id gw-3c7d8e1 \
  --capability-namespace "iotsitewise:opcuacollector:1" \
  --capability-configuration '{
    "sources": [{
      "name": "PLC-MotorController",
      "endpoint": {
        "certificateTrust": {"type": "TrustAny"},
        "endpointUri": "opc.tcp://10.20.30.40:4840",
        "securityPolicy": "BASIC256",
        "messageSecurityMode": "SIGN_AND_ENCRYPT"
      },
      "nodePathMappings": [
        {"assetPropertyAlias": "/acme/plant1/pumpstation1/pm001/temperature", "nodePath": "Objects/PumpMotor/Temperature"},
        {"assetPropertyAlias": "/acme/plant1/pumpstation1/pm001/motorpower", "nodePath": "Objects/PumpMotor/Power"},
        {"assetPropertyAlias": "/acme/plant1/pumpstation1/pm001/shaftfrequency", "nodePath": "Objects/PumpMotor/Frequency"}
      ]
    }]
  }'
```

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

### Asset model stuck in CREATING state
- The model is being validated. If it stays in CREATING for more than a
  minute, check for invalid transform/metric expressions or circular
  property references. A model in CREATING for several minutes likely
  has a validation error — check `describe-asset-model` for error
  details.

### Gateway shows ERROR state
- Check the Greengrass core device logs on the edge device. Common
  causes: OPC-UA server unreachable, certificate trust failure,
  insufficient Greengrass permissions, or the core device is offline.

### No data appears in dashboards despite ingestion
- Verify the asset property alias matches the alias used in the
  ingestion call (or the OPC-UA nodePathMapping). Check
  BatchPutAssetPropertyValue error entries. Confirm the property is a
  measurement (transforms/metrics derive from measurements, not from
  external data). Verify the asset status is ACTIVE.

### Portal dashboards show no data
- The portal IAM role lacks permissions to read asset data. Verify the
  role has `iotsitewise:BatchGetAssetPropertyAggregates`,
  `BatchGetAssetPropertyValue`, and `BatchGetAssetPropertyValueHistory`
  on the relevant assets. Also check that the access policy assigns
  the user/group to the correct project.

### Alarm never fires despite threshold breach
- The alarm duration (`durationInMinutes`) may be too long for the data
  frequency. If data arrives every 60 seconds but the duration is 10
  minutes, the alarm needs 10 minutes of sustained breach. Also verify
  the alarm references the correct property ID and comparison operator.

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
