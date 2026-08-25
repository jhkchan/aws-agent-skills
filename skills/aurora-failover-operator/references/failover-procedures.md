# Aurora Failover Procedures Reference

Load this reference when planning or executing any Aurora failover operation.
The procedures below are the canonical sequences for each failover archetype,
with pre-checks, command sequence, post-verification, and rollback notes.

## Decision tree — which failover archetype

| Scenario | Use | Why |
|---|---|---|
| Automatic failover (primary health check failed) | **Automatic** (Aurora-initiated) | No CLI needed; Aurora promotes the healthiest replica automatically |
| Planned failover (AZ maintenance, instance rebalance) | **Planned failover** (`failover-db-cluster`) | Promote a specific replica; controlled timing |
| Primary unreachable, replicas available | **Unplanned failover** (`failover-db-cluster` force) | Force promotion of an available reader |
| Return original primary to writer role | **Failback** (`failover-db-cluster`) | Second failover event targeting the original writer |
| Regional disaster (primary region down) | **Global Database failover** (`failover-global-cluster`) | Promote a secondary region cluster |
| Connection pooling to survive failover | **RDS Proxy** | Transparent connection pooling; no drops during failover |

## Planned failover procedure

**When to use:** AZ maintenance, instance rebalance, controlled testing.

**Pre-checks:**
1. `DBClusterStatus: available`.
2. At least 1 reader in `available` status.
3. Target replica (if specified) is in `available` status.
4. `AuroraReplicaLag` on target < 30 seconds.
5. `GlobalClusterIdentifier` is empty (use global failover for Global DB).
6. `ActivityStreamStatus` is `stopped`.
7. RDS Proxy target group `HEALTHY` (if proxy is associated).

**Command sequence:**
```bash
# 1. Capture pre-state
aws rds describe-db-clusters --db-cluster-identifier <cluster> \
  --output json > /tmp/<cluster>-pre-$(date +%s).json

# 2. Execute planned failover (promote a specific replica)
aws rds failover-db-cluster \
  --db-cluster-identifier <cluster> \
  --target-db-instance-identifier <target-replica>

# 3. Wait for failover to complete
aws rds wait db-cluster-available --db-cluster-identifier <cluster>
```

**Post-verification:**
- `describe-db-clusters` shows `DBClusterStatus: available`.
- Target replica is now writer (`IsClusterWriter: true`).
- Old writer is now reader (`IsClusterWriter: false`).
- `mysql -h <writer-endpoint> -e "SELECT @@innodb_read_only"` returns 0.
- `AuroraReplicaLag` on all readers converges to < 100ms within 60s.

**Rollback:** Failback via another `failover-db-cluster` targeting the
original writer. Note: failback is a second failover event (another 60-120s
write outage).

## Unplanned failover procedure

**When to use:** Primary is unreachable (health check failure) and Aurora's
automatic failover did not trigger (or needs to be forced).

**Pre-checks:**
1. Primary instance is confirmed unreachable (writer endpoint health check
   fails for > 30 seconds).
2. At least 1 reader in `available` status.
3. `AuroraReplicaLag` checked — warn if > 30s (data loss risk).

**Command sequence:**
```bash
# Force failover (Aurora will promote the healthiest available reader)
aws rds failover-db-cluster \
  --db-cluster-identifier <cluster>

# If you want to specify the target:
aws rds failover-db-cluster \
  --db-cluster-identifier <cluster> \
  --target-db-instance-identifier <target-replica>

# Wait for completion
aws rds wait db-cluster-available --db-cluster-identifier <cluster>
```

**Post-verification:** Same as planned failover, plus verify that the old
writer (if it comes back) is demoted to reader automatically.

**Common failure modes:**
- No available reader → BLOCKED. Wait for a reader to reach `available` or
  restore from snapshot.
- Reader in `creating` status → BLOCKED. Wait for it to become `available`.

## Failback procedure

**When to use:** Return the original writer to the writer role after a
failover (e.g., AZ maintenance completed, original instance recovered).

**Pre-checks:**
1. Original writer (now reader) is in `available` status.
2. Current writer is in `available` status.
3. `AuroraReplicaLag` on original writer (now reader) < 30 seconds.
4. No critical write operations in progress.

**Command sequence:**
```bash
# Failback: promote the original writer back
aws rds failover-db-cluster \
  --db-cluster-identifier <cluster> \
  --target-db-instance-identifier <original-writer-instance>

# Wait for completion
aws rds wait db-cluster-available --db-cluster-identifier <cluster>
```

**Notes:**
- Failback is a SECOND failover event. It causes another 60-120s write
  outage. Schedule for off-peak.
- Only failback if AZ preference or instance-specific config matters.
  Otherwise, leave the new writer in place.

## Aurora Global Database failover procedure

**When to use:** Regional disaster (primary region down) or planned
regional migration.

### Managed planned failover (`failover-global-cluster`)

**Pre-checks:**
1. Global cluster has at least 1 secondary region cluster in `available`.
2. Cross-region replication lag (`AuroraGlobalDBReplicationLag`) < 5s.
3. Primary region cluster is `available`.

```bash
# 1. Capture pre-state
aws rds describe-global-clusters \
  --global-cluster-identifier <global-cluster-id> \
  --output json > /tmp/<global-id>-pre-$(date +%s).json

# 2. Execute managed global failover
aws rds failover-global-cluster \
  --global-cluster-identifier <global-cluster-id> \
  --target-db-cluster-identifier arn:aws:rds:<secondary-region>:<acct>:cluster:<secondary-cluster>

# 3. Wait for the secondary cluster to become the new primary
aws rds wait db-cluster-available \
  --db-cluster-identifier <secondary-cluster> --region <secondary-region>

# 4. Verify global cluster topology
aws rds describe-global-clusters \
  --global-cluster-identifier <global-cluster-id>
```

### Unplanned global failover (detach + promote)

**When to use:** Primary region is truly down (confirmed); managed
failover is not available or too slow.

```bash
# 1. Promote the secondary cluster to a standalone primary
aws rds promote-global-secondary-to-primary \
  --global-cluster-identifier <global-cluster-id> \
  --db-cluster-identifier arn:aws:rds:<secondary-region>:<acct>:cluster:<secondary-cluster> \
  --region <secondary-region>

# OR: detach and promote manually (older approach)
aws rds remove-from-global-cluster \
  --db-cluster-identifier arn:aws:rds:<secondary-region>:<acct>:cluster:<secondary-cluster> \
  --global-cluster-identifier <global-cluster-id> \
  --region <secondary-region>

# The detached cluster becomes a standalone primary automatically

# 2. Update application connection strings to the new region's endpoint
# 3. When the original region recovers, re-add it as a secondary:
aws rds create-global-cluster \
  --global-cluster-identifier <global-cluster-id> \
  --source-db-cluster-identifier arn:aws:rds:<new-primary-region>:<acct>:cluster:<new-primary> \
  --region <original-primary-region>
```

**Split-brain warning:** If the primary region is NOT actually down, both
regions have active writers writing to divergent storage volumes. This is
unrecoverable without manual data reconciliation. Always confirm the
primary is truly unreachable before unplanned global failover.

## RDS Proxy configuration for failover resilience

**When to configure:** Before a failover, to ensure application connections
survive without drops.

```bash
# 1. Create an RDS Proxy targeting the Aurora cluster
aws rds create-db-proxy \
  --proxy-name <proxy-name> \
  --engine-family MYSQL \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"arn:aws:secretsmanager:<region>:<acct>:secret:<secret>","IAMAuth":"DISABLED"}]' \
  --role-arn arn:aws:iam::<acct>:role/<proxy-role> \
  --vpc-subnet-ids <subnet-1> <subnet-2> \
  --vpc-security-group-ids <sg-id>

# 2. Register the Aurora cluster as the proxy target
aws rds register-db-proxy-targets \
  --proxy-name <proxy-name> \
  --db-cluster-identifier <cluster-id>

# 3. Verify target health
aws rds describe-db-proxy-targets --proxy-name <proxy-name>
```

**Key configuration points:**
- The proxy target must be the CLUSTER (not individual instances) for
  failover-aware routing.
- Application connection strings must use the PROXY ENDPOINT, not the
  cluster endpoint.
- The proxy handles connection pooling: application connections stay open
  during failover; the proxy reconnects to the new writer internally.

## Endpoint behavior during failover

| Endpoint type | Before failover | After failover | Action needed |
|---|---|---|---|
| Writer endpoint (`cluster-*`) | Points to primary | Points to new primary (DNS CNAME follows) | Flush DNS cache |
| Reader endpoint (`cluster-ro-*`) | Load-balances readers | Load-balances readers (now includes old writer) | None |
| Custom endpoint | Points to specified instances | Unchanged (instances don't change) | None |
| RDS Proxy endpoint | Pools to cluster | Pools to new writer transparently | None (proxy handles it) |
| Global endpoint | N/A (per-region endpoints) | N/A (each region has own endpoint) | Update app connection strings for regional failover |

## DNS cache flush commands

| Runtime / OS | Command |
|---|---|
| JVM (Java) | Set `networkaddress.cache.ttl=0` in `java.security` or restart JVM |
| Node.js | Restart process (Node caches DNS per-process) |
| Python | `socket.clearcache()` or restart (Python 3.9+ clears on TTL) |
| Go | Restart process (Go caches DNS at resolver level) |
| Linux (systemd-resolved) | `systemd-resolve --flush-caches` |
| Linux (nscd) | `service nscd restart` |
| macOS | `dscacheutil -flushcache && sudo killall -HUP mDNSResponder` |
| AWS SDK (any language) | Restart the SDK client (connection pool holds stale IPs) |

## Failover timing benchmarks (2026, us-east-1)

| Operation | Typical duration |
|---|---|
| Automatic failover (detection) | ~30 seconds |
| Automatic failover (promotion) | ~30-60 seconds |
| Automatic failover (total RTO) | ~30-90 seconds |
| Planned failover (`failover-db-cluster`) | 30-120 seconds |
| Failback | 30-120 seconds (same as planned failover) |
| Global Database managed failover | 1-5 minutes |
| Global Database unplanned failover | 30-60 seconds (detach + promote) |
| RDS Proxy reconnection | 5-10 seconds |
| Writer endpoint DNS update (RDS layer) | 30-60 seconds |
| Replica lag convergence post-failover | < 60 seconds (typically < 100ms within 30s) |

## Common failover pitfalls

- **Forgot to flush DNS cache.** The writer endpoint DNS updates at the
  RDS layer in 30-60 seconds, but application-layer DNS caches (JVM, OS,
  framework) may hold the old IP for minutes. Applications continue writing
  to the old writer (now a reader) and get read-only errors.

- **Application connects to cluster endpoint instead of proxy endpoint.**
  RDS Proxy only helps if the application uses the proxy endpoint. Direct
  cluster-endpoint connections experience drops during failover.

- **Failback treated as an "undo."** Failback is a second failover event
  with another write outage. Operators who expect instant rollback are
  surprised by the second outage.

- **No healthy reader available for failover.** Single-instance Aurora
  clusters (no replicas) cannot failover. Always maintain at least 1
  reader in a different AZ for HA.

- **Global DB unplanned failover without confirming primary is down.**
  If the primary region is still alive, both regions have writers writing
  to divergent storage volumes (split-brain). This is unrecoverable
  without manual reconciliation.

- **Skipped AuroraReplicaLag check before planned failover.** High lag
  on the target replica means the promoted writer is missing recent
  writes. Data loss.

- **Used reader endpoint for writes.** The reader endpoint load-balances
  across readers (read-only). Write operations must target the writer
  endpoint.

## Failover timing baselines (2026) — narrative (moved from SKILL.md Quick reference)

**Failover timing baselines (2026):**

- Automatic failover detection: ~30 seconds (Aurora health check interval).
- Replica promotion: ~60 seconds (Aurora writer promotion sequence).
- Total automatic failover RTO: ~30-90 seconds (detection + promotion +
  DNS propagation).
- Planned failover via `failover-db-cluster`: 30-120 seconds.
- Aurora Global Database managed failover: 1-5 minutes (promotes a
  secondary region cluster).
- RDS Proxy connection survival: connections pool transparently through
  failover — no drops if the proxy is configured correctly.
- DNS cache propagation: writer endpoint updates within 30-60 seconds
  at the RDS layer; application-layer DNS caches may take longer.
