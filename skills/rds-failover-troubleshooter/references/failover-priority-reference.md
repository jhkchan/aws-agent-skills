# Aurora Failover Priority and Global DB Reference Guide

Supplementary reference for the RDS Failover Troubleshooter skill.
Loaded on-demand when a diagnostic needs failover tier details, Global
DB failover modes, RDS Proxy failover behavior, or storage-full
thresholds.

## Failover priority tier matrix

Aurora assigns a PromotionTier (0-15) to each instance in a cluster.
Lower tier = higher priority for promotion.

| Tier | Promotion order | Typical use |
|---|---|---|
| 0 | **First** | Intended failover target (usually the largest instance) |
| 1 | Second | Secondary failover target |
| 2-14 | By tier number | Lower-priority instances |
| 15 (default) | **Last** | Replicas not intended for promotion |

### Tie-breaking rules within the same tier

1. **Largest instance class wins.** A `db.r6g.4xlarge` beats a
   `db.r6g.2xlarge` at the same tier.
2. **If same instance class, longest uptime wins.** The instance that
   has been running the longest is preferred (it has the warmest
   cache).
3. **If same uptime (rare), random selection.**

### Common misconfiguration patterns

| Pattern | Effect | Fix |
|---|---|---|
| All instances at tier 15 (default) | Largest instance promoted (arbitrary) | Set the intended target to tier 0 |
| Two instances at tier 0, different sizes | Larger one promoted (correct) | Verify size before setting tier 0 |
| Two instances at tier 0, same size | Longer uptime promoted (may surprise) | Set only the intended target to tier 0 |
| Intended target at tier 0, another at tier 0 unintentionally | Unintended instance may be promoted | Audit all instances' tiers after adding new replicas |

### Setting failover priority

```bash
# Set an instance to tier 0 (highest priority)
aws rds modify-db-instance \
  --db-instance-identifier <target-instance> \
  --promotion-tier 0 --apply-immediately

# Verify
aws rds describe-db-instances \
  --db-instance-identifier <target-instance> --output json | \
  jq '.DBInstances[].PromotionTier'
```

## Aurora Global DB failover modes

### Managed failover (recommended)

```bash
aws rds failover-global-cluster \
  --global-cluster-identifier <global-cluster-id> \
  --target-db-cluster-identifier <arn-of-secondary-cluster>
```

- Duration: 1-5 minutes
- AWS manages DNS update across regions
- Secondary cluster is promoted; old primary becomes a secondary
- Application must reconnect (DNS TTL varies by region)
- **Planned failover** variant: `--allow-data-loss false` (for
  scheduled migrations with zero data loss)

### Unmanaged failover (faster, manual)

```bash
# 1. Remove the secondary from the global cluster
aws rds remove-from-global-cluster \
  --global-cluster-identifier <global-cluster-id> \
  --db-cluster-identifier <arn-of-secondary-cluster>

# 2. Promote the secondary to a standalone primary
aws rds promote-read-replica-db-cluster \
  --db-cluster-identifier <secondary-cluster-id>

# 3. Update Route 53 or application DNS to point to the new region
```

- Duration: 30-90 seconds (excluding manual DNS)
- Operator manages DNS update (Route 53 health checks, weighted
  routing)
- Data loss possible if replication lag > 0 at detachment time

### Global DB replication lag

| Metric | Meaning | Impact on failover |
|---|---|---|
| `AuroraGlobalDBReplicationLag` | Milliseconds behind primary | If > 0, data loss on failover |
| `AuroraGlobalDBDataTransferBytes` | Bytes transferred per second | High lag indicates network bottleneck |

Check lag before failover:

```bash
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name AuroraGlobalDBReplicationLag \
  --dimensions Name=DBClusterIdentifier,Value=<secondary-cluster-id> \
  --start-time $(date -d '-15 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Maximum,Average --output json
```

## RDS Proxy failover behavior

### How Proxy handles Multi-AZ / Aurora failover

1. **Detection:** Proxy detects the writer change via RDS event
   notifications (typically within 5 seconds).
2. **Pool drain:** Existing connections to the old writer are drained
   (active transactions are allowed to complete or timeout).
3. **Reconnect:** Proxy establishes new connections to the new writer.
4. **Resume:** Queued client requests are forwarded to the new writer.

Total Proxy recovery: 5-30 seconds (no client-side connection errors).

### Proxy configuration for failover

| Setting | Default | Recommended for HA | Effect |
|---|---|---|---|
| `IdleClientTimeout` | 1800s (30 min) | 120s | Disconnect idle clients faster |
| `MaxConnectionsPercent` | 100% of DB max | 80% | Leave headroom for failover reconnect |
| `RequireTLS` | false | true | Security (does not affect failover) |
| Target group health check | 30s | 10s | Faster detection of writer change |

### Proxy target group states

| State | Meaning |
|---|---|
| `AVAILABLE` | Target is healthy and accepting connections |
| `UNAVAILABLE` | Target is unhealthy; connections routed elsewhere |
| `TRACKING` | Target is in transition (failover in progress) |
| `UPDATING` | Proxy is updating the target's writer/reader status |

## Storage-full thresholds

| Check | Threshold | Action |
|---|---|---|
| `FreeStorageSpace` CloudWatch | < 10% of allocated | Alarm + increase storage |
| `FreeStorageSpace` absolute | < 5 GB | Critical — failover may fail |
| `DBInstanceStatus: storage-full` | 0 GB free | Failover WILL fail with InsufficientStorage |

### Auto-scaling storage

RDS supports storage auto-scaling for most engines:

```bash
# Check if auto-scaling is enabled
aws rds describe-db-instances \
  --db-instance-identifier <id> --output json | \
  jq '.DBInstances[].MaxAllocatedStorage'

# Enable auto-scaling (10 TB max)
aws rds modify-db-instance \
  --db-instance-identifier <id> \
  --max-allocated-storage 10000 --apply-immediately
```

Aurora clusters use a shared storage volume that auto-scales (up to
128 TB). Storage-full on Aurora is extremely rare but can occur if the
account-level storage quota is hit.

## Parameter group alignment for Multi-AZ

For Multi-AZ, the primary and standby MUST use the same DB parameter
group and option group. A mismatch prevents failover.

### Common parameter group mismatches

| Parameter | Effect if mismatched | How to detect |
|---|---|---|
| `max_connections` | Standby has fewer connections; health check fails | `describe-db-instances` for parameter groups |
| `shared_buffers` | Standay has less memory allocated; OOM on promotion | Compare `show shared_buffers` on both |
| `work_mem` | Different query plans on standby; timeout on promotion | Compare parameter group versions |
| `logging_collector` | Different log behavior; health check script fails | Check `describe-db-parameters` |
| `ssl` / `rds.force_ssl` | TLS mismatch; connection refused | Check SSL parameters |

### Option group conflicts

| Engine | Option | Effect if standby missing |
|---|---|---|
| Oracle | TDE (Transparent Data Encryption) | Standby cannot read encrypted data |
| SQL Server | .NET Framework | Engine fails to start |
| PostgreSQL | pg_stat_statements | Health check query fails |
| MySQL | audit plugin | Audit gap; may not block promotion |

Always verify option group alignment after modifying the primary's
option group.
