---
name: rds-failover-troubleshooter
description: >-
  Diagnoses RDS and Aurora failover issues through a thirteen-category
  diagnostic tree: Multi-AZ failover not triggering (health check
  threshold too conservative), failover taking too long (DNS
  propagation, recovery mode full), Aurora writer endpoint not
  redirecting (application using instance endpoint instead of cluster
  endpoint), read replica promotion failures (network connectivity,
  storage), storage-full preventing failover (allocated storage
  exhausted), parameter group mismatch between primary and standby,
  option group conflicts preventing standby from taking over, Aurora
  cluster endpoint type confusion (writer vs reader vs custom vs
  instance), failover priority tier misconfiguration (tier 0 vs tier
  1 not set on the intended promotion target), Aurora Global DB
  failover (managed vs unmanaged), RDS Proxy failover behavior
  (connection pool not draining), application connection string not
  using cluster endpoint, and CloudWatch failover event gaps. Walks
  symptoms to a verified root cause with evidence-backed probes;
  emits ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and cluster configuration. Live-account
  diagnosis uses aws rds describe-db-clusters, aws rds describe-db-instances, aws rds describe-db-cluster-endpoints, aws rds describe-db-cluster-parameter-groups, aws rds describe-events, aws cloudwatch get-metric-statistics,
  aws ec2 describe-route-tables, aws ec2 describe-security-groups, and aws logs filter-log-events (AWS CLI v2, SSO or key-based credentials).
keywords:
- RDS
- Aurora
- failover
- Multi-AZ
- writer endpoint
- cluster endpoint
- read replica promotion
- storage-full
- parameter group mismatch
- option group conflict
- failover priority
- tier 0
- Aurora Global DB
- RDS Proxy
- connection pool
- DNS propagation
- CloudWatch failover events
- troubleshooting
tags:
- rds
- aurora
- databases
- troubleshooting
- failover
- multi-az
- high-availability
- cluster-endpoint
- rds-proxy
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an RDS or Aurora failover issue (Multi-AZ failover not triggering, failover taking too long, writer endpoint not redirecting, read replica promotion failure, storage-full preventing failover, parameter group mismatch, option group conflict, failover priority misconfiguration, Aurora Global DB failover, RDS Proxy failover, application connection issues), walking a symptom to the failed layer with verify commands, or triaging a "failover did not work" incident where the root cause may be endpoint configuration, health threshold, storage, parameter group, option group, failover tier, or application connection string — not necessarily the database engine itself.
  when_not_to_use: RDS connectivity debugging (use rds-connectivity-troubleshooter), RDS performance tuning (use rds-cost-optimizer for right-sizing), Aurora backup and restore (use rds-backup-restore-operator), or RDS instance creation (use rds-instance-deployer). This skill diagnoses failover-time issues; it does not tune query performance or audit steady-state security posture.
  activation_triggers:
  - RDS failover not working
  - Aurora failover not triggering
  - Multi-AZ failover failed
  - Aurora writer endpoint not redirecting
  - RDS failover taking too long
  - Aurora failover priority
  - read replica promotion failed
  - storage-full failover
  - parameter group mismatch failover
  - option group conflict failover
  - Aurora Global DB failover
  - RDS Proxy failover
  - application not connecting after failover
  - Aurora cluster endpoint confusion
  - troubleshoot RDS failover
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "failover took 5 minutes", "writer endpoint still points to old instance"), optionally paired with the cluster configuration and recent RDS events, OR (b) a DB cluster identifier plus caller context (application connection string, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/ROOT_CAUSE/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and ROOT_CAUSE ∈ {APP_NOT_CLUSTER_ENDPOINT, MULTI_AZ_HEALTH_THRESHOLD, FAILOVER_PRIORITY_TIER, STORAGE_FULL, PARAMETER_GROUP_MISMATCH, OPTION_GROUP_CONFLICT, DNS_PROPAGATION_DELAY, CONNECTION_POOL_CACHING, AURORA_GLOBAL_FAILOVER_MODE, RDS_PROXY_POOL_DRAIN, RECOVERY_MODE_FULL, CLOUDWATCH_EVENT_GAP, READ_REPLICA_PROMOTION_FAILURE, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Aurora PostgreSQL cluster prod-db-cluster\nfailed over automatically at 03:17 UTC. The writer\nendpoint resolved to the new writer within 1 second,\nbut the application continued hitting the old writer\nfor 90 seconds, then connection errors cleared.\"\nDBClusterIdentifier: prod-db-cluster\nEngine: aurora-postgresql\nWriterEndpoint: prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com\nApplication connection string: uses the instance endpoint\nprod-db-cluster-instance-1.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com\ninstead of the cluster endpoint"
---

# RDS Failover Troubleshooter

## Quick start

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

## Philosophy

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

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely root cause | First probe |
|---|---|---|
| Failover triggered but app still hits old instance | APP_NOT_CLUSTER_ENDPOINT | Check application connection string for instance vs cluster endpoint |
| App recovers 2-5 minutes after failover despite DNS TTL 1s | CONNECTION_POOL_CACHING | Check DB driver connection pool TTL, JVM DNS cache (`networkaddress.cache.ttl`) |
| Failover did not trigger at all | MULTI_AZ_HEALTH_THRESHOLD | `describe-db-instances` for Multi-AZ config; CloudWatch `DatabaseConnection` and `DiskQueueDepth` metrics |
| New writer is not the expected instance | FAILOVER_PRIORITY_TIER | `describe-db-instances` for `PromotionTier` on each instance |
| `InsufficientStorage` or `FailoverFailed` | STORAGE_FULL | `describe-db-instances` for `StorageAllocated` vs `StorageUsed`; CloudWatch `FreeStorageSpace` |
| Standby cannot take over; error in RDS events | PARAMETER_GROUP_MISMATCH or OPTION_GROUP_CONFLICT | `describe-db-instances` for `DBParameterGroups` and `OptionGroupMemberships` on primary vs standby |
| Aurora writer endpoint not resolving to new writer | DNS_PROPAGATION_DELAY | `nslookup` or `dig` on the cluster endpoint; check DNS resolver cache |
| Read replica promotion fails | READ_REPLICA_PROMOTION_FAILURE | `describe-db-instances` for replica status; check network connectivity and storage |
| Aurora Global DB failover not working | AURORA_GLOBAL_FAILOVER_MODE | `describe-global-clusters`; check if managed or unmanaged failover |
| RDS Proxy not draining connections | RDS_PROXY_POOL_DRAIN | `describe-db-proxies`; CloudWatch `DatabaseConnections` metric on the proxy |
| Recovery mode causes long failover | RECOVERY_MODE_FULL | Check parameter group for `recovery_mode` or Aurora parallel recovery settings |
| No CloudWatch event for failover | CLOUDWATCH_EVENT_GAP | `describe-events` for the cluster; check EventBridge rule for RDS events |

## Pre-flight: gather the failover context

Before running root-cause-specific probes, gather the canonical cluster
configuration and short-circuit on misconfigurations that mimic
failover failures.

### Account-wide pre-flight commands

```bash
# 1. Cluster configuration (Aurora)
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[] | {DBClusterIdentifier, Engine, EngineVersion, Status,
    MultiAZ, DBClusterMembers, Endpoint, ReaderEndpoint,
    DBClusterParameterGroup, AllocatedStorage, StorageEncrypted}'

# 2. Instance details (primary and replicas)
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {DBInstanceIdentifier, DBInstanceClass, DBInstanceStatus,
    MultiAZ, PromotionTier, DBParameterGroups, OptionGroupMemberships,
    AllocatedStorage, StorageType, Engine, Endpoint}'

# 3. Cluster endpoints (Aurora)
aws rds describe-db-cluster-endpoints \
  --db-cluster-identifier <cluster-id> --output json

# 4. Recent RDS events
aws rds describe-events \
  --source-identifier <cluster-id> --source-type db-cluster \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# 5. CloudWatch failover-related metrics
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value=<cluster-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 6. Free storage space
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Minimum --output json
```

### Cluster-state short-circuit

| Finding | Effect on diagnosis |
|---|---|
| Cluster `Status: available`, writer endpoint resolves to a healthy instance | Failover completed at the DB layer. Investigate application-side issues (endpoint, connection pool). |
| Cluster `Status: modifying` or `Status: upgrading` | A maintenance action is in progress. Failover may be delayed or blocked. Wait for completion. |
| Instance `Status: storage-full` | The instance has exhausted allocated storage. Failover cannot complete. **ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: STORAGE_FULL`. |
| Instance `MultiAZ: false` | The instance is not Multi-AZ enabled. No standby exists. Failover cannot occur. |
| Instance `PromotionTier` on intended target > 0 | A lower-tier instance will be promoted first. Check if another instance has tier 0. |
| Parameter group `status: applying` or `pending-reboot` | A parameter change is pending. The standby may have a different effective configuration. |
| Aurora Global cluster with `GlobalClusterIdentifier` set | The cluster is part of a Global DB. Failover semantics differ (managed vs unmanaged). |

If the input is malformed (missing cluster identifier, absent symptom
description, no application context), emit:

```text
TARGET: <cluster-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum the
  DBClusterIdentifier (or DBInstanceIdentifier for Multi-AZ) and a
  description of the observed failover symptom.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the cluster or instance
  identifier, (2) the observed symptom (failover did not trigger,
  took too long, app still errors), and (3) the application
  connection string (to check for instance vs cluster endpoint).
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the root-cause-specific probes in
order.

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Application connection string check

Symptom: failover completed (new writer is active, cluster endpoint
resolves correctly), but the application still cannot connect.

```bash
# Check what endpoint the application is using
# Look for the connection string in the application configuration
grep -r "rds.amazonaws.com" /path/to/app/config/

# Verify the cluster endpoint resolves to the new writer
dig +short <cluster-endpoint>

# Compare with the instance endpoint
dig +short <instance-endpoint>
```

If the application uses the instance endpoint
(`<cluster>-instance-1.<id>.<region>.rds.amazonaws.com`) instead of
the cluster endpoint
(`<cluster>.cluster-<id>.<region>.rds.amazonaws.com`),
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: APP_NOT_CLUSTER_ENDPOINT`.

The instance endpoint does not follow the writer after failover. The
application must use the cluster endpoint (also called the writer
endpoint) for transparent failover.

### Step 2: DNS propagation check

Symptom: application uses the cluster endpoint but still hits the old
instance for 30+ seconds after failover.

```bash
# Check DNS TTL for the Aurora cluster endpoint
dig <cluster-endpoint> | grep "ANSWER SECTION" -A 5

# Aurora cluster endpoints have a 1-second TTL by default
# If the application's DNS resolver ignores the TTL, the old IP persists
```

Check the application's DNS caching layers:

| Layer | Default TTL | Fix |
|---|---|---|
| OS DNS resolver (systemd-resolved, dnsmasq) | 30-60 seconds | Set `cache-max-ttl` to 1 second, or disable caching |
| JVM DNS cache (`networkaddress.cache.ttl`) | 60 seconds (Java 8+); some frameworks override | Set `-Dnetworkaddress.cache.ttl=1` |
| Database driver connection pool (HikariCP, c3p0, pgxpool) | Varies; pools hold connections until closed | Set `maxLifetime` < 30s, or implement `onFailover` callback |
| Application-level DNS cache | Varies | Disable or set TTL to 1 second |

If a caching layer is holding the old IP,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: DNS_PROPAGATION_DELAY`
(OS/JVM DNS cache) or `ROOT_CAUSE: CONNECTION_POOL_CACHING`
(connection pool).

### Step 3: Multi-AZ health check threshold

Symptom: primary instance is unhealthy (high CPU, stuck queries) but
failover does not trigger.

```bash
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {MultiAZ, DBInstanceStatus, AutomatedBackupRetentionPeriod}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

Multi-AZ failover triggers when:
- The primary instance becomes unreachable (network partition).
- The instance status changes to `failed`.
- The storage subsystem becomes unresponsive.

Multi-AZ does NOT trigger on:
- High CPU (even at 100%).
- High connection count.
- Slow queries.

If the primary is degraded but responsive (high CPU, slow queries),
Multi-AZ will not failover. **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: MULTI_AZ_HEALTH_THRESHOLD`. The health check only triggers
on unreachability, not performance degradation.

### Step 4: Failover priority tier

Symptom: Aurora failover completed, but the "wrong" instance became
the new writer.

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[].DBClusterMembers[] | {DBInstanceIdentifier,
    IsClusterWriter, PromotionTier}'

# Check each instance's tier
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, DBInstanceClass, PromotionTier}'
```

Aurora failover promotion order:
1. Lowest `PromotionTier` (tier 0 first).
2. Within the same tier, largest `DBInstanceClass`.
3. Within the same tier and class, longest uptime.

If the intended promotion target has tier 15 (default) but another
instance has tier 0, the tier 0 instance is promoted.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: FAILOVER_PRIORITY_TIER`.

Fix: set the intended target to tier 0:

```bash
aws rds modify-db-instance \
  --db-instance-identifier <target-instance> \
  --promotion-tier 0 --apply-immediately
```

### Step 5: Storage-full check

Symptom: failover event appears in RDS events but the new writer does
not become available. Error: `InsufficientStorage` or
`FailoverFailed`.

```bash
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {DBInstanceStatus, AllocatedStorage, StorageType}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Minimum --output json
```

If `FreeStorageSpace` is near zero (< 5 GB) or `DBInstanceStatus` is
`storage-full`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: STORAGE_FULL`.

Fix: increase allocated storage:

```bash
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --allocated-storage <new-size> --apply-immediately
```

### Step 6: Parameter group mismatch

Symptom: standby instance fails health checks during promotion. RDS
events show a promotion failure with parameter-related errors.

```bash
# Compare parameter groups on primary and standby
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, DBParameterGroups, OptionGroupMemberships}'

# Check for pending parameter changes
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[].DBParameterGroups[] | {DBParameterGroupName,
    ParameterApplyStatus}'
```

If the primary and standby have different DB parameter groups with
incompatible settings, the standby may fail during promotion.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: PARAMETER_GROUP_MISMATCH`.

Fix: align the parameter groups:

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --db-parameter-group-name <primary-param-group> \
  --apply-immediately
```

### Step 7: Option group conflict

Symptom: standby cannot start the engine after promotion. RDS events
show an option-group-related error.

```bash
# Compare option groups
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, OptionGroupMemberships}'

# Check for pending option group changes
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[].OptionGroupMemberships[] | {OptionGroupName,
    Status}'
```

If the option groups are incompatible (e.g., primary has TDE, standby
does not), **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: OPTION_GROUP_CONFLICT`.

Fix: align the option groups:

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --option-group-name <primary-option-group> \
  --apply-immediately
```

### Step 8: Read replica promotion failure

Symptom: a read replica (Aurora or cross-region) cannot be promoted
to a standalone cluster/instance.

```bash
aws rds describe-db-instances \
  --db-instance-identifier <replica-id> --output json | \
  jq '.DBInstances[] | {DBInstanceStatus, ReadReplicaSourceDBInstanceIdentifier,
    DBInstanceClass, AllocatedStorage}'

# Check replication lag
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=<replica-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

Common promotion failures:
- High replication lag (the replica has not caught up).
- Network connectivity to the source (for cross-region).
- Storage-full on the replica.
- Parameter group mismatch.

If any of these apply, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: READ_REPLICA_PROMOTION_FAILURE`.

### Step 9: Aurora Global DB failover mode

Symptom: Aurora Global DB failover did not work or took too long.

```bash
aws rds describe-global-clusters \
  --global-cluster-identifier <global-cluster-id> --output json | \
  jq '.GlobalClusters[] | {GlobalClusterIdentifier, GlobalClusterMembers,
    FailoverConfig}'

# Check the failover mode
aws rds describe-global-clusters --output json | \
  jq '.GlobalClusters[] | .FailoverConfig'
```

Managed failover (`failover-global-cluster`) is a control-plane
operation that takes 1-5 minutes. Unmanaged failover (detach secondary
+ promote) is faster but requires manual coordination.

If the failover mode is misconfigured or the secondary cluster has
high replication lag, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: AURORA_GLOBAL_FAILOVER_MODE`.

### Step 10: RDS Proxy failover

Symptom: RDS Proxy does not transparently handle failover; application
sees connection errors.

```bash
aws rds describe-db-proxies \
  --db-proxy-name <proxy-name> --output json | \
  jq '.DBProxies[] | {DBProxyName, Status, EngineFamily,
    TargetRole, RequireTLS}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBProxyIdentifier,Value=<proxy-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average --output json
```

RDS Proxy should queue and reconnect during failover. If connections
are being dropped instead of queued, check:
- Proxy target group health.
- `ConnectionBorrowTimeout` (client-side).
- Proxy `IdleClientTimeout`.

If the Proxy is not draining/queuing correctly,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: RDS_PROXY_POOL_DRAIN`.

### Step 11: Recovery mode

Symptom: Aurora failover takes 30+ seconds consistently; Multi-AZ
failover takes 120+ seconds.

For Aurora, check if parallel recovery is enabled (engine-version
dependent):

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[] | {EngineVersion, DBClusterParameterGroup}'
```

Aurora PostgreSQL 13+ supports parallel WAL replay. Aurora MySQL 8.0
has optimised crash recovery. Older versions use serial recovery.

For Multi-AZ, check the `recovery_mode` parameter:

```bash
aws rds describe-db-parameters \
  --db-parameter-group-name <param-group> --output json | \
  jq '.Parameters[] | select(.ParameterName == "recovery_mode")'
```

If recovery mode is set to `full` instead of `optimized`,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: RECOVERY_MODE_FULL`.

### Step 12: CloudWatch failover event gap

Symptom: failover occurred but no CloudWatch alarm or EventBridge rule
fired.

```bash
# Check RDS events
aws rds describe-events \
  --source-identifier <cluster-id> --source-type db-cluster \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# Check EventBridge rules for RDS
aws events list-rules --output json | \
  jq '.Rules[] | select(.EventPattern | contains("rds"))'
```

RDS failover events are emitted as:
- `RDS-EVENT-0049`: A Multi-AZ failover has started.
- `RDS-EVENT-0050`: A Multi-AZ failover has completed.
- `RDS-EVENT-0088`: Aurora failover started.
- `RDS-EVENT-0089`: Aurora failover completed.

If no events appear in `describe-events`, the failover may not have
triggered at the RDS service level. If events appear but no alarm
fired, the EventBridge rule or CloudWatch alarm is misconfigured.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: CLOUDWATCH_EVENT_GAP`.

## Output format

```text
TARGET: <cluster-id or instance-id, application context>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the root cause and the failing probe>
ROOT_CAUSE: <APP_NOT_CLUSTER_ENDPOINT | MULTI_AZ_HEALTH_THRESHOLD |
              FAILOVER_PRIORITY_TIER | STORAGE_FULL |
              PARAMETER_GROUP_MISMATCH | OPTION_GROUP_CONFLICT |
              DNS_PROPAGATION_DELAY | CONNECTION_POOL_CACHING |
              AURORA_GLOBAL_FAILOVER_MODE | RDS_PROXY_POOL_DRAIN |
              RECOVERY_MODE_FULL | CLOUDWATCH_EVENT_GAP |
              READ_REPLICA_PROMOTION_FAILURE | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string, failover timeline>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster> in <region>. Proceed?
  (yes/no)"
```

### Worked example — Application using instance endpoint

```text
TARGET: prod-db-cluster, application payments-service
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Aurora cluster failover completed at 03:17 UTC (confirmed
  via RDS events). The writer cluster endpoint resolves to the new
  writer instance within 1 second (DNS TTL verified). However, the
  application connection string uses the instance endpoint
  (prod-db-cluster-instance-1.xxxx.us-east-1.rds.amazonaws.com)
  instead of the cluster endpoint. After failover, instance-1 became
  a reader; the application is connecting to a reader and receiving
  "cannot execute WRITE in a read-only transaction" errors.
ROOT_CAUSE: APP_NOT_CLUSTER_ENDPOINT
EVIDENCE:
  - Symptom: application started receiving "read-only transaction"
    errors at 03:17 UTC, the same time as the Aurora failover event.
  - Probe: aws rds describe-db-clusters shows the cluster Status is
    "available"; the writer endpoint resolves to instance-2 (the new
    writer).
  - Probe: application config shows connection string:
    jdbc:postgresql://prod-db-cluster-instance-1.xxxx.us-east-1.rds.amazonaws.com:5432/prod_db
    (instance endpoint, NOT cluster endpoint).
  - Probe: dig prod-db-cluster-instance-1.xxxx resolves to the reader
    IP; dig prod-db-cluster.cluster-xxxx resolves to the writer IP.
  - Passing: DNS TTL is 1 second (not a DNS issue); connection pool
    maxLifetime is 30s (not a pool caching issue).
REMEDIATION:
  1. Update the application connection string to use the cluster
     endpoint:
     jdbc:postgresql://prod-db-cluster.cluster-xxxx.us-east-1.rds.amazonaws.com:5432/prod_db
  2. Restart or reload the application to pick up the new connection
     string.
  3. Verify by triggering a test failover and confirming the
     application reconnects to the new writer within 30 seconds.
CONFIRM: Before updating the application configuration, confirm:
  "CONFIRM: About to update the payments-service connection string
   from instance endpoint to cluster endpoint. Proceed? (yes/no)"
```

### Worked example — Connection pool caching

```text
TARGET: prod-db-cluster, application orders-api (Java/Spring Boot)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Aurora failover completed at 14:23 UTC (10 seconds). The
  application uses the correct cluster endpoint. DNS TTL is 1 second.
  However, the application did not recover until 14:26 UTC (3 minutes
  later). The JVM DNS cache (networkaddress.cache.ttl) is set to 60
  seconds (Java default), and the HikariCP connection pool has
  maxLifetime=300 (5 minutes). The connection pool held stale
  connections to the old writer IP for up to 5 minutes.
ROOT_CAUSE: CONNECTION_POOL_CACHING
EVIDENCE:
  - Symptom: application errors cleared at 14:26 UTC — 3 minutes
    after the failover completed at 14:23 UTC.
  - Probe: aws rds describe-events shows failover completed at
    14:23:12 UTC.
  - Probe: dig prod-db-cluster.cluster-xxxx shows TTL 1 (correct).
  - Probe: JVM startup flags show -Dnetworkaddress.cache.ttl=60
    (not overridden; Java default).
  - Probe: HikariCP config shows maxLifetime=300000 (5 minutes).
  - Passing: application uses the cluster endpoint (not the instance
    endpoint); OS DNS resolver TTL is 1 second.
REMEDIATION:
  1. Set JVM DNS cache TTL to 1 second:
     -Dnetworkaddress.cache.ttl=1
  2. Reduce HikariCP maxLifetime to 30 seconds or implement an
     onFailover callback that evicts stale connections:
     spring.datasource.hikari.max-lifetime=30000
  3. Alternatively, use the AWS Advanced JDBC Driver (Wrapper) which
     handles failover transparently without connection pool changes.
  4. Verify by triggering a test failover and confirming recovery
     within 30 seconds.
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown (cluster identifier not provided)
VERDICT: INSUFFICIENT_DATA
REASON: The operator reported "Aurora failover did not work" but
  did not provide the cluster identifier, the observed symptom, or
  the application connection string.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: cluster identifier, symptom description, application
    connection string
REMEDIATION: Re-prompt for: (1) the DBClusterIdentifier, (2) the
  observed symptom (did not trigger, took too long, app errors), and
  (3) the application connection string.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER recommend using the instance endpoint for production
  application connections. The instance endpoint does not follow the
  writer after failover. Always use the cluster endpoint (writer
  endpoint for writes, reader endpoint for reads).

- NEVER assume the failover mechanism is broken because the application
  is down. Aurora and Multi-AZ failover automation works correctly in
  the vast majority of cases. The root cause is usually in the
  application layer (wrong endpoint, stale pool) or configuration
  (tier, storage, parameter group).

- NEVER trigger a manual failover to "test" without confirming the
  application will handle it. If the application uses the instance
  endpoint or has stale connection pools, a test failover will cause
  an outage.

- NEVER conclude "failover took 5 minutes" without checking the
  database failover time separately from the application recovery
  time. The DB failover may have completed in 10 seconds; the
  application's connection pool held stale connections for 4.5 minutes.

- NEVER set `PromotionTier` to 0 on all instances without
  understanding the implication. When multiple instances have tier 0,
  the largest is chosen. If you want a specific instance to be the
  promotion target, set it to tier 0 and all others to tier 1+.

- NEVER ignore `FreeStorageSpace` when troubleshooting failover. A
  storage-full instance cannot complete failover. The error does not
  say "storage full" — it says `FailoverFailed` or
  `InsufficientStorage`.

- NEVER assume Aurora Global DB failover is as fast as single-region
  failover. Managed Global failover takes 1-5 minutes (control-plane
  operation + cross-region DNS). Plan for this latency in your RTO.

- NEVER use `recovery_mode: full` when `optimized` is available. Full
  recovery mode extends failover duration by 30-60 seconds for no
  benefit in production workloads.

- NEVER assume RDS Proxy eliminates all failover impact. The Proxy
  reduces connection errors but active transactions on the old writer
  are rolled back. The Proxy pool drains over 5-30 seconds.

- NEVER modify parameter groups or option groups on a production
  cluster without verifying compatibility between primary and standby.
  A mismatch can prevent the standby from being promoted.

- NEVER conclude no failover occurred just because no CloudWatch alarm
  fired. Check `describe-events` directly — the alarm may be
  misconfigured, not the failover.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`failover-db-cluster`, `modify-db-instance`, `promote-read-replica`,
  `failover-global-cluster`), emit and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-db-clusters`, `describe-db-instances`,
  `describe-events`, `get-metric-statistics`, `dig`). Do not perform
  state-changing operations as diagnostic probes.

- **Manual failover** causes a brief outage (10-120 seconds depending
  on engine). Always confirm before `failover-db-cluster`.

- **`modify-db-instance --promotion-tier`** is applied immediately but
  does not affect the current writer. It only affects the next
  failover.

- **Increasing allocated storage** (`--allocated-storage`) is applied
  online for most engines but may cause a brief I/O suspension for
  older MySQL versions.

- **Parameter group changes** may require a reboot to take effect.
  For Multi-AZ, the reboot triggers a failover. Always use
  `--no-apply-immediately` if the change should wait for the next
  maintenance window.

- **Option group changes** can cause the engine to restart. For
  Multi-AZ, this triggers a failover.

## Remediation guidance

### For APP_NOT_CLUSTER_ENDPOINT

Update the application connection string to use the cluster endpoint:

```text
# Writer endpoint (for read/write workloads):
<cluster>.cluster-<id>.<region>.rds.amazonaws.com

# Reader endpoint (for read-only workloads):
<cluster>.cluster-ro-<id>.<region>.rds.amazonaws.com
```

### For DNS_PROPAGATION_DELAY

Set JVM DNS cache TTL:
```
-Dnetworkaddress.cache.ttl=1
```

Set OS DNS resolver max TTL (systemd-resolved):
```bash
# /etc/systemd/resolved.conf
[Resolve]
Cache=no
```

### For CONNECTION_POOL_CACHING

Reduce connection pool `maxLifetime` to 30 seconds or implement
failover-aware connection eviction. Use the AWS Advanced JDBC Driver
or AWS Advanced Python Driver for transparent failover handling.

### For MULTI_AZ_HEALTH_THRESHOLD

Multi-AZ failover only triggers on unreachability, not performance
degradation. If the primary is degraded but responsive, consider:
- Adding a performance-based failover trigger via EventBridge + Lambda.
- Using Aurora (which has faster failover than Multi-AZ).

### For FAILOVER_PRIORITY_TIER

```bash
aws rds modify-db-instance \
  --db-instance-identifier <target-instance> \
  --promotion-tier 0 --apply-immediately
```

### For STORAGE_FULL

```bash
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --allocated-storage <new-size> --apply-immediately
```

Set up a CloudWatch alarm on `FreeStorageSpace` < 10% to catch this
before the next failover.

### For PARAMETER_GROUP_MISMATCH

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --db-parameter-group-name <primary-param-group> \
  --apply-immediately
```

### For OPTION_GROUP_CONFLICT

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --option-group-name <primary-option-group> \
  --apply-immediately
```

### For AURORA_GLOBAL_FAILOVER_MODE

Managed failover:
```bash
aws rds failover-global-cluster \
  --global-cluster-identifier <global-cluster-id> \
  --target-db-cluster-identifier <secondary-cluster-arn>
```

Unmanaged failover (faster, requires manual coordination):
```bash
aws rds remove-from-global-cluster \
  --db-cluster-identifier <secondary-cluster-arn>
aws rds promote-read-replica-db-cluster \
  --db-cluster-identifier <secondary-cluster-id>
```

### For RDS_PROXY_POOL_DRAIN

Check and update proxy target group settings. Ensure
`ConnectionBorrowTimeout` is set to a value that tolerates the
failover drain window (5-30 seconds).

### For RECOVERY_MODE_FULL

Update the parameter group to use optimised recovery:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier <cluster-id> \
  --db-cluster-parameter-group-name <param-group-with-optimized-recovery>
```

### For READ_REPLICA_PROMOTION_FAILURE

Address the underlying issue (replication lag, storage, network):
- Wait for replication lag to drop to zero.
- Increase storage if storage-full.
- Check cross-region network connectivity.

Then retry promotion:
```bash
aws rds promote-read-replica-db-cluster \
  --db-cluster-identifier <replica-cluster-id>
```

## Deep reference: Aurora and Multi-AZ failover model

### Aurora cluster endpoint types

| Endpoint type | ARN pattern | Behaviour after failover |
|---|---|---|
| Writer (cluster) endpoint | `<cluster>.cluster-<id>.<region>.rds.amazonaws.com` | Resolves to the new writer (dynamic) |
| Reader endpoint | `<cluster>.cluster-ro-<id>.<region>.rds.amazonaws.com` | Load-balances across reader instances (dynamic) |
| Custom endpoint | `<cluster>.custom-<id>.<region>.rds.amazonaws.com` | Routes to specified instances (static membership if type=INSTANCE) |
| Instance endpoint | `<instance>.<id>.<region>.rds.amazonaws.com` | Resolves to a specific instance (does NOT follow failover) |

### Failover timeline comparison

| Phase | Aurora | Multi-AZ |
|---|---|---|
| Detection | 5-10 seconds | 30-60 seconds |
| Promotion | 5-15 seconds (parallel recovery) | 60-120 seconds (full recovery) |
| DNS update | < 1 second (TTL 1s) | < 30 seconds (TTL varies) |
| Total | 10-30 seconds | 60-120 seconds |

### Failover priority tier matrix

| Tier | Promotion order | Typical use |
|---|---|---|
| 0 | First | Intended failover target (largest instance) |
| 1 | Second | Secondary failover target |
| 2-14 | By tier | Lower-priority instances |
| 15 (default) | Last | Replicas not intended for promotion |

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

## Domain

AWS CloudOps / RDS and Aurora Database Failover, High Availability,
Cluster Endpoint Management, Multi-AZ Configuration, Aurora Global DB,
and RDS Proxy.

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
