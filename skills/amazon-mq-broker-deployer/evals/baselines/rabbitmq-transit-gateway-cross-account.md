# Baseline (no-skill) — rabbitmq-transit-gateway-cross-account

> This is the response a model produces **without** the skill definition.
> It misses the transit gateway RAM sharing step, the cross-account
> security group CIDR rule, the definitions JSON for cross-account
> consumer topology, the audit log requirement, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To create a RabbitMQ broker with transit gateway access:

1. Create the broker:
```bash
aws mq create-broker \
  --broker-name shared-rabbit \
  --broker-instance-type mq.m5.large \
  --engine-type RABBITMQ \
  --engine-version "3.13" \
  --deployment-mode active/standby
```

2. Configure transit gateway routing in the VPC.

That should give you cross-account access.
