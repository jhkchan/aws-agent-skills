# Eval: opcua-gateway-asset-model

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — measurement/transform/metric/attribute model, OPC-UA gateway with node-to-alias mappings, alias-based ingestion path

## Prompt

Create a SiteWise asset model named "Pump Station" in us-east-1.
Measurement properties: FlowRate (DOUBLE, m3/s), Pressure (DOUBLE,
kPa), Temperature (DOUBLE, C), Vibration (DOUBLE, mm/s). Transform
property: TemperatureF = Temperature * 9/5 + 32. Metric property:
HourlyAvgFlow = AVG(FlowRate, 3600s). Attribute property: Manufacturer
(STRING), SerialNumber (STRING). Gateway "Plant Gateway" on Greengrass
core device GreengrassCore-001. OPC-UA source from
opc.tcp://10.0.1.50:4840 with 4 node mappings to aliases
/plant/area1/pump1/*. Account 123456789012. Tags: Environment=production,
Site=PlantA.
