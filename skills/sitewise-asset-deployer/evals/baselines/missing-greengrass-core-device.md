# Baseline (no-skill) — missing-greengrass-core-device

> This is the response a model produces **without** the skill
> definition. It attempts to create the gateway without verifying that
> the Greengrass core device is registered, which causes a failure at
> runtime. Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the gateway:

```bash
aws iotsitewise create-gateway \
  --gateway-name "Factory Gateway" \
  --gateway-platform greengrassV2CoreDevice=MyCoreDevice
```

Then configure the OPC-UA source.
