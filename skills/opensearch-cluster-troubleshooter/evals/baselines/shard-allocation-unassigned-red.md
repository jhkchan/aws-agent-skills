# Baseline (no-skill) response: shard-allocation-unassigned-red

---

Your OpenSearch cluster is red. You lost a data node and the
shards that were on it are now unassigned. You need to either get
the third data node back online, or add another data node so the
shards can be reallocated.

You can also check the allocation explain API to see why the
shards aren't being assigned. It might be a disk space issue.
