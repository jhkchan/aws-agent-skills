# Baseline (no-skill) — activemq-active-standby-ldap

> This is the response a model produces **without** the skill
> definition. It lists a CLI command but misses the LDAP auth
> requirement for network connectivity, the CloudWatch alarms
> configuration (separate from the MQ API), the maintenance window
> flag, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the broker:

```bash
aws mq create-broker \
  --broker-name prod-mq \
  --engine-type ActiveMQ \
  --host-instance-type mq.m5.large \
  --deployment-mode ACTIVE_STANDBY
```

Then configure security groups and you should be good.
