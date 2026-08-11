# Baseline (no-skill) — missing-kms-key

> This is the response a model produces **without** the skill
> definition. It attempts to create the broker with a KMS key alias
> that does not exist, which will cause a creation failure. Does
> not verify the key exists first or emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Create the broker with encryption:

```bash
aws mq create-broker \
  --broker-name prod-rmq2 \
  --engine-type RabbitMQ \
  --host-instance-type mq.m5.xlarge \
  --deployment-mode CLUSTER_MULTI_AZ \
  --encryption-options '{"UseAwsOwnedKey": false, "KmsKeyId": "alias/does-not-exist-yet"}'
```

The key should work once it's created.
