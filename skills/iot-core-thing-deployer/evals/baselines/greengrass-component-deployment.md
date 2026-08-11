# Baseline (no-skill) — greengrass-component-deployment

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the core device
> registration requirement, the deployment target validation, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Deploy the component:

```bash
aws greengrassv2 create-deployment \
  --target-arn arn:aws:iot:...:thinggroup/factory-edge-devices \
  --components '{"com.example.TelemetryAgent":{"componentVersion":"1.0.0"}}'
```
