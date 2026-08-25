# Aurora Failover Operator — Advanced Patterns

Expert-knowledge deep dives, edge cases, and recent-feature notes moved
from SKILL.md. Load on demand before complex failover decisions.


## Step 0: Expert heuristic — non-obvious Aurora failover behaviours (moved from SKILL.md)

These behaviours are easy to misjudge without operational Aurora
experience. Each changes a plan if ignored:

- **The writer endpoint DNS update takes 30-60 seconds at the RDS layer,
  but application DNS caches can hold the old IP for minutes.** The JVM
  default DNS cache TTL is 60 seconds (or infinite if configured via
  `networkaddress.cache.ttl=-1`). Node.js, Python, and Go have their own
  resolver caches. After failover, applications with long DNS cache TTLs
  continue connecting to the old writer (now a reader) and get read-only
  errors. Always surface the DNS cache flush step in the failover plan.

- **RDS Proxy eliminates connection drops during failover, but only if the
  application connects THROUGH the proxy endpoint, not the cluster
  endpoint.** The proxy endpoint is separate from the cluster writer
  endpoint. Applications that connect to the cluster endpoint directly do
  NOT benefit from proxy pooling. Verify the application connection string
  uses the proxy endpoint before claiming "connections survive failover."

- **Aurora failover promotes a reader to writer; the old writer becomes a
  reader.** This is a role swap, not a "new instance." The instance that
  was the writer is now a reader. After failback, the original writer is
  promoted back. Each failover/failback cycle causes a brief write outage
  (30-120 seconds). Minimize unnecessary failback cycles.

- **`failover-db-cluster --target-db-instance-identifier` lets you choose
  which replica to promote.** Without this flag, Aurora picks the replica
  with the lowest `AuroraReplicaLag` automatically. For planned failovers
  (e.g., AZ maintenance), specify the target to control the promotion.

- **Aurora Replica lag (`AuroraReplicaLag`) determines potential data
  loss during unplanned failover.** Aurora replicates synchronously within
  a region (shared storage volume), so replica lag is typically < 100ms.
  However, under heavy write load, lag can spike. If the primary fails
  during a lag spike, the promoted replica may be missing recent writes.
  Always check `AuroraReplicaLag` before a planned failover.

- **Aurora Global Database uses asynchronous cross-region replication
  (typically < 1 second lag, but no SLA).** During an unplanned global
  failover (primary region is down), the secondary region may be behind.
  The RPO depends on the replication lag at the time of the outage. For
  planned global failover, AWS ensures the secondary is fully caught up
  before promoting.

- **`failover-global-cluster` is the managed path for Aurora Global
  Database failover.** It promotes a secondary region cluster to primary
  and demotes the original. This is the safest path. The unplanned
  alternative (`detach-from-global-cluster` + manual promote) is faster
  but does not coordinate with the original primary — if the original
  comes back, you have split-brain.

- **Split-brain risk exists only with Aurora Global Database unplanned
  failover.** In a single-region Aurora cluster, failover is atomic (shared
  storage volume ensures only one writer). In a Global Database, if you
  detach a secondary and promote it while the primary region is still
  alive (false-positive outage detection), both regions have active
  writers writing to divergent storage volumes. This is unrecoverable
  without manual data reconciliation.

- **The reader endpoint does NOT change during failover.** The reader
  endpoint (`<cluster>.cluster-ro-<random>.<region>.rds.amazonaws.com`)
  load-balances across all readers. During failover, the old writer joins
  the reader pool; the promoted reader leaves it. The endpoint itself
  does not change. Applications using the reader endpoint are unaffected.

- **Aurora Serverless v2 failover behaves like provisioned Aurora.** The
  cluster automatically promotes a reader and adjusts capacity. No special
  handling is needed — the same pre-checks and CLI commands apply.

- **Cross-AZ failover does NOT incur cross-AZ data transfer charges.**
  Aurora's shared storage volume spans AZs transparently. Failover within
  a region has no data-transfer cost implications.

- **`failover-db-cluster` returns immediately; the actual promotion takes
  30-120 seconds.** The CLI returns the cluster description with
  `DBClusterStatus: available` (or `failing-over` briefly). Use
  `aws rds wait db-cluster-available` to wait for the failover to complete.


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Aurora Global Database managed planned failover improvements
  (2024-2025):** `failover-global-cluster` now coordinates more
  efficiently, reducing the managed failover window from 5-10 minutes to
  1-5 minutes. The secondary region is confirmed fully caught up before
  promotion.

- **RDS Proxy multi-AZ failover enhancement (2024):** RDS Proxy now
  detects Aurora failover events faster and reconnects to the new writer
  within 5-10 seconds (previously 10-30 seconds). Connection drops during
  failover are further reduced.

- **Aurora Serverless v2 failover parity (2024-2025):** Serverless v2
  clusters now support the same failover behavior as provisioned Aurora,
  including `failover-db-cluster` with target specification and automatic
  capacity adjustment on the promoted writer.

- **Aurora Global Database unplanned failover Runbook (2024-2025):** AWS
  published a formalized runbook for unplanned global failover via
  `detach-from-global-cluster` + promote. The runbook includes split-brain
  detection and reconciliation guidance.

- **Aurora I/O-Optimized failover (2024):** Clusters on the Aurora
  I/O-Optimized storage configuration failover identically to standard
  Aurora — no special handling needed.

- **Application Auto Scaling with Aurora failover (2024-2025):** Aurora
  Auto Scaling now adjusts reader count post-failover automatically if
  the promoted replica's capacity is insufficient. Monitor
  `CPUUtilization` and `DatabaseConnections` post-failover to verify
  adequate capacity.

- **Aurora PostgreSQL 16/17 failover improvements (2025):** Faster
  connection re-establishment for Aurora PostgreSQL during failover.
  Connection handling now more closely matches Aurora MySQL behavior.
