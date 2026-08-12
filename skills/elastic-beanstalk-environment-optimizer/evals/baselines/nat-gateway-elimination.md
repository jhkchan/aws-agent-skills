# Baseline (no-skill) — nat-gateway-elimination

> This is the response a model produces **without** the skill
> definition. It suggests reducing the instance size but misses the
> NAT Gateway elimination opportunity entirely. The instance has a
> public IP and is in a public subnet, so the $32/month NAT Gateway
> is unnecessary. Generated for with-skill-vs-baseline comparison.

---

You can right-size the instance from t3.medium to t3.small since
CPU is only at 18%.

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-staging-app \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small
```

That should save some money each month.
