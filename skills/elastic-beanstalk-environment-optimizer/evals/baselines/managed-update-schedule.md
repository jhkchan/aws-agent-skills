# Baseline (no-skill) — managed-update-schedule

> This is the response a model produces **without** the skill
> definition. It mentions enabling managed updates but misses the
> off-peak scheduling recommendation (Sunday 04:00 UTC, outside
> the 09:00-18:00 peak window), does not specify the update level
> (minor vs major), and does not structure the output as a proper
> optimization assessment. Generated for with-skill-vs-baseline
> comparison.

---

The environment seems well-provisioned. You should enable managed
platform updates so the environment stays up to date.

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-api-prod \
  --option-settings Namespace=aws:elasticbeanstalk:managedactions,OptionName=ManagedActionsEnabled,Value=true
```

The CPU at 45% looks fine for c5.large instances.
