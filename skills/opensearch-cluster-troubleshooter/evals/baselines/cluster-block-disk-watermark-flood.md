# Baseline (no-skill) response: cluster-block-disk-watermark-flood

---

Your OpenSearch cluster is returning ClusterBlockException. The error
mentions "read-only" so the cluster has hit a disk watermark and
blocked writes. Free up some disk space — delete old indices or
expand the EBS volumes.

Once disk usage is below the threshold, the cluster should allow
writes again. If it doesn't, you may need to manually clear the
read-only flag on the indices.
