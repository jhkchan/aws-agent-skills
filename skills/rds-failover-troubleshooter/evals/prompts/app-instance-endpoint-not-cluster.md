# Eval prompt: app-instance-endpoint-not-cluster

Diagnose the Aurora failover issue for the following scenario. Walk
the diagnostic decision tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE, REMEDIATION).

Symptom: Aurora PostgreSQL cluster `prod-db-cluster` failed over
automatically at 03:17 UTC. The writer cluster endpoint resolved to
the new writer (instance-2) within 1 second. However, the application
(payments-service) continued receiving "cannot execute WRITE in a
read-only transaction" errors. The application did not recover until
manually restarted.

```text
DBClusterIdentifier: prod-db-cluster
Engine: aurora-postgresql
EngineVersion: 16.2
WriterEndpoint: prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com

DBClusterMembers:
  - instance-1: was writer, now reader (PromotionTier: 15)
  - instance-2: was reader, now writer (PromotionTier: 0)

Application connection string:
  jdbc:postgresql://prod-db-cluster-instance-1.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com:5432/prod_db

RDS events:
  03:17:05 — RDS-EVENT-0088: Aurora failover started
  03:17:18 — RDS-EVENT-0089: Aurora failover completed

DNS:
  prod-db-cluster.cluster-xxxx → instance-2 IP (new writer), TTL 1s
  prod-db-cluster-instance-1.xxxx → instance-1 IP (now reader), TTL 300s

JVM DNS cache: networkaddress.cache.ttl=60
Connection pool: HikariCP maxLifetime=30s
```

The application is using the instance endpoint instead of the cluster
endpoint. After failover, instance-1 became a reader. Verify the
connection string and recommend the fix.
