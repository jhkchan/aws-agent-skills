# Eval prompt: cluster-block-disk-watermark-flood

Diagnose the OpenSearch cluster incident for the following domain. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE, REMEDIATION).

Symptom: writes to `prod-logs-cluster` return
`ClusterBlockException: blocked by: [FORBIDDEN/12/index read-only /
delete admin api]`. The cluster status is yellow and writes have been
failing for 12 minutes. Reads still work.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
HotDataNodes: 3 (r6g.large.search, EBS 100 GB each)
MasterNodes: 3
ClusterStatus: yellow

_cat/allocation?v output (disk.percent per node):
  data-1  disk.percent=91  disk.used=91.2gb  disk.avail=8.8gb
  data-2  disk.percent=88  disk.used=89.8gb  disk.avail=10.2gb
  data-3  disk.percent=97  disk.used=97.0gb  disk.avail=3.0gb

CloudWatch metrics (last 30 min):
  - ClusterIndexWritesBlocked: 1 (sustained 12 min)
  - FreeStorageSpace Minimum: 3.0 GB on data-3
  - JVMHeapPressure Average: 41% (heap is NOT the issue)
  - ClusterStatus.yellow: 1

_cat/indices/logs-*?v&s=index (summary):
  427 monthly indices from 2023-02 to 2024-12
  Oldest 14 months have not been queried in 30 days
  No ISM policy attached to any logs-* index
```

The well-known write block hits at flood stage (95% disk). The
freeing-disk path is well understood; the question is which watermark
is breached and what upstream cause allowed disk to fill.
