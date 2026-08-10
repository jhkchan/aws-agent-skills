# Baseline (no-skill) — dev-t3-single-node

> This is the response a model produces **without** the skill
> definition. It creates a t3 domain but misses the "t3 is dev-only"
> rule, the public-vs-VPC access decision, the FGAC IAM master user
> setup, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create a small OpenSearch domain for testing:

```bash
aws opensearch create-domain \
  --domain-name dev-search \
  --engine-version OpenSearch_2.11 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1
```

That should be enough for testing search features.
