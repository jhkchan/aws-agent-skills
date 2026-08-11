# Baseline (no-skill) response: dc2-migrate-to-ra3

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-optimizer skill loaded.

---

Your DC2 cluster is using about 44% of its local storage. You might want
to consider migrating to RA3 nodes since they offer managed storage that
scales independently of compute.

To migrate, you can take a snapshot and restore to a new RA3 cluster:

```bash
aws redshift create-snapshot \
  --cluster-identifier reporting-dc2-cluster \
  --snapshot-identifier migration-snapshot

aws redshift restore-from-cluster-snapshot \
  --cluster-identifier new-ra3-cluster \
  --snapshot-identifier migration-snapshot \
  --node-type ra3.4xlarge \
  --number-of-nodes 3
```

RA3 separates compute from storage so you only pay for the storage you
actually use. This could be cheaper than DC2 where you pay for the full
local disk regardless of usage.
