# Worked examples (secondary) — rds-failover-troubleshooter (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Worked example — Connection pool caching

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

## Worked example — INSUFFICIENT_DATA

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

