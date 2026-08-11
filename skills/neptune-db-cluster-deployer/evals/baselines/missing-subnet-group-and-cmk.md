# Baseline (no-skill) — missing-subnet-group-and-cmk

> This is the response a model produces **without** the skill
> definition. It blindly issues a create-db-cluster command without
> flagging the missing subnet group (Multi-AZ requires a multi-AZ
> subnet group), the missing security group (port 8182 inbound), or
> the missing customer CMK ARN — exactly the prerequisites the skill
> is designed to catch. Generated for with-skill-vs-baseline
> comparison.

---

Here's how to create your Neptune cluster:

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier user-graph \
  --engine neptune \
  --storage-encrypted \
  --kms-key-id alias/user-graph-kms
```

That should give you a Multi-AZ Neptune with a customer CMK. Let me
know if you need anything else.
