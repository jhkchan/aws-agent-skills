# Baseline (no-skill) — cloud-ingestion-alias

> This is the response a model produces **without** the skill
> definition. It creates the asset model but misses the alias-based
> ingestion advantage (avoiding DescribeAsset lookups at scale), the
> storage warm tier configuration, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the model and asset:

```bash
aws iotsitewise create-asset-model --asset-model-name "Temperature Sensor"
```

Then ingest data with BatchPutAssetPropertyValue.
