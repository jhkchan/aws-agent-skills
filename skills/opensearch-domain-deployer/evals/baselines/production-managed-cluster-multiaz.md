# Baseline (no-skill) — production-managed-cluster-multiaz

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the encryption-at-rest-
> must-enable-at-creation rule, the Multi-AZ node-count-multiple-of-3
> rule, the dedicated-master requirement for latency-sensitive
> production, the VPC-only-vs-public decision, the FGAC IAM master
> user setup, the 30-50 GB per shard rule, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Here's how to create an OpenSearch domain:

1. Create the domain:
```bash
aws opensearch create-domain \
  --domain-name prod-search \
  --engine-version OpenSearch_2.11 \
  --cluster-config InstanceType=r6g.2xlarge.search,InstanceCount=4
```

2. Add EBS storage:
```bash
aws opensearch update-domain-config \
  --domain-name prod-search \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=100
```

3. Add encryption at rest (after creation):
```bash
aws opensearch update-domain-config \
  --domain-name prod-search \
  --encryption-at-rest-options Enabled=true
```

That should cover it.
