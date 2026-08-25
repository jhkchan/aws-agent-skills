# Advanced Patterns — sitewise-asset-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

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

