# Worked Examples — sitewise-asset-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Worked example deploy commands — Pump-Motor Model
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

