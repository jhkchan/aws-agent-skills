# Error handling — rds-failover-troubleshooter (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Malformed input — INSUFFICIENT_DATA contract

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

## Step 2 — DNS caching layers (default TTL and fix)

| Layer | Default TTL | Fix |
|---|---|---|
| OS DNS resolver (systemd-resolved, dnsmasq) | 30-60 seconds | Set `cache-max-ttl` to 1 second, or disable caching |
| JVM DNS cache (`networkaddress.cache.ttl`) | 60 seconds (Java 8+); some frameworks override | Set `-Dnetworkaddress.cache.ttl=1` |
| Database driver connection pool (HikariCP, c3p0, pgxpool) | Varies; pools hold connections until closed | Set `maxLifetime` < 30s, or implement `onFailover` callback |
| Application-level DNS cache | Varies | Disable or set TTL to 1 second |

## RDS failover event codes

RDS failover events are emitted as:
- `RDS-EVENT-0049`: A Multi-AZ failover has started.
- `RDS-EVENT-0050`: A Multi-AZ failover has completed.
- `RDS-EVENT-0088`: Aurora failover started.
- `RDS-EVENT-0089`: Aurora failover completed.

## Remediation guidance (per root cause)

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

