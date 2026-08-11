# Baseline (no-skill) — rabbitmq-cluster-with-iam

> This is the response a model produces **without** the skill definition.
> It misses the IAM-auth-is-creation-time-only constraint, the 3-node
> quorum requirement for cluster mode, the definitions JSON configuration
> requirement, the audit-vs-general log distinction, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

To create a RabbitMQ cluster:

1. Create the broker:
```bash
aws mq create-broker \
  --broker-name prod-rabbit \
  --broker-instance-type mq.m5.2xlarge \
  --engine-type RABBITMQ \
  --engine-version "3.13" \
  --deployment-mode CLUSTER_MULTI_AZ
```

2. You can add IAM auth later:
```bash
aws mq update-broker \
  --broker-id prod-rabbit \
  --authentication-strategy ldap
```

3. Enable logs:
```bash
aws mq update-broker \
  --broker-id prod-rabbit \
  --logs General=true
```

That should work.
