# Baseline (no-skill) — dev-single-instance-migration

> This is the response a model produces **without** the skill
> definition. It suggests using smaller instances but misses the
> topology change (single-instance saves ~85% by eliminating ELB +
> NAT Gateway), the deployment policy optimization (Immutable doubles
> cost during deploy on dev), and the cost breakdown that quantifies
> the savings. Generated for with-skill-vs-baseline comparison.

---

You can try using smaller instances like t3.small or t3.micro
for your dev environment. The CPU usage is low at 12%.

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-dev-app \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small
```

Also check if you can reduce the number of instances in the auto-
scaling group.
