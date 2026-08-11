# Baseline (no-skill) — rabbitmq-cluster-iam-auth

> This is the response a model produces **without** the skill
> definition. It creates the broker but misses that RabbitMQ IAM auth
> uses `authenticationStrategy = LDAP` (counterintuitive naming),
> does not verify the 3-subnet requirement for cluster mode, and
> omits the READY_TO_DEPLOY checklist. Generated for with-skill-vs-
> baseline comparison.

---

Create the RabbitMQ broker:

```bash
aws mq create-broker \
  --broker-name prod-rmq \
  --engine-type RabbitMQ \
  --host-instance-type mq.m5.large \
  --deployment-mode CLUSTER_MULTI_AZ
```

Then set up IAM and security groups.
