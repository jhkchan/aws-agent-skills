# Baseline (no-skill) — dev-single-shard

> This is the response a model produces **without** the skill
> definition. It creates a single-shard dev cluster but misses the
> explicit "NO failover" notation, the named-ACL requirement (uses
> default open-access), and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to create a dev MemoryDB cluster:

```bash
aws memorydb create-cluster \
  --cluster-name dev-memorydb \
  --node-type db.r6g.large \
  --acl-name open-access
```

That should work for functional testing.
