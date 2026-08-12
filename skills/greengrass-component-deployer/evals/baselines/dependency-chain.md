# Baseline (no-skill) — dependency-chain

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but treats all dependencies the
> same (no HARD vs SOFT distinction), misses the topological
> resolution order, omits the configuration merge semantics, and
> lacks the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the component with dependencies:

```yaml
ComponentDependencies:
  - ComponentRequire:
      ThingName: com.example.StreamCollector
      Version: "1.1.0"
  - ComponentRequire:
      ThingName: com.example.OptionalLogger
      Version: "1.0.0"
```

Deploy:

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/PipelineDevices" \
  --components '{"com.example.DataPipeline": {"componentVersion": "2.0.0"}}'
```
