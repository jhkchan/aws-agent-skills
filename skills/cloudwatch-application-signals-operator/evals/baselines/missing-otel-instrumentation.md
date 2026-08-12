# Baseline (no-skill) — missing-otel-instrumentation

> This is the response a model produces **without** the skill
> definition. It creates the SLO and burn rate alerts without flagging
> the missing OTel instrumentation as a prerequisite gap. Application
> Signals would show no services and no SLI data. Generated for
> with-skill-vs-baseline comparison.

---

Create an SLO for legacy-api:

```bash
aws application-signals create-service-level-objective \
  --name legacy-api-slo \
  --goal '{"AttainmentGoal": 99.5}'
```

Configure burn rate alerts:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name legacy-api-burn \
  --metric-name BurnRate \
  --threshold 14.4
```

The SLO is now configured.
