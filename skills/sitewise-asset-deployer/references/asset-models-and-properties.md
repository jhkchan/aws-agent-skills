# Asset Models and Property Types — AWS IoT SiteWise Asset Deployer

Deep reference on SiteWise asset model design: the four property types
(measurement, transform, metric, attribute), their data-flow semantics,
transform expression syntax, metric processing configurations, asset
hierarchy composition, and composite models. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Property type semantics

### Measurement properties

Measurement properties are the ONLY property type that receives
external data. OPC-UA sources and BatchPutAssetPropertyValue write to
measurements. Each measurement has a data type:

- `STRING` — textual sensor readings (e.g., "RUNNING", "FAULT")
- `INTEGER` — whole-number readings (e.g., cycle count, error code)
- `DOUBLE` — floating-point readings (e.g., temperature, pressure)
- `BOOLEAN` — binary state (e.g., running/stopped)

**Cannot derive from other properties.** Measurements are the source
of truth; transforms and metrics reference measurements.

### Transform properties

Transform properties apply a formula to the current value of
referenced measurements/transforms on EACH incoming data point. They
compute near-real-time derived values.

**Expression syntax:**

```text
# Arithmetic
TemperatureF = Temperature * 9/5 + 32
PressureBar = Pressure / 100

# Conditional
Status = if(Temperature > 80, 'OVERHEATING', if(Temperature > 60, 'WARNING', 'NORMAL'))

# Math functions
Efficiency = PowerOutput / max(WindSpeed * WindSpeed * WindSpeed, 0.1)
SignalStrength = abs(Measured - Expected)
LogValue = ln(Value)

# Trigonometry
PhaseAngle = atan(Imaginary / Real)
```

**Supported functions:**
- Arithmetic: `+`, `-`, `*`, `/`
- Math: `max`, `min`, `avg`, `sum`, `abs`, `sqrt`, `exp`, `ln`, `log`,
  `pow`, `round`, `ceil`, `floor`
- Trigonometry: `sin`, `cos`, `tan`, `asin`, `acos`, `atan`
- Conditional: `if`, `case`
- Time-series context: `earliest`, `latest`

**Key behavior:** transforms evaluate on every new data point of their
referenced properties. If a transform references two measurements with
different update frequencies, it evaluates when EITHER updates.

### Metric properties

Metric properties aggregate data over a specified time window. Unlike
transforms (which operate on each data point), metrics compute on a
fixed interval.

**Processing configuration:**

```json
{
  "computeLocation": "CLOUD",
  "path": [
    {
      "value": "Property1"
    }
  ]
}
```

**Metric definition with window:**

```json
{
  "id": "metric-hourly-avg-power",
  "name": "HourlyAvgPower",
  "type": "metric",
  "metricExpression": "avg(PowerOutput)",
  "window": {
    "tumbling": {
      "interval": "1h"
    }
  }
}
```

**Aggregation functions:** `avg`, `sum`, `min`, `max`, `count`,
`stddev`, and all functions available to transforms.

**Window types:**
- Tumbling — fixed, non-overlapping intervals (e.g., every 1 hour)
- The interval is specified as a duration string: `30s`, `5m`, `1h`,
  `1d`

### Attribute properties

Attributes store static metadata. They do NOT have time series data.

**Use cases:**
- Serial number, manufacturer, model number
- Rated capacity, installation date
- Geographic coordinates (as STRING)
- Configuration parameters

Attributes are set at asset creation time or updated via
`update-asset-property`. They do not trigger transform or metric
recalculations.

## Asset hierarchy design

### Hierarchy definition lives in the parent model

The hierarchy (parent-child relationship type) is defined in the
parent asset model, NOT on the asset instance:

```json
{
  "assetModelName": "Wind Farm",
  "assetModelHierarchies": [
    {
      "name": "Contains Turbines",
      "childAssetModelId": "model-wind-turbine-id"
    }
  ]
}
```

**Key constraint:** the `childAssetModelId` specifies WHICH child model
this hierarchy accepts. You cannot associate an asset of a different
model through this hierarchy.

### Associating children

After creating parent and child assets:

```bash
aws iotsitewise associate-assets \
  --asset-id "parent-asset-id" \
  --hierarchy-id "hierarchy-id-from-parent-model" \
  --child-asset-id "child-asset-id"
```

### Hierarchy-level metrics

Parent models can define metrics that aggregate across all child
assets in a hierarchy. This is SiteWise's most powerful feature for
fleet-level monitoring:

```json
{
  "name": "TotalFarmPower",
  "type": "metric",
  "metricExpression": "sum(PowerOutput)",
  "window": {
    "tumbling": { "interval": "5m" }
  }
}
```

This metric automatically sums the PowerOutput from ALL child assets
(wind turbines) associated with the parent (wind farm), every 5
minutes.

## Composite models (2023-2024 feature)

Composite models enable grouping related properties and alarms into
reusable units that can be included in multiple asset models:

```json
{
  "assetModelCompositeModels": [
    {
      "name": "ElectricalModule",
      "type": "aws.sitewise.composite",
      "properties": [
        {"name": "Voltage", "type": "measurement", "dataType": "DOUBLE"},
        {"name": "Current", "type": "measurement", "dataType": "DOUBLE"},
        {"name": "PowerFactor", "type": "transform", "expression": "Voltage * Current"}
      ]
    }
  ]
}
```

This "ElectricalModule" can be included in a Pump model, a Motor
model, and a Transformer model — each inherits the same electrical
properties and derived calculations.

## Terraform asset model example

```hcl
resource "aws_iotsitewise_asset_model" "turbine" {
  asset_model_name = "Wind Turbine"

  asset_model_property {
    name      = "WindSpeed"
    data_type = "DOUBLE"
    unit      = "m/s"
    type      = "measurement"
  }

  asset_model_property {
    name      = "Temperature"
    data_type = "DOUBLE"
    unit      = "C"
    type      = "measurement"
  }

  asset_model_property {
    name      = "TemperatureF"
    data_type = "DOUBLE"
    unit      = "F"
    type      = "transform"
    expression = "Temperature * 9/5 + 32"
  }

  asset_model_property {
    name      = "HourlyAvgPower"
    data_type = "DOUBLE"
    unit      = "kW"
    type      = "metric"
    expression = "avg(PowerOutput)"
    interval  = "1h"
  }

  asset_model_property {
    name      = "Manufacturer"
    data_type = "STRING"
    type      = "attribute"
  }

  asset_model_hierarchy {
    name                = "Contains Turbines"
    child_asset_model_id = aws_iotsitewise_asset_model.turbine.id
  }
}
```
