# Aurora Failover Operator — Worked Examples

Secondary worked examples moved from SKILL.md. The primary worked example
(planned failover, READY) remains in SKILL.md under § Output format.


## Worked example — unplanned failover BLOCKED (no healthy replica)

```text
OPERATION: unplanned
VERDICT: BLOCKED
TARGET: prod-orders-cluster
PRE_CHECKS:
  - [PASS] prod-orders-cluster DBClusterStatus is available (cluster is up)
  - [FAIL] No healthy reader available — prod-orders-cluster has 1 reader
    (node-2) but it is in status 'creating' (recently launched, not yet
    promoted-capable). Cannot failover without an available reader.
  - [FAIL] Writer node-1 is unreachable (health check failed) AND no
    available reader to promote — the cluster cannot elect a new writer.
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
WRITER_ENDPOINT: prod-orders-cluster.cluster-abc123.us-east-1.rds.amazonaws.com
  (writer endpoint still points to node-1 which is unreachable)
CONNECTION_NOTES:
  - BLOCKED: no available failover target. Remediation:
    1. Wait for node-2 to reach 'available' status:
       aws rds wait db-instance-available \
         --db-instance-identifier prod-orders-cluster-node-2
    2. Then retry failover:
       aws rds failover-db-cluster \
         --db-cluster-identifier prod-orders-cluster
  - If node-1 is permanently lost and node-2 cannot reach available,
    restore from the most recent snapshot as a last resort:
    aws rds restore-db-cluster-from-snapshot \
      --db-cluster-identifier prod-orders-cluster-recovery \
      --snapshot-identifier <latest-snapshot>
```


## Worked example — COMPLETED (automatic failover verified)

```text
OPERATION: automatic
VERDICT: COMPLETED
TARGET: prod-checkout-cluster
PRE_CHECKS:
  - [PASS] (automatic failover — pre-checks bypassed, Aurora initiated
    failover due to writer health check failure)
STEPS:
  1. (Automatic failover triggered by Aurora at 2026-08-07T10:02:15Z)
  2. Aurora promoted node-2 (us-east-1b) to writer at 2026-08-07T10:03:12Z
  3. Failover duration: 57 seconds (detection + promotion)
POST_VERIFY:
  - [PASS] DBClusterStatus is available
  - [PASS] node-2 is the writer (IsClusterWriter: true)
  - [PASS] node-1 is now a reader (IsClusterWriter: false, AuroraReplicaLag: 12ms)
  - [PASS] Writer endpoint resolves to node-2's endpoint
  - [PASS] mysql -h <writer-endpoint> SELECT @@innodb_read_only returns 0 (read-write)
  - [PASS] Reader endpoint load-balances across node-1 and node-3
  - [PASS] RDS Proxy target group HEALTHY on new writer
  - [WARN] JVM DNS cache may hold old writer IP for up to 60s (default TTL).
    Flush if write errors persist.
WRITER_ENDPOINT: prod-checkout-cluster.cluster-def456.us-east-1.rds.amazonaws.com
  (unchanged — DNS CNAME now resolves to node-2)
READER_ENDPOINT: prod-checkout-cluster.cluster-ro-def456.us-east-1.rds.amazonaws.com
  (unchanged — now includes node-1)
CONNECTION_NOTES:
  - Automatic failover completed successfully (RTO: 57s).
  - RDS Proxy connections survived the failover with no drops.
  - Flush application DNS caches if write errors persist beyond 60 seconds.
  - Consider failing back to node-1 during the next maintenance window if
    AZ preference matters (node-1 is in us-east-1a, node-2 is in us-east-1b).
```


## Worked example — Aurora Global Database failover (READY)

```text
OPERATION: global
VERDICT: READY
TARGET: prod-global-cluster (primary: us-east-1, secondary: eu-west-1)
PRE_CHECKS:
  - [PASS] Global cluster has 2 region members (us-east-1, eu-west-1)
  - [PASS] Secondary cluster in eu-west-1 is available
  - [PASS] AuroraGlobalDBReplicationLag is 0.3s (< 5s threshold)
  - [PASS] Primary cluster in us-east-1 is available (planned failover)
STEPS:
  1. CONFIRM: About to failover-global-cluster prod-global-cluster in
     account 111111111111. This will promote the eu-west-1 cluster to
     primary and demote us-east-1 to secondary. Cross-region write
     redirection will take 1-5 minutes. Proceed? (yes/no)
  2. aws rds failover-global-cluster \
       --global-cluster-identifier prod-global-cluster \
       --target-db-cluster-identifier arn:aws:rds:eu-west-1:111111111111:cluster:prod-global-cluster-eu
  3. aws rds wait db-cluster-available \
       --db-cluster-identifier prod-global-cluster-eu --region eu-west-1
POST_VERIFY: (pending execution)
WRITER_ENDPOINT: prod-global-cluster-eu.cluster-xyz789.eu-west-1.rds.amazonaws.com
  (NEW regional endpoint — applications must update connection strings to
  the eu-west-1 cluster endpoint)
READER_ENDPOINT: prod-global-cluster-eu.cluster-ro-xyz789.eu-west-1.rds.amazonaws.com
  (new regional reader endpoint)
CONNECTION_NOTES:
  - Global failover changes the primary REGION. Application connection
    strings must be updated to the eu-west-1 cluster endpoint.
  - The us-east-1 cluster becomes a read-only secondary.
  - Aurora Global Database does NOT provide a global writer endpoint —
    each region has its own cluster endpoint. Use Route 53 health checks
    + weighted routing for automatic regional connection-string failover.
  - Cross-region replication will resume from eu-west-1 to us-east-1 once
    the failover completes.
```
