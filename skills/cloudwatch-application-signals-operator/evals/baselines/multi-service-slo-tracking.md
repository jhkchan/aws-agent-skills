# Baseline (no-skill) — multi-service-slo-tracking

> This is the response a model produces **without** the skill
> definition. It creates SLOs but does not set up a fleet dashboard,
> uses a single burn rate per service (not MWMBR), omits canary alarms,
> and misses the OPERATION_COMPLETED checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create SLOs for each service:

```bash
for svc in orders-api inventory-api payments-api shipping-api notification-api; do
  aws application-signals create-service-level-objective \
    --name "${svc}-slo" \
    --goal '{"AttainmentGoal": 99.9}'
done
```

Each service now has a 99.9% SLO.
