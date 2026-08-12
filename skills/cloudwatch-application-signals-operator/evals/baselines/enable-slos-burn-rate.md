# Baseline (no-skill) — enable-slos-burn-rate

> This is the response a model produces **without** the skill
> definition. It creates an SLO but uses a single burn rate threshold
> (not MWMBR), omits the warning threshold, does not distinguish fast
> burn (page) from slow burn (ticket), does not note SLI auto-derivation
> from traces, and misses the OPERATION_COMPLETED checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create an SLO for payments-api:

```bash
aws application-signals create-service-level-objective \
  --name payments-api-slo \
  --goal '{"AttainmentGoal": 99.9}'
```

Then create an alarm on the burn rate:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name payments-burn \
  --metric-name BurnRate \
  --threshold 14.4
```

That should cover it.
