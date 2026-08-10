# Example usage: aurora-failover-operator

A walkthrough showing the skill planning a planned Aurora failover to
promote a specific replica, demonstrating the pre-check gate, the CONFIRM
gate, endpoint behavior analysis, and the DNS cache flush step.

## Input (user prompt)

> We need to failover our Aurora production cluster for AZ maintenance.
> Promote prod-orders-node-2 (us-east-1b) as the new writer. We have an
> RDS Proxy in front of the cluster.

```text
Cluster: prod-orders-cluster
Region: us-east-1
Operation: planned-failover
Target replica to promote: prod-orders-node-2

Cluster configuration:
  - Engine: aurora-mysql
  - DBClusterStatus: available
  - MultiAZ: true
  - Writer: prod-orders-node-1 (us-east-1a)
  - Readers: prod-orders-node-2 (us-east-1b), prod-orders-node-3 (us-east-1c)
  - GlobalClusterIdentifier: (empty)
  - ActivityStreamStatus: stopped
  - StorageEncrypted: true

Instance details:
  - prod-orders-node-2: status=available, AuroraReplicaLag=8ms

RDS Proxy: prod-orders-proxy
  - Target group health: HEALTHY
  - Application connects via proxy endpoint
```

## Skill output

```text
OPERATION: planned
VERDICT: READY
TARGET: prod-orders-cluster (writer: node-1 → target: node-2)
PRE_CHECKS:
  - [PASS] prod-orders-cluster DBClusterStatus is available
  - [PASS] Cluster has 2 readers (node-2, node-3)
  - [PASS] Target replica node-2 is available
  - [PASS] AuroraReplicaLag on node-2 is 8ms (< 30s threshold)
  - [PASS] node-2 is in us-east-1b (different AZ from current writer)
  - [PASS] GlobalClusterIdentifier is empty (single-region cluster)
  - [PASS] ActivityStreamStatus is stopped
  - [PASS] RDS Proxy prod-orders-proxy target group is HEALTHY
STEPS:
  1. CONFIRM: About to failover-db-cluster prod-orders-cluster in account
     111111111111 region us-east-1. This will promote node-2 to writer
     and demote node-1 to reader. Write operations will be interrupted
     for ~60-120 seconds. Proceed? (yes/no)
  2. aws rds failover-db-cluster \
       --db-cluster-identifier prod-orders-cluster \
       --target-db-instance-identifier prod-orders-node-2
  3. aws rds wait db-cluster-available \
       --db-cluster-identifier prod-orders-cluster
POST_VERIFY:
  - (pending execution)
WRITER_ENDPOINT: prod-orders-cluster.cluster-abc123.us-east-1.rds.amazonaws.com
  (unchanged — DNS CNAME follows the new writer automatically)
READER_ENDPOINT: prod-orders-cluster.cluster-ro-abc123.us-east-1.rds.amazonaws.com
  (unchanged — now includes node-1 as a reader)
CONNECTION_NOTES:
  - Writer endpoint is a DNS CNAME that follows the new primary. No
    connection-string change needed for the writer endpoint.
  - Flush application DNS caches: JVM set networkaddress.cache.ttl=0 or
    restart; OS run systemd-resolve --flush-caches.
  - RDS Proxy connections survive the failover without drops. Verify
    application connects to the proxy endpoint, not the cluster endpoint.
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate.** A generic assistant jumps straight to the CLI. The
   skill verifies 8 pre-checks (cluster status, healthy replica, replica
   lag, AZ spread, Global DB membership, activity stream status, RDS Proxy
   health) before recommending execution.

2. **RDS Proxy connection survival.** The skill explicitly verifies the
   RDS Proxy target group is HEALTHY and confirms the application connects
   via the proxy endpoint. A generic assistant doesn't distinguish between
   proxy and cluster endpoints.

3. **DNS cache flush.** The skill surfaces the JVM DNS cache flush step —
   the most common post-failover failure point. A generic assistant says
   "the endpoint updates automatically" without addressing application-
   layer DNS caches that hold the old IP.

4. **Endpoint behavior analysis.** The skill explains that the writer
   endpoint (CNAME) follows the new primary transparently, while the
   reader endpoint now includes the old writer as a reader. A generic
   assistant doesn't explain endpoint behavior.

5. **Failback awareness.** The skill notes that failback (if AZ
   preference matters) is another failover event with another write
   outage. A generic assistant doesn't mention the failback asymmetry.

## Slash-command invocation

```
/aws:operate-aurora-failover
```

Or via the orchestrator:

```
/aws:pipeline
You: "plan a failover for our Aurora production cluster"
```

The orchestrator emits
`[Phase: Operate | Skills routed: aurora-failover-operator]` and hands
off to this skill for the failover block.

## Live-account follow-up (optional, requires AWS CLI)

After the failover completes, verify the cluster state:

```bash
# Confirm cluster is available
aws rds describe-db-clusters \
  --db-cluster-identifier prod-orders-cluster \
  --query 'DBClusters[0].{Status:Status, Writer:DBClusterMembers[?IsClusterWriter==`true`].DBInstanceIdentifier}' \
  --output json

# Verify writer endpoint resolves to the new writer
aws rds describe-db-clusters \
  --db-cluster-identifier prod-orders-cluster \
  --query 'DBClusters[0].Endpoint' --output text

# Test write connectivity
mysql -h prod-orders-cluster.cluster-abc123.us-east-1.rds.amazonaws.com \
  -u admin -p -e "SELECT @@innodb_read_only"
# Should return 0 (read-write)

# Check replica lag convergence
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBClusterIdentifier,Value=prod-orders-cluster \
  --start-time $(date -d '-15 minutes' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --period 60 --statistics Average,Maximum --output json

# Verify RDS Proxy targets
aws rds describe-db-proxy-targets \
  --proxy-name prod-orders-proxy
```

If write errors persist beyond 60 seconds, flush application DNS caches
(JVM: restart or set `networkaddress.cache.ttl=0`; OS:
`systemd-resolve --flush-caches`).
