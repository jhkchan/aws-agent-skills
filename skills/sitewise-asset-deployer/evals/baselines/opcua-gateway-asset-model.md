# Baseline (no-skill) — opcua-gateway-asset-model

> This is the response a model produces **without** the skill
> definition. It creates the asset model and gateway but misses the
> distinction between measurement/transform/metric/attribute property
> types (treating all as generic properties), the OPC-UA node-to-alias
> mapping requirement (without mappings the gateway ingests nothing),
> the alias uniqueness constraint, the storage configuration, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the asset model:

```bash
aws iotsitewise create-asset-model --asset-model-name "Pump Station"
```

Then create the gateway and add the OPC-UA source.
