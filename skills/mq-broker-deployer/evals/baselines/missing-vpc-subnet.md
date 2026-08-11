# Baseline (no-skill) — missing-vpc-subnet

> This is the response a model produces **without** the skill
> definition. It attempts to create the broker without verifying
> that subnets are required for active/standby mode (2 subnets in
> 2 AZs). Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here's the broker creation:

```bash
aws mq create-broker \
  --broker-name prod-mq2 \
  --engine-type ActiveMQ \
  --host-instance-type mq.m5.large \
  --deployment-mode ACTIVE_STANDBY
```

You can add subnets later.
