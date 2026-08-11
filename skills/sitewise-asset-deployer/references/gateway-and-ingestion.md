# Gateway and Data Ingestion — AWS IoT SiteWise Asset Deployer

Deep reference on SiteWise Edge gateways (Greengrass V2 platform, OPC-UA
source configuration, node-to-alias mappings), data ingestion paths
(BatchPutAssetPropertyValue via alias vs property ID, OPC-UA via
gateway), asset property aliases (naming conventions, uniqueness),
storage configuration, and CloudWatch integration. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## SiteWise Edge gateway architecture

### Components

```text
Industrial Device (PLC/SCADA)
  → OPC-UA Server (opc.tcp://...)
    → SiteWise Edge Connector (IoT Greengrass component)
      → OPC-UA Collector (reads nodes per configuration)
        → SiteWise Cloud (BatchPutAssetPropertyValue)
          → Asset Property (measurement)
            → Transforms/Metrics derive
              → Dashboards/Alarms
```

### Gateway creation

```bash
GATEWAY_ID=$(aws iotsitewise create-gateway \
  --gateway-name "Factory Floor Gateway" \
  --gateway-platform greengrassV2CoreDevice=GreengrassCore-001 \
  --query 'gatewayId' --output text)
```

**Prerequisites:**
- Greengrass V2 core device registered and online
- Core device has the `aws.iotsitewise.EdgeConnector` component
  deployed (auto-deployed when gateway is created)
- IAM permissions for the Greengrass core device role to call
  `iotsitewise:BatchPutAssetPropertyValue`

### Gateway states

| State | Meaning | Action needed |
|---|---|---|
| PENDING | Created, not yet syncing | Wait for Greengrass deployment |
| SYNCING | Downloading configuration | Wait |
| RUNNING | Active, collecting data | None — healthy |
| ERROR | Something failed | Check Greengrass logs on device |

## OPC-UA source configuration

### Source configuration structure

The OPC-UA source configuration is a JSON document applied to the
gateway's capability namespace:

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
      "measurementDataStreamPrefix": "/factory/line1",
      "serializationProcessCount": 1
    }
  ]
}
```

### Node path formats

SiteWise supports two node identification formats:

- **NamePath** — the human-readable path of node display names
  (e.g., `Objects/Device/Temperature`). Easier to configure but
  depends on display names not changing.

- **NodeId** — the OPC-UA NodeId (e.g.,
  `ns=2;s=MyTemperature.Variable`). More stable but requires
  knowledge of the OPC-UA address space.

### Certificate trust

| Trust type | When to use | Security risk |
|---|---|---|
| TrustAny | Development/testing | Accepts any certificate (MITM risk) |
| TrustProvidedCertificates | Production | Only trusts specified certificates |

For production, always use `TrustProvidedCertificates` with the
OPC-UA server's CA certificate.

### Common OPC-UA pitfalls

1. **Wrong node path.** The gateway connects but reads nothing. Verify
   the path matches the OPC-UA server's address space using a tool
   like UaExpert.

2. **Certificate trust failure.** The gateway cannot establish the
   OPC-UA session. Use `TrustAny` for testing, then switch to
   `TrustProvidedCertificates` with the correct CA cert.

3. **Missing nodePathMappings.** Without mappings, the gateway has no
   nodes to read. This is the #1 cause of "gateway connected but no
   data."

4. **Alias mismatch.** The `assetPropertyAlias` in the source config
   must match the alias set on the asset property (via
   `update-asset-property`). A mismatch means data goes nowhere.

## Data ingestion via BatchPutAssetPropertyValue

### Alias-based ingestion (recommended)

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

**Advantages of alias-based ingestion:**
- No prior DescribeAsset call needed to resolve property ID
- IoT Core rule SQL actions can write directly to aliases
- Lambda functions can use a pre-configured alias without asset
  lookup overhead
- Scales better (one less API call per data point)

### Property ID-based ingestion

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

**When to use property ID-based ingestion:**
- Low-volume ingestion (< 100 assets)
- When aliases are not set
- When the asset/property ID is already known (cached)

### Batch limits

- Maximum 10 entries per API call
- Maximum 10 property values per entry
- Maximum 100 total property values per call
- For high throughput: batch via Kinesis + Lambda with parallel calls

### Quality values

| Quality | Meaning | Use case |
|---|---|---|
| GOOD | Reliable data | Normal sensor readings |
| BAD | Unreliable data | Sensor fault, communication error |
| UNCERTAIN | Data may be unreliable | Calibration drift, stale data |

Transform and metric properties only compute when the source
measurement quality is GOOD (by default).

## Asset property aliases

### Setting aliases

```bash
aws iotsitewise update-asset-property \
  --asset-id "$ASSET_ID" \
  --property-id "$PROPERTY_ID" \
  --property-alias "/factory/line1/turbine1/temperature" \
  --property-notification-state ENABLED
```

### Naming convention

Use a hierarchical path that mirrors the physical or logical topology:

```text
/<company>/<site>/<area>/<equipment>/<property>

Examples:
  /acme/hoover/line1/turbine1/temperature
  /acme/hoover/line1/turbine1/rpm
  /acme/hoover/line1/turbine1/powerOutput
  /acme/hoover/line2/pump1/flowRate
```

### Uniqueness constraint

Aliases must be unique across the entire AWS account. Two assets
cannot share the same alias. Duplicate aliases cause
BatchPutAssetPropertyValue to write to whichever asset claimed the
alias first — leading to silent data misdirection.

**Verification before setting aliases:**

```bash
# List all aliases in the account (paginated)
aws iotsitewise list-asset-models --query 'assetModelSummaries[*].id' --output text | \
  tr '\t' '\n' | while read model_id; do
    aws iotsitewise describe-asset-model --asset-model-id "$model_id" \
      --query 'assetModelProperties[?alias].[alias,name]' --output text
  done
```

## Storage configuration

### Warm tier

```bash
aws iotsitewise put-storage-configuration \
  --storage-type "SITE_WISE" \
  --disassociated-data-storage "ENABLED" \
  --retention-period "{\"warmRetentionInDays\": 365}"
```

| Parameter | Default | Range | Notes |
|---|---|---|---|
| storage-type | SITE_WISE | SITE_WISE | SiteWise-managed warm tier |
| disassociated-data-storage | DISABLED | ENABLED/DISABLED | Enables ingestion via alias without prior asset association |
| warmRetentionInDays | 90 | 30-3650 | Days of data retained in the warm tier |

**Disassociated data storage:** when ENABLED, data ingested via alias
is stored even if no asset property is associated with the alias yet.
This is critical for use cases where aliases are set before assets are
created (e.g., during migration from another historian).

## CloudWatch integration

SiteWise publishes operational metrics to CloudWatch automatically:

| Metric namespace | Metric | Description |
|---|---|---|
| AWS/IoTSiteWise | IngestionState | Active or ActiveWithFailures |
| AWS/IoTSiteWise | AssetPropertyReportedValueCount | Number of data points ingested per property |
| AWS/IoTSiteWise | GatewayConnectivity | Gateway online/offline (per gateway) |
| AWS/IoTSiteWise | GatewayDataIngress | Bytes ingressed per gateway |

**Recommended CloudWatch alarms:**

```bash
# Alarm on ingestion failures
aws cloudwatch put-metric-alarm \
  --alarm-name "SiteWise-IngestionFailure" \
  --namespace "AWS/IoTSiteWise" \
  --metric-name "IngestionState" \
  --dimensions "Name=AccountId,Value=123456789012" \
  --statistic "Maximum" --period 300 --threshold 0 \
  --comparison-operator "LessThanThreshold" --evaluation-periods 1

# Alarm on gateway offline
aws cloudwatch put-metric-alarm \
  --alarm-name "SiteWise-GatewayOffline" \
  --namespace "AWS/IoTSiteWise" \
  --metric-name "GatewayConnectivity" \
  --dimensions "Name=GatewayId,Value=gw-xxx" \
  --statistic "Minimum" --period 60 --threshold 1 \
  --comparison-operator "LessThanThreshold" --evaluation-periods 5
```

## Terraform gateway example

```hcl
resource "aws_iotsitewise_gateway" "plant_gateway" {
  gateway_name = "Plant Gateway"
  gateway_platform {
    greengrass_v2 {
      core_device_thing_name = "GreengrassCore-001"
    }
  }

  gateway_capability_summaries {
    capability_namespace = "iotsitewise:opcuacollector:1"
  }
}

# OPC-UA source configuration applied as gateway capability
resource "aws_iotsitewise_gateway_capability" "opcua_source" {
  gateway_id              = aws_iotsitewise_gateway.plant_gateway.id
  capability_namespace    = "iotsitewise:opcuacollector:1"
  capability_configuration = jsonencode({
    sources = [
      {
        name = "PLC-Primary"
        endpoint = {
          certificateTrust = { type = "TrustAny" }
          endpointUri      = "opc.tcp://10.0.1.50:4840"
          securityPolicy   = "BASIC256"
          messageSecurityMode = "NONE"
        }
        nodePathMappings = [
          { assetPropertyAlias = "/plant/area1/pump1/flowRate", nodePath = "Objects/Pump/FlowRate" },
          { assetPropertyAlias = "/plant/area1/pump1/pressure", nodePath = "Objects/Pump/Pressure" }
        ]
      }
    ]
  })
}
```
