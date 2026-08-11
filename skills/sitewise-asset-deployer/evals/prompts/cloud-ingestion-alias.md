# Eval: cloud-ingestion-alias

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — measurement model with alias, storage config, cloud-direct ingestion (no gateway)

## Prompt

Create a SiteWise asset model "Temperature Sensor" in us-east-1 with
measurement property Reading (DOUBLE, Celsius). Set alias
/buildings/hq/sensor1/reading on the property. Cloud-direct ingestion
via BatchPutAssetPropertyValue (no gateway). Storage warm tier 180
days. Account 123456789012. Tags: Environment=production, Building=HQ.
