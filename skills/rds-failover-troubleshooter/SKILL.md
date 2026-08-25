---
name: rds-failover-troubleshooter
description: 'Diagnoses RDS and Aurora failover issues through a thirteen-category diagnostic tree: Multi-AZ failover not triggering (health check threshold too conservative), failover taking too long (DNS propagation, recovery mode full), Aurora writer endpoint not redirecting (application using instance endpoint instead of cluster endpoint), read replica promotion failures (network connectivity, storage), storage-full preventing failover (allocated storage exhausted), parameter group mismatch between primary and standby, option group conflicts preventing standby from taking over, Aurora cluster endpoint type confusion (writer vs reader vs custom vs instance), failover priority tier misconfiguration (tier 0 vs tier 1 not set on the intended promotion target), Aurora Global DB failover (managed vs unmanaged), RDS Proxy failover behavior (connection pool not draining), application connection string not using cluster endpoint, and CloudWatch failover event gaps. Walks symptoms to a verified root cause with...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and cluster configuration. Live-account diagnosis uses aws rds describe-db-clusters, aws rds describe-db-instances, aws rds describe-db-cluster-endpoints, aws rds describe-db-cluster-parameter-groups, aws rds describe-events, aws cloudwatch get-metric-statistics, aws ec2 describe-route-tables, aws ec2 describe-security-groups, and aws logs...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an RDS or Aurora failover issue (Multi-AZ failover not triggering, failover taking too long, writer endpoint not redirecting, read replica promotion failure, storage-full preventing failover, parameter group mismatch, option group conflict, failover priority misconfiguration, Aurora Global DB failover, RDS Proxy failover, application connection issues), walking a symptom to the failed layer with verify commands, or triaging a "failover did not work" incident where the root cause may be endpoint configuration, health threshold, storage, parameter group, option group, failover tier, or application connection string — not necessarily the database engine itself.
  when_not_to_use: RDS connectivity debugging (use rds-connectivity-troubleshooter), RDS performance tuning (use rds-cost-optimizer for right-sizing), Aurora backup and restore (use rds-backup-restore-operator), or RDS instance creation (use rds-instance-deployer). This skill diagnoses failover-time issues; it does not tune query performance or audit steady-state security posture.
  activation_triggers: RDS failover not working, Aurora failover not triggering, Multi-AZ failover failed, Aurora writer endpoint not redirecting, RDS failover taking too long, Aurora failover priority, read replica promotion failed, storage-full failover, parameter group mismatch failover, option group conflict failover, Aurora Global DB failover, RDS Proxy failover, application not connecting after failover, Aurora cluster endpoint confusion, troubleshoot RDS failover
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "failover took 5 minutes", "writer endpoint still points to old instance"), optionally paired with the cluster configuration and recent RDS events, OR (b) a DB cluster identifier plus caller context (application connection string, observed error) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/ROOT_CAUSE/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and ROOT_CAUSE ∈ {APP_NOT_CLUSTER_ENDPOINT, MULTI_AZ_HEALTH_THRESHOLD, FAILOVER_PRIORITY_TIER, STORAGE_FULL, PARAMETER_GROUP_MISMATCH, OPTION_GROUP_CONFLICT, DNS_PROPAGATION_DELAY, CONNECTION_POOL_CACHING, AURORA_GLOBAL_FAILOVER_MODE, RDS_PROXY_POOL_DRAIN, RECOVERY_MODE_FULL, CLOUDWATCH_EVENT_GAP, READ_REPLICA_PROMOTION_FAILURE, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Aurora PostgreSQL cluster prod-db-cluster

    failed over automatically at 03:17 UTC. The writer

    endpoint resolved to the new writer within 1 second,

    but the application continued hitting the old writer

    for 90 seconds, then connection errors cleared."

    DBClusterIdentifier: prod-db-cluster

    Engine: aurora-postgresql

    WriterEndpoint: prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com

    Application connection string: uses the instance endpoint

    prod-db-cluster-instance-1.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com

    instead of the cluster endpoint'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: RDS, Aurora, failover, Multi-AZ, writer endpoint, cluster endpoint, read replica promotion, storage-full, parameter group mismatch, option group conflict, failover priority, tier 0, Aurora Global DB, RDS Proxy, connection pool, DNS propagation, CloudWatch failover events, troubleshooting
  tags: rds, aurora, databases, troubleshooting, failover, multi-az, high-availability, cluster-endpoint, rds-proxy
---

# RDS Failover Troubleshooter

## Quick start

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## Mindset

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## Philosophy

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


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

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


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

> Moved verbatim to [`references/error-handling.md`](references/error-handling.md) — load on demand.


## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the root-cause-specific probes in
order.

### Step 0: Non-obvious behaviours that change diagnosis

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


### Step 1: Application connection string check

Symptom: failover completed (new writer is active, cluster endpoint
resolves correctly), but the application still cannot connect.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


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

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


Check the application's DNS caching layers:

> Moved verbatim to [`references/error-handling.md`](references/error-handling.md) — load on demand.


If a caching layer is holding the old IP,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: DNS_PROPAGATION_DELAY`
(OS/JVM DNS cache) or `ROOT_CAUSE: CONNECTION_POOL_CACHING`
(connection pool).

### Step 3: Multi-AZ health check threshold

Symptom: primary instance is unhealthy (high CPU, stuck queries) but
failover does not trigger.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


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

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


Aurora failover promotion order:
1. Lowest `PromotionTier` (tier 0 first).
2. Within the same tier, largest `DBInstanceClass`.
3. Within the same tier and class, longest uptime.

If the intended promotion target has tier 15 (default) but another
instance has tier 0, the tier 0 instance is promoted.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: FAILOVER_PRIORITY_TIER`.

Fix: set the intended target to tier 0:

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


### Step 5: Storage-full check

Symptom: failover event appears in RDS events but the new writer does
not become available. Error: `InsufficientStorage` or
`FailoverFailed`.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


If `FreeStorageSpace` is near zero (< 5 GB) or `DBInstanceStatus` is
`storage-full`, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: STORAGE_FULL`.

Fix: increase allocated storage:

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


### Step 6: Parameter group mismatch

Symptom: standby instance fails health checks during promotion. RDS
events show a promotion failure with parameter-related errors.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


If the primary and standby have different DB parameter groups with
incompatible settings, the standby may fail during promotion.
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: PARAMETER_GROUP_MISMATCH`.

Fix: align the parameter groups:

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


### Step 7: Option group conflict

Symptom: standby cannot start the engine after promotion. RDS events
show an option-group-related error.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


If the option groups are incompatible (e.g., primary has TDE, standby
does not), **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: OPTION_GROUP_CONFLICT`.

Fix: align the option groups:

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


### Step 8: Read replica promotion failure

Symptom: a read replica (Aurora or cross-region) cannot be promoted
to a standalone cluster/instance.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


Common promotion failures:
- High replication lag (the replica has not caught up).
- Network connectivity to the source (for cross-region).
- Storage-full on the replica.
- Parameter group mismatch.

If any of these apply, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: READ_REPLICA_PROMOTION_FAILURE`.

### Step 9: Aurora Global DB failover mode

Symptom: Aurora Global DB failover did not work or took too long.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


Managed failover (`failover-global-cluster`) is a control-plane
operation that takes 1-5 minutes. Unmanaged failover (detach secondary
+ promote) is faster but requires manual coordination.

If the failover mode is misconfigured or the secondary cluster has
high replication lag, **ROOT_CAUSE_IDENTIFIED** with
`ROOT_CAUSE: AURORA_GLOBAL_FAILOVER_MODE`.

### Step 10: RDS Proxy failover

Symptom: RDS Proxy does not transparently handle failover; application
sees connection errors.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


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

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


Aurora PostgreSQL 13+ supports parallel WAL replay. Aurora MySQL 8.0
has optimised crash recovery. Older versions use serial recovery.

For Multi-AZ, check the `recovery_mode` parameter:

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


If recovery mode is set to `full` instead of `optimized`,
**ROOT_CAUSE_IDENTIFIED** with `ROOT_CAUSE: RECOVERY_MODE_FULL`.

### Step 12: CloudWatch failover event gap

Symptom: failover occurred but no CloudWatch alarm or EventBridge rule
fired.

> Moved verbatim to [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — load on demand.


> Moved verbatim to [`references/error-handling.md`](references/error-handling.md) — load on demand.


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

> Moved verbatim to [`references/worked-examples.md`](references/worked-examples.md) — load on demand.


### Worked example — INSUFFICIENT_DATA

> Moved verbatim to [`references/worked-examples.md`](references/worked-examples.md) — load on demand.


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

> Moved verbatim to [`references/error-handling.md`](references/error-handling.md) — load on demand.


## Deep reference: Aurora and Multi-AZ failover model

> Moved verbatim to [`references/aurora-endpoint-reference.md`](references/aurora-endpoint-reference.md) — load on demand.


> Moved verbatim to [`references/failover-priority-reference.md`](references/failover-priority-reference.md) — load on demand.


> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## Recent AWS features (2024-2026)

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.


## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight sweep and every Step 1-12 probe/fix CLI listing.
- [references/error-handling.md](references/error-handling.md) — malformed-input INSUFFICIENT_DATA contract, DNS caching fix table, failover event codes, full per-root-cause remediation guidance.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (connection pool caching, INSUFFICIENT_DATA).
- [references/advanced-patterns.md](references/advanced-patterns.md) — quick-start bullets, mindset, philosophy, Step 0 non-obvious behaviours, Global DB failover modes, recent AWS features, AWS documentation links.
- [references/aurora-endpoint-reference.md](references/aurora-endpoint-reference.md) — Aurora cluster endpoint types and post-failover behaviour.
- [references/failover-priority-reference.md](references/failover-priority-reference.md) — failover timeline comparison and promotion tier matrix.

## Domain

AWS CloudOps / RDS and Aurora Database Failover, High Availability,
Cluster Endpoint Management, Multi-AZ Configuration, Aurora Global DB,
and RDS Proxy.

## AWS documentation

> Moved verbatim to [`references/advanced-patterns.md`](references/advanced-patterns.md) — load on demand.

