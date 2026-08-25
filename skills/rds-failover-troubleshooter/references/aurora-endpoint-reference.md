# Aurora and Multi-AZ Endpoint Reference Guide

Supplementary reference for the RDS Failover Troubleshooter skill.
Loaded on-demand when a diagnostic needs Aurora cluster endpoint types,
DNS TTL values, connection pool failover behavior, or failover timeline
details.

## Aurora cluster endpoint types

| Endpoint type | Format | Behaviour after failover | DNS TTL |
|---|---|---|---|
| Writer (cluster) endpoint | `<cluster>.cluster-<id>.<region>.rds.amazonaws.com` | Resolves to the new writer instance (dynamic) | 1 second |
| Reader endpoint | `<cluster>.cluster-ro-<id>.<region>.rds.amazonaws.com` | Load-balances across reader instances (dynamic) | 1 second |
| Custom endpoint | `<cluster>.custom-<id>.<region>.rds.amazonaws.com` | Routes to specified instances; STATIC membership unless type=READER | 1 second |
| Instance endpoint | `<instance>.<id>.<region>.rds.amazonaws.com` | Resolves to a specific instance; does NOT follow failover | 5 seconds |

### When to use each endpoint

| Use case | Correct endpoint |
|---|---|
| Application read/write (production) | Writer (cluster) endpoint |
| Application read-only scaling | Reader endpoint |
| Specific instance targeting (debug, analytics) | Instance endpoint |
| Read/write isolation with custom routing | Custom endpoint (type=READER for reads, type=INSTANCE for specific) |
| Cross-region read replicas | Instance endpoint (each region has its own cluster endpoint) |

### Multi-AZ endpoint behavior

Multi-AZ RDS instances do NOT have a cluster endpoint. The instance
endpoint (`<instance>.<id>.<region>.rds.amazonaws.com`) IS the failover
endpoint — RDS updates the DNS record to point to the standby after
failover. The DNS TTL for Multi-AZ is typically 5 seconds but the
failover itself takes 60-120 seconds.

This is a key difference from Aurora:
- **Aurora:** cluster endpoint follows the writer; instance endpoints
  do NOT follow.
- **Multi-AZ:** the single instance endpoint DOES follow (DNS record
  updated to the new primary after failover).

## Failover timeline comparison

### Aurora failover (single-region)

| Phase | Duration | What happens |
|---|---|---|
| Detection | 5-10 seconds | Health monitor detects writer unresponsive |
| Election | 1-2 seconds | Aurora selects the new writer based on PromotionTier |
| Promotion | 5-15 seconds | Reader instance promoted to writer (no storage copy — shared volume) |
| DNS update | < 1 second | Cluster endpoint DNS record updated (TTL 1s) |
| **Total** | **10-30 seconds** | |

### Multi-AZ failover

| Phase | Duration | What happens |
|---|---|---|
| Detection | 30-60 seconds | Health monitor detects primary unresponsive |
| Promotion | 60-120 seconds | Standby promoted (block-level recovery) |
| DNS update | < 30 seconds | Instance endpoint DNS record updated (TTL ~5s) |
| **Total** | **60-120 seconds** | |

### Aurora Global DB failover

| Phase | Duration (managed) | Duration (unmanaged) |
|---|---|---|
| Detection | 10-30 seconds | 10-30 seconds |
| Promotion | 30-60 seconds | 10-15 seconds |
| Cross-region DNS | 60-120 seconds | Manual (operator updates Route 53) |
| **Total** | **1-5 minutes** | **30-90 seconds + manual DNS** |

## Connection pool failover behavior

| Pool/Driver | Default TTL | Failover behavior | Fix |
|---|---|---|---|
| HikariCP (Java) | `maxLifetime=1800s` (30 min) | Holds stale connections until maxLifetime expires | Set `maxLifetime=30s`; implement `connectionTestQuery` |
| c3p0 (Java) | `maxIdleTime=0` (never) | Holds stale connections indefinitely | Set `maxIdleTime=30s`; `idleConnectionTestPeriod=15s` |
| pgxpool (Go) | `max_conn_lifetime=1h` | Holds stale connections for 1 hour | Set `max_conn_lifetime=30s` |
| SQLAlchemy (Python) | `pool_recycle=3600s` | Holds stale connections for 1 hour | Set `pool_recycle=30s` |
| Node.js pg (pg-pool) | `idleTimeoutMillis=30000` | Recycles idle connections every 30s | Already reasonable; verify |
| AWS Advanced JDBC Driver | N/A | Transparent failover (topology-aware) | Use as drop-in replacement |

### JVM DNS cache

| Setting | Default | Effect |
|---|---|---|
| `networkaddress.cache.ttl` (Java 8+) | 60 seconds | JVM caches DNS results for 60 seconds regardless of DNS TTL |
| `networkaddress.cache.negative.ttl` | 10 seconds | Caches negative (NXDOMAIN) results |

Set `-Dnetworkaddress.cache.ttl=1` for production database connections
to honour the Aurora 1-second DNS TTL.

### OS DNS resolver caching

| Resolver | Default cache TTL | Fix |
|---|---|---|
| systemd-resolved | 30-60 seconds | Set `Cache=no` in `/etc/systemd/resolved.conf` |
| dnsmasq | `cache-max-ttl=1500` (25 min) | Set `cache-max-ttl=1` |
| glibc (no caching daemon) | Honours DNS TTL | No change needed |
| macOS mDNSResponder | Honours DNS TTL (usually) | `sudo dscacheutil -flushcache` to clear |

## RDS event codes for failover

| Event code | Message | Meaning |
|---|---|---|
| RDS-EVENT-0049 | "Multi-AZ failover has started" | Multi-AZ failover initiated |
| RDS-EVENT-0050 | "Multi-AZ failover has completed" | Multi-AZ failover succeeded |
| RDS-EVENT-0088 | "Aurora failover started" | Aurora cluster failover initiated |
| RDS-EVENT-0089 | "Aurora failover completed" | Aurora cluster failover succeeded |
| RDS-EVENT-0006 | "DB instance failover failed" | Failover failed (check reason) |
| RDS-EVENT-0065 | "DB instance has insufficient storage" | Storage-full; blocks failover |
| RDS-EVENT-0004 | "DB instance configuration mismatch" | Parameter/option group mismatch |

### EventBridge patterns for RDS failover

```json
{
  "source": ["aws.rds"],
  "detail-type": ["RDS DB Instance Event", "RDS DB Cluster Event"],
  "detail": {
    "EventCategories": ["failover"]
  }
}
```

Use this pattern to trigger Lambda or SNS notifications on failover
events for proactive application connection refresh.

## Aurora cluster endpoint types (moved from SKILL.md deep reference)

### Aurora cluster endpoint types

| Endpoint type | ARN pattern | Behaviour after failover |
|---|---|---|
| Writer (cluster) endpoint | `<cluster>.cluster-<id>.<region>.rds.amazonaws.com` | Resolves to the new writer (dynamic) |
| Reader endpoint | `<cluster>.cluster-ro-<id>.<region>.rds.amazonaws.com` | Load-balances across reader instances (dynamic) |
| Custom endpoint | `<cluster>.custom-<id>.<region>.rds.amazonaws.com` | Routes to specified instances (static membership if type=INSTANCE) |
| Instance endpoint | `<instance>.<id>.<region>.rds.amazonaws.com` | Resolves to a specific instance (does NOT follow failover) |

