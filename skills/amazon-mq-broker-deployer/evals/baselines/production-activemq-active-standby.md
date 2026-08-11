# Baseline (no-skill) — production-activemq-active-standby

> This is the response a model produces **without** the skill definition.
> It lists CLI commands but misses the active/standby multi-AZ subnet
> requirement, the LDAP directory dependency, the audit-vs-general log
> distinction, the OpenWire failover URI requirement, the configuration-
> must-precede-broker ordering, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to create an ActiveMQ broker:

1. Create the broker:
```bash
aws mq create-broker \
  --broker-name prod-mq \
  --broker-instance-type mq.m5.large \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --deployment-mode active/standby
```

2. Add encryption:
```bash
aws mq update-broker \
  --broker-id prod-mq \
  --encryption-options useAwsOwnedKey=false,kmsKeyId=alias/prod-mq-kms
```

3. Enable logs:
```bash
aws mq update-broker \
  --broker-id prod-mq \
  --logs General=true
```

That should cover it.
