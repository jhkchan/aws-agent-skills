# Baseline (no-skill) — prod-immutable-deploy-cost

> This is the response a model produces **without** the skill
> definition. It notes the low CPU and suggests right-sizing but
> misses the managed platform update scheduling recommendation
> (updates are disabled — should be enabled with an off-peak window),
> does not quantify the savings, and does not structure the output
> as a proper optimization assessment. Generated for with-skill-vs-
> baseline comparison.

---

The production environment looks fine. CPU is at 28% so you could
try smaller instances like m5.large instead of m5.xlarge. The
Immutable deployment policy is appropriate for production.

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=m5.large
```

Make sure to test in staging first.
