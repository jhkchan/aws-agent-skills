# Baseline (no-skill) — missing-subnet-group-and-acl

> This is the response a model produces **without** the skill
> definition. It blindly issues a create-cluster command without
> flagging the missing subnet group (Multi-AZ requires a multi-AZ
> subnet group), the missing security group (port 6379 inbound), or
> the missing named ACL (MemoryDB requires an ACL; default
> open-access is NOT for production) — exactly the prerequisites the
> skill is designed to catch. Generated for with-skill-vs-baseline
> comparison.

---

Here's how to create your MemoryDB cluster:

```bash
aws memorydb create-cluster \
  --cluster-name session-db \
  --node-type db.r6g.large \
  --acl-name open-access
```

That should give you a Multi-AZ MemoryDB for sessions. Let me know
if you need anything else.
