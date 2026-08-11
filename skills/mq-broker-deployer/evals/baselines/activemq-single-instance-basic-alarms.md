# Baseline (no-skill) — activemq-single-instance-basic-alarms

> This is the response a model produces **without** the skill
> definition. It creates the broker with basic CLI flags but misses
> the CloudWatch alarms configuration (which is a separate
> CloudWatch API call, not an MQ API parameter), the correct port
> mapping for OpenWire, and the READY_TO_DEPLOY checklist. Generated
> for with-skill-vs-baseline comparison.

---

Create the broker:

```bash
aws mq create-broker \
  --broker-name dev-mq \
  --engine-type ActiveMQ \
  --host-instance-type mq.t3.small \
  --deployment-mode SINGLE_INSTANCE \
  --users '[{"Username":"admin","Password":"secret123"}]'
```

That should cover it.
