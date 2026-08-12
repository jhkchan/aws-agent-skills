# Example usage: rds-failover-troubleshooter

A walkthrough showing the skill diagnosing an Aurora failover issue
where the application continued receiving errors after the database
failover completed successfully, demonstrating the cluster-endpoint-vs-
instance-endpoint diagnostic, the DNS TTL and connection pool analysis,
the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the targeted
remediation.

## Input (user prompt)

> Our Aurora PostgreSQL cluster failed over at 03:17 UTC. The
> database events show the failover completed in 13 seconds. But our
> payments-service kept getting "cannot execute WRITE in a read-only
> transaction" errors for 18 minutes until we manually restarted it.
> The database layer looks healthy. Help us find why the application
> didn't recover.

```text
DBClusterIdentifier: prod-db-cluster
Engine: aurora-postgresql
EngineVersion: 16.2
WriterEndpoint: prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com

DBClusterMembers:
  - instance-1: was writer, now reader (PromotionTier: 15)
  - instance-2: was reader, now writer (PromotionTier: 0)

Application connection string (from payments-service config):
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

## Skill output

```text
TARGET: prod-db-cluster, application payments-service
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The Aurora failover completed at 03:17:18 UTC (13 seconds).
  The writer cluster endpoint resolves to instance-2 (the new writer)
  within 1 second (DNS TTL verified). However, the application's
  connection string uses the INSTANCE endpoint
  (prod-db-cluster-instance-1.xxxx...) instead of the CLUSTER endpoint
  (prod-db-cluster.cluster-xxxx...). After failover, instance-1 became
  a reader. The application is connecting to a reader and receiving
  "cannot execute WRITE in a read-only transaction" because the reader
  is read-only.
ROOT_CAUSE: APP_NOT_CLUSTER_ENDPOINT
EVIDENCE:
  - Symptom: application started receiving "cannot execute WRITE in a
    read-only transaction" at 03:17 UTC — exactly when the Aurora
    failover event occurred. Errors persisted until the application
    was manually restarted at 03:35 UTC.
  - Probe: aws rds describe-db-clusters shows the cluster Status is
    "available"; instance-2 is the writer (IsClusterWriter: true);
    instance-1 is a reader (IsClusterWriter: false).
  - Probe: application config shows connection string:
    jdbc:postgresql://prod-db-cluster-instance-1.xxxxxxxxxxxx.us-east-1.rds.amazonaws.com:5432/prod_db
    This is the INSTANCE endpoint, NOT the cluster endpoint.
  - Probe: dig prod-db-cluster-instance-1.xxxx resolves to instance-1's
    IP (now a reader); dig prod-db-cluster.cluster-xxxx resolves to
    instance-2's IP (the new writer). The cluster endpoint is correct;
    the application is not using it.
  - Passing: DNS TTL for the cluster endpoint is 1 second (not a DNS
    propagation issue); HikariCP maxLifetime is 30s (not a connection
    pool caching issue for this root cause — the pool IS cycling
    connections, but they all go to the instance endpoint which is a
    reader).
REMEDIATION:
  1. Update the application connection string to use the cluster
     endpoint:
     jdbc:postgresql://prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com:5432/prod_db
  2. Redeploy or reload the application to pick up the new connection
     string.
  3. Set up a CloudWatch alarm on RDS-EVENT-0088 (Aurora failover
     started) to proactively notify the on-call engineer, reducing
     detection time from 18 minutes to seconds.
  4. Optionally, adopt the AWS Advanced JDBC Driver which transparently
     follows the Aurora writer endpoint, eliminating this class of
     issue entirely.
  5. Verify by triggering a test failover and confirming the
     application reconnects to the new writer within 30 seconds.
CONFIRM: Before updating the application configuration, confirm:
  "CONFIRM: About to update the payments-service connection string
   from the instance endpoint to the cluster endpoint. Proceed?
   (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Distinguished database-layer recovery from application-layer
   recovery.** A generic assistant sees "failover didn't work" and
   investigates the database. The skill confirms the DB failover
   completed in 13 seconds and shifts focus to the application layer.

2. **Identified the instance endpoint in the connection string.** The
   skill reads the application config and recognises that
   `prod-db-cluster-instance-1.xxxx` is an instance endpoint, not a
   cluster endpoint. After failover, instance-1 is a reader — the
   application is connecting to a read-only instance.

3. **Used DNS probes to prove the mismatch.** The skill checks `dig`
   on both the cluster endpoint (resolves to the new writer) and the
   instance endpoint (resolves to the old writer, now a reader). The
   DNS evidence confirms the application is hitting the wrong IP.

4. **Ruled out connection pool caching.** HikariCP maxLifetime is 30s,
   so the pool IS cycling connections — but all new connections go to
   the instance endpoint (a reader). The issue is the endpoint, not
   the pool. A generic assistant might recommend reducing maxLifetime,
   which would not fix the problem.

5. **Recommended the AWS Advanced JDBC Driver as a permanent fix.**
   The skill suggests adopting the failover-aware driver wrapper to
   eliminate this class of issue for all future failovers — not just
   fixing the current connection string.

## Slash-command invocation

```
/aws:troubleshoot-rds-failover
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why payments-service didn't recover after Aurora failover"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: rds-failover-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the failover recovery:

```bash
# Confirm the cluster endpoint resolves to the writer
dig +short prod-db-cluster.cluster-xxxxxxxxxxxx.us-east-1.rds.amazonaws.com

# Confirm the application is now using the cluster endpoint
aws logs filter-log-events \
  --log-group-name /aws/lambda/payments-service \
  --filter-pattern '"cluster-xxxx"' \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --profile default --output json

# Trigger a test failover (OFF-PEAK ONLY — confirm with operator first)
# aws rds failover-db-cluster \
#   --db-cluster-identifier prod-db-cluster --profile default

# Monitor application error rate after test failover
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=payments-service \
  --start-time $(date -d '-10 minutes' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 60 --statistics Sum --profile default --output json

# Verify RDS failover event was emitted
aws rds describe-events \
  --source-identifier prod-db-cluster --source-type db-cluster \
  --start-time $(date -d '-30 minutes' +%FT%TZ) \
  --profile default --output json
```

Then monitor the application's error rate for 10-15 minutes to confirm
the connection string fix eliminates the post-failover errors.
