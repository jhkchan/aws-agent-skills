# Eval prompt: connection-pool-hikari-stale-cache

Diagnose the Aurora failover issue for the following scenario. Walk
the diagnostic decision tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Aurora MySQL cluster `orders-db-cluster` failed over at
14:23 UTC. The DB failover completed in 12 seconds. The application
(orders-api, Java/Spring Boot) did not recover until 14:27:30 UTC —
4.5 minutes later. The application uses the correct cluster endpoint.

```text
DBClusterIdentifier: orders-db-cluster
Engine: aurora-mysql
EngineVersion: 8.0.mysql_aurora.3.05.2

Application connection string:
  jdbc:mysql://orders-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com:3306/orders_db

RDS events:
  14:23:12 — RDS-EVENT-0088: Aurora failover started
  14:23:24 — RDS-EVENT-0089: Aurora failover completed

DNS:
  orders-db-cluster.cluster-xxxx → new writer IP, TTL 1 second (verified)

JVM configuration:
  networkaddress.cache.ttl=60 (Java default, not overridden)

HikariCP configuration:
  maxLifetime=300000 (5 minutes)
  maximumPoolSize=20
  connectionTimeout=30000 (30 seconds)

Application error pattern:
  14:23:24 to 14:27:30: "Communications link failure" and
    "Connection refused" errors
  14:27:30: errors cleared (coincides with connection pool cycling
    connections at maxLifetime boundary)
```

The application uses the correct cluster endpoint but the connection
pool and JVM DNS cache are holding stale connections. Verify the
caching layers and recommend the fix.
