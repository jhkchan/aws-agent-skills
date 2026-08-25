# Advanced patterns — rds-failover-troubleshooter (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Quick start — symptom → root-cause map and core rules

- **Symptom → root-cause map (first plausible match drives the first probe):**
  Failover did not trigger → MULTI_AZ_HEALTH_THRESHOLD (health check
  threshold too conservative); failover triggered but application still
  hits old instance → APP_NOT_CLUSTER_ENDPOINT (using instance endpoint
  instead of cluster endpoint) or DNS_PROPAGATION_DELAY (DNS TTL not
  1s for Aurora) or CONNECTION_POOL_CACHING (connection pool cached the
  old IP); failover took too long → RECOVERY_MODE_FULL (recovery mode
  set to full instead of optimized); new writer not promoted as expected
  → FAILOVER_PRIORITY_TIER (tier 0 not on the intended instance);
  read replica promotion failed → READ_REPLICA_PROMOTION_FAILURE
  (network or storage issue); storage-full error → STORAGE_FULL;
  standby cannot take over → PARAMETER_GROUP_MISMATCH or
  OPTION_GROUP_CONFLICT; Aurora Global DB failover →
  AURORA_GLOBAL_FAILOVER_MODE (managed vs unmanaged).
- **Always verify with a probe, never guess.** Each root cause has a
  single command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED
  verdict requires positive evidence — a failing probe that matches
  the symptom — not a process of elimination.
- **Application MUST use the cluster endpoint for transparent
  failover.** The Aurora cluster endpoint (writer endpoint)
  automatically resolves to the current writer instance after
  failover. DNS TTL is 1 second for Aurora endpoints. Applications
  using the instance endpoint will hit the old (now reader or
  terminated) instance after failover. This is the #1 source of
  "failover didn't work" incidents.
- **Aurora failover tier 0 is promoted first.** When multiple
  instances have tier 0, the largest instance class is chosen. If no
  instance has tier 0, tier 1 instances are considered. An instance
  with tier 15 (default) is promoted last. Operators who expect a
  specific instance to become the writer must set it to tier 0.
- **DNS TTL is 1 second for Aurora endpoints, but application
  connection pool caching can cause delays.** The OS DNS resolver,
  JVM DNS cache, and database driver connection pool can each cache
  the resolved IP longer than 1 second. The application must honour
  the DNS TTL or proactively refresh connections after a failover
  event.

## Mindset

An RDS or Aurora failover failure is almost never about the database
engine or the failover mechanism itself. AWS's Multi-AZ and Aurora
failover automation works correctly in the vast majority of cases.
The root cause is usually in the application layer (wrong endpoint,
stale connection pool), the configuration layer (health threshold,
failover tier, parameter group), or the resource layer (storage-full,
network). Senior database engineers start with the cluster endpoint
and the application connection string; they do not start by inspecting
the database engine logs.

## Philosophy — four senior-engineer behaviours

Four behaviours separate a senior RDS/Aurora engineer from a generalist:

- **The cluster endpoint is the linchpin of transparent failover.**
  Aurora provides a writer endpoint
  (`<cluster>.cluster-<id>.<region>.rds.amazonaws.com`) that
  automatically resolves to the current writer. Applications using
  this endpoint experience a brief interruption (typically 10-30
  seconds for Aurora, 60-120 seconds for Multi-AZ) during failover,
  then reconnect transparently. Applications using the instance
  endpoint (`<cluster>-instance-1.<id>.<region>.rds.amazonaws.com`)
  will fail after failover because that endpoint either resolves to
  the old writer (now a reader or terminated) or stops resolving.

- **Failover duration is determined by the detection time plus the
  promotion time.** Detection time depends on the health check
  interval and threshold (Multi-AZ: typically 30-60 seconds). Promotion
  time depends on the recovery mode (Aurora: 10-30 seconds with
  parallel recovery; Multi-AZ: 60-120 seconds with full recovery).
  Operators who report "failover took 5 minutes" are usually measuring
  the application recovery time, not the database failover time — the
  application's connection pool cached the old IP for several minutes.

- **Failover priority tiers determine which instance becomes the new
  writer.** Aurora assigns a tier (0-15) to each instance. Tier 0
  instances are promoted first. Within the same tier, the largest
  instance class is chosen. If the intended promotion target is tier
  15 (default), it will be promoted only after all tier 0-14 instances
  are considered — which may never happen if a tier 0 instance exists.
  Operators who "just added a replica and it became the writer instead
  of my intended instance" forgot to check the tier.

- **Storage-full blocks failover.** If the primary or standby instance
  has exhausted its allocated storage, the failover cannot complete
  because the new writer cannot write the recovery log. The error is
  not "failover failed" but `InsufficientStorage` or a generic
  `FailoverFailed`. Always check `StorageFull` CloudWatch alarms
  before concluding the failover mechanism is broken.

## Step 0 — Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior RDS/Aurora engineer knows
from incident experience:

- **The Aurora cluster endpoint DNS TTL is 1 second, but the
  application may not honour it.** The OS DNS resolver, JVM DNS cache
  (`networkaddress.cache.ttl`, default 60 seconds in many JVMs), and
  database driver connection pool can each cache the resolved IP
  longer than 1 second. The failover completes at the DB layer in
  10-30 seconds, but the application does not recover for 60-120
  seconds because the connection pool holds stale connections. This is
  the #1 cause of "failover took 5 minutes."

- **Multi-AZ failover takes 60-120 seconds; Aurora failover takes
  10-30 seconds.** Multi-AZ creates a standby in a different AZ with
  synchronous block-level replication. On failover, the standby is
  promoted and the DNS record is updated. Aurora uses a distributed
  storage volume shared across AZs; failover promotes a reader
  instance without storage copy. The difference in failover time is
  architectural, not a configuration issue.

- **Failover priority tier 0 does not guarantee promotion order when
  multiple instances have tier 0.** When two or more instances have
  tier 0, Aurora chooses the largest instance class. If they are the
  same size, the instance with the longest uptime is chosen. Operators
  who set two instances to tier 0 and expect a specific one to be
  promoted must ensure it is also the largest.

- **An Aurora reader instance promoted to writer during failover
  inherits the cluster parameter group, not its own.** If the reader
  had a different DB parameter group than the primary (common for
  read-optimised tuning), the promoted instance uses the primary's
  parameter group after promotion. This can cause unexpected behaviour
  if the parameter groups differ significantly.

- **RDS Proxy does not eliminate failover downtime, but it reduces
  connection errors.** During failover, the Proxy queues requests and
  reconnects to the new writer transparently. However, active
  transactions on the old writer are rolled back. The Proxy's
  connection pool drains over 5-30 seconds; during this window, the
  application sees elevated latency but not connection errors.

- **Recovery mode affects failover duration.** Aurora PostgreSQL with
  parallel recovery (Aurora PostgreSQL 13+) uses parallel WAL replay,
  reducing failover time from 30 seconds to 10-15 seconds. Aurora
  MySQL uses a different recovery mechanism. Multi-AZ instances with
  `recovery_mode` parameter set to `full` (instead of `optimized`)
  take longer to recover the transaction log.

- **A storage-full instance cannot complete failover.** The new writer
  needs to write the recovery log. If the allocated storage is
  exhausted, the write fails. The error is `InsufficientStorage` or
  a generic `FailoverFailed` — not "storage full." Always check
  `FreeStorageSpace` CloudWatch metric before concluding the failover
  mechanism is broken.

- **Parameter group mismatches between primary and standby can prevent
  the standby from taking over.** If the primary's parameter group has
  settings that the standby's does not (e.g., different `max_connections`,
  `shared_buffers`, or engine-specific parameters), the standby may
  fail health checks during promotion. The error appears in RDS events
  as a promotion failure.

- **Option group conflicts prevent Multi-AZ failover.** If the primary
  has an option group with options that require specific binaries
  (e.g., Oracle Transparent Data Encryption, SQL Server .NET
  framework), the standby must have a compatible option group. A
  mismatch prevents the standby from starting the engine after
  promotion.

- **Aurora Global DB managed failover is a control-plane operation
  that takes 1-5 minutes.** The managed failover (`failover-global-
  cluster`) promotes a secondary cluster in another region. It is
  slower than a single-region failover because it involves cross-
  region DNS propagation and the secondary cluster must catch up on
  the replication lag. Unmanaged failover (detach + promote manually)
  is faster but requires application-level coordination.

- **Application health checks may not detect a failover.** If the
  application pings the database on a schedule (e.g., every 60
  seconds), it may not notice the failover for up to 60 seconds. A
  failover event should trigger an immediate connection refresh, not
  wait for the next health check.

- **The Aurora custom endpoint can route to the wrong instance after
  failover.** A custom endpoint with static membership (listing
  specific instance identifiers) does not update after failover.
  Only the writer endpoint and reader endpoint are dynamic. Operators
  who use custom endpoints for read/write separation must ensure the
  custom endpoint uses the `ANY` or `READER` type, not `INSTANCE`.

## Aurora Global DB failover modes and RDS event codes (moved from SKILL.md deep reference)

### Aurora Global DB failover modes

| Mode | Command | Duration | Application impact |
|---|---|---|---|
| Managed | `failover-global-cluster` | 1-5 minutes | DNS update across regions; application must reconnect |
| Unmanaged | `remove-from-global-cluster` + `promote-read-replica-db-cluster` | 30-60 seconds | Manual DNS update required; application must point to new region |

### RDS event codes for failover

| Event code | Meaning |
|---|---|
| RDS-EVENT-0049 | Multi-AZ failover started |
| RDS-EVENT-0050 | Multi-AZ failover completed |
| RDS-EVENT-0088 | Aurora failover started |
| RDS-EVENT-0089 | Aurora failover completed |
| RDS-EVENT-0065 | DB instance has insufficient storage |
| RDS-EVENT-0006 | DB instance failover failed |

## Recent AWS features (2024-2026)

- **Aurora PostgreSQL 16+ parallel query recovery (2024-2025):**
  Further reduces failover time from 15 seconds to 8-10 seconds for
  large clusters. Enabled automatically; no configuration needed.
- **Aurora Global DB managed planned failover (2024):** New
  `planned-failover` mode for scheduled regional migrations with zero
  data loss. Different from the emergency managed failover.
- **RDS Proxy multi-AZ awareness (2024-2025):** Proxy automatically
  routes to the new writer after Multi-AZ failover, reducing
  connection errors to near zero. Previously, Proxy required manual
  target group updates.
- **AWS Advanced JDBC Driver failover mode (2024-2025):** Open-source
  driver wrapper that monitors Aurora cluster topology and redirects
  connections transparently after failover. Eliminates the JVM DNS
  cache and connection pool caching issues.
- **Aurora Serverless v2 failover (2024-2026):** Serverless v2
  clusters support failover priority tiers identical to provisioned
  Aurora. The ACU capacity of the promoted instance may start low and
  scale up during the post-failover window.
- **RDS Automated Multi-AZ failover for storage issues (2025):** RDS
  now triggers Multi-AZ failover on storage subsystem failures (not
  just instance unreachability). Reduces the window for
  storage-related outages.

## AWS documentation

- **Amazon Aurora User Guide — Managing Aurora cluster endpoints** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html
- **Aurora high availability and failover** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
- **Multi-AZ deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
- **Aurora Global Database** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
- **RDS Proxy** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-proxy.html
- **Aurora failover priority** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-mysql-cluster.html#aurora-mysql-cluster-failover
- **RDS events** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_Events.html
- **AWS Advanced JDBC Driver** — https://github.com/aws/aws-advanced-jdbc-wrapper
- **Managing DB parameter groups** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.html
- **Promoting a read replica** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReadRepl.html

