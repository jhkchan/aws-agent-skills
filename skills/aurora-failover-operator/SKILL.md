---
name: aurora-failover-operator
description: Operates Aurora cluster failover and recovery workflows safely — automatic Multi-AZ failover (30s detection, 60s promotion), planned failover to promote a specific replica, unplanned failover when the primary is unreachable, failback to the original primary, Aurora Global Database managed failover, RDS Proxy connection pooling that survives failover without dropping connections, writer/reader endpoint behavior, application connection-string cutover, and full post-failover verification (cluster status, instance roles, replica lag). Runs deterministic pre-checks (healthy replica count, Global DB membership, writer endpoint reachability, replication health), executes behind a CONFIRM gate, and emits READY, BLOCKED, or COMPLETED per operation with the exact CLI sequence, endpoint behavior, and verification commands. Use for Aurora failover planning, promoting a replica, failing back, or verifying post-failover health.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws rds describe-db-clusters, aws rds failover-db-cluster, aws rds describe-global-clusters, aws rds failover-global-cluster, aws rds describe-db-instances, aws rds describe-db-proxy-target-groups, and aws rds wait db-cluster-available (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Planning or executing an Aurora cluster failover (automatic, planned, or unplanned), failing back to the original primary, promoting a specific replica, managing an Aurora Global Database failover, configuring RDS Proxy to survive failover, verifying post-failover cluster health, or recovering from a primary outage.
  when_not_to_use: RDS backup and restore operations (use rds-backup-restore-operator), RDS instance rightsizing or cost optimization (use the optimize skills), RDS security audits (use the audit skills), or non-Aurora RDS failover (standard RDS Multi-AZ failover is automatic only — no manual failover CLI). This skill is Aurora-specific (cluster-level failover, Global Database, writer/reader endpoints).
  activation_triggers: Aurora failover, promote Aurora replica, planned failover Aurora, unplanned failover Aurora, failback Aurora cluster, Aurora Global Database failover, RDS Proxy failover, Aurora writer endpoint, Aurora reader endpoint, Aurora primary unreachable, Aurora Multi-AZ failover, verify Aurora failover, Aurora split-brain, Aurora DNS cache failover, Aurora connection string update
  invocation_schema: 'Input: either (a) an Aurora cluster configuration with the intended failover operation (automatic, planned, unplanned, failback, global), OR (b) a cluster-id + operation for live-account execution. Output: a deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  invocation_example: "# Minimal valid input (offline plan classification):\nCluster: prod-orders-cluster\nRegion: us-east-1\nOperation: planned-failover\nTarget replica to promote: prod-orders-cluster-node-2\nCluster configuration:\n  - Engine: aurora-mysql\n  - DBClusterStatus: available\n  - MultiAZ: true\n  - Writer: prod-orders-cluster-node-1 (us-east-1a)\n  - Readers: prod-orders-cluster-node-2 (us-east-1b), prod-orders-cluster-node-3 (us-east-1c)\n  - GlobalClusterMember: false\n  - RDSProxy: prod-orders-proxy (connected)\nEmit the standard VERDICT block."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Aurora, failover, Multi-AZ, planned failover, unplanned failover, failback, RDS Proxy, Aurora Global Database, writer endpoint, reader endpoint, connection pooling, replica promotion, split-brain, DNS cache, replica lag, high availability, disaster recovery
  tags: aurora, databases, failover, high-availability, disaster-recovery, rds-proxy, multi-az
---

# Aurora Failover Operator

## What this skill does

Executes Aurora cluster failover and recovery operations correctly and
safely. Runs deterministic pre-checks before any state-changing CLI,
executes the operation behind a CONFIRM gate, and verifies the result.
Every failover promotes a new writer — the writer endpoint follows the
new primary transparently, but application DNS caches and connection
pools may need attention.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority order | Before any operation |
| **§ STRICT output contract** | Mandatory output block format | Before emitting any response |
| **§ Mindset** | Writer endpoint behavior, RDS Proxy, DNS cache, the failback asymmetry | Understanding the failover model |
| **§ Pre-flight** | Cluster metadata gate — status, replica health, Global DB, RDS Proxy | Before executing any CLI |
| **§ Process** | Per-operation planning: automatic, planned, unplanned, failback, global | When choosing which operation to run |
| **§ Output format** | Worked examples (READY, BLOCKED, COMPLETED) | Formatting the response |
| **§ Expert heuristic** | Non-obvious Aurora failover behaviours from operational experience | Review before complex decisions |
| **§ NEVER** | Anti-patterns that cause split-brain, connection loss, or data divergence | Review before risky operations |
| **§ Pre-flight safety** | Additional checks before any failover CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (no healthy replica, Global DB writer without detach, cluster in modifying state, RDS Proxy target group unhealthy) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Failover finished and post-verification passed | Emit new writer info, verification results, connection notes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Cluster status** — must be `available`. `modifying`, `upgrading`,
   `creating`, `deleting`, `failing-over` → BLOCKED.
2. **Healthy replica count** — at least 1 reader in `available` status for
   failover target. No healthy replica → BLOCKED.
3. **Replica lag** — `AuroraReplicaLag` < 30 seconds on the target
   replica. High lag → BLOCKED or warn (data loss risk).
4. **Global Database membership** — if the cluster is a Global DB writer,
   failover requires managed global failover (not standalone
   `failover-db-cluster`).
5. **RDS Proxy health** — if a proxy is associated, verify target group
   health. Unhealthy proxy targets cause connection failures during
   failover.

Timing baselines moved to [references/failover-procedures.md](references/failover-procedures.md)
(section: Failover timing baselines) — load when estimating RTO.

## STRICT output contract

Every failover response MUST emit this block per target cluster. No prose
before or after the block; the block is the entire actionable output.

```text
OPERATION: <automatic | planned | unplanned | failback | global>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <cluster-id, writer-instance, target-replica>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
WRITER_ENDPOINT: <writer endpoint (unchanged if transparent; new if regional)>
READER_ENDPOINT: <reader endpoint behavior>
CONNECTION_NOTES: <DNS cache, RDS Proxy, connection string updates>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <operation> on <cluster> in <region>.
  Proceed? (yes/no)"
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Mindset

**One-line takeaway:** Aurora failover promotes a reader to writer; the
writer endpoint follows the new primary transparently. The original writer
becomes a reader. RDS Proxy connections survive the failover without drops.
Application-layer DNS caches are the most common failure point.

Driven by four Aurora realities:

- **The writer endpoint is a DNS CNAME that follows the primary.** Aurora
  exposes a cluster writer endpoint (`<cluster>.cluster-<random>.<region>.rds.amazonaws.com`)
  that always points to the current writer. After failover, this endpoint
  updates to the new writer automatically. Applications connecting via the
  writer endpoint do not need a connection-string change — but DNS caches
  at the application level (JVM DNS cache, OS resolver cache, application
  framework HTTP client pools) may hold the old IP for their TTL duration.

- **RDS Proxy survives failover transparently.** RDS Proxy maintains a
  connection pool to the Aurora cluster. During failover, the proxy
  reconnects to the new writer without dropping application connections.
  Applications behind an RDS Proxy experience a brief stall (seconds) but
  no connection errors. This is the single biggest reason to use RDS Proxy
  with Aurora.

- **Failback is not symmetric with failover.** After a failover, the
  original writer becomes a reader. Failing back (promoting the original
  writer again) requires another `failover-db-cluster` call — it is a
  second failover event, not a "undo." Each failover causes a brief write
  outage. Avoid unnecessary failback cycles in production.

- **Aurora Global Database failover is a different mechanism.** Aurora
  Global Database replicates asynchronously across regions. A regional
  failover uses `failover-global-cluster` (managed planned) or
  `detach-from-global-cluster` + promote (unplanned). These are NOT the
  same as a single-region `failover-db-cluster`. The replication lag
  between regions (typically < 1 second, but can spike) determines
  potential data loss during an unplanned global failover.

## Pre-flight: cluster metadata gate

Run before classification. Misclassifying these produces wrong plans.

Live-account pre-flight commands moved to [references/diagnostic-commands.md](references/diagnostic-commands.md)
— load that file before executing against a live account.

**Malformed input:** if the input is invalid or missing required fields,
emit `VERDICT: BLOCKED` with `REASON: Cluster/operation configuration is
not valid or is missing required fields — cannot plan.`

| Cluster attribute | Effect on failover |
|---|---|
| `DBClusterStatus: available` | Pre-check passes for failover operations. |
| `DBClusterStatus: modifying, upgrading, creating, deleting` | BLOCKED — wait for `available`. |
| `DBClusterStatus: failing-over` | BLOCKED — a failover is already in progress. |
| `DBClusterStatus: backing-up` | Can proceed for read operations; BLOCKED for failover. |
| `MultiAZ: true` with >= 1 healthy reader | Failover target available. |
| `MultiAZ: false` or no readers | BLOCKED — no failover target. Add a replica first. |
| `GlobalClusterIdentifier` set (Global DB writer) | Use `failover-global-cluster`, NOT standalone `failover-db-cluster`. |
| `GlobalClusterIdentifier` set (Global DB reader) | Can promote via global failover or detach + promote. |
| `ActivityStreamStatus: started` | BLOCKED — stop the activity stream before failover. |
| RDS Proxy associated with healthy targets | Connection pooling active; connections survive failover. |
| RDS Proxy with unhealthy targets | BLOCKED — fix proxy target health before failover. |
| `AuroraReplicaLag > 30s` on target replica | WARN — data loss risk if lag is high during promotion. |
| `DeletionProtection: true` | Does not block failover (blocks deletion only). |
| `StorageEncrypted: true` | Does not affect failover (KMS key follows the cluster). |

## Process — operation planning (apply in order)

### Step 0: Expert heuristic — non-obvious Aurora failover behaviours

Deep dive moved to [references/advanced-patterns.md](references/advanced-patterns.md)
(Step 0: non-obvious Aurora failover behaviours) — load before complex decisions.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is BLOCKED
with the failed checks enumerated in PRE_CHECKS. Do NOT execute.

**For ALL failover operations:**
1. `DBClusterStatus` is `available` (not `modifying`, `upgrading`,
   `failing-over`, `creating`, `deleting`).
2. The cluster has at least 1 reader in `available` status.
3. The target replica (if specified) is in `available` status and is a
   member of the cluster.
4. No existing failover is in progress.
5. IAM role for the operator holds `rds:FailoverDBCluster` (or
   `rds:FailoverGlobalCluster` for global).

**For planned failover (`failover-db-cluster`):**
6. `AuroraReplicaLag` on the target replica is < 30 seconds (data loss
   risk if higher).
7. The target replica is in a different AZ from the current writer (for
   AZ failover scenarios).
8. `ActivityStreamStatus` is `stopped` (activity streams block failover).

**For unplanned failover (force failover):**
6. The primary instance is confirmed unreachable (writer endpoint does
   not respond to health checks).
7. At least 1 reader is in `available` status (even if the primary is
   down).
8. `AuroraReplicaLag` checked — warn if > 30s (potential data loss).

**For failback (`failover-db-cluster` targeting the original writer):**
6. The original writer (now a reader) is in `available` status.
7. The current writer (promoted during the original failover) is in
   `available` status.
8. `AuroraReplicaLag` on the original writer (now reader) is < 30 seconds.
9. No writes in progress that would be interrupted by the failback cycle.

**For Aurora Global Database failover (`failover-global-cluster`):**
6. The global cluster has at least 1 secondary region cluster in
   `available` status.
7. Cross-region replication lag is < 5 seconds (check via
   `aws rds describe-global-clusters` — lag is not directly exposed; use
   CloudWatch `AuroraGlobalDBReplicationLag`).
8. The primary region cluster is `available` for planned failover.
9. For unplanned: the primary region is confirmed unreachable.

**For RDS Proxy verification (if proxy is associated):**
6. `describe-db-proxy-target-groups` shows target health `HEALTHY`.
7. The proxy's target group includes the cluster (not individual
   instances) — proxy-managed failover only works when targeting the
   cluster.
8. Application connection strings use the proxy endpoint, not the cluster
   endpoint.

### Step 2: READY — emit failover plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated.
- The expected duration (planned failover 30-120s, global failover 1-5min).
- The expected endpoint behavior (writer endpoint follows new primary;
  reader endpoint unchanged).
- The DNS cache flush step.
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI, emit:
  `CONFIRM: About to <operation> on <cluster> in account <account> region
  <region>. This will promote <replica> to writer and demote <current-writer>
  to reader. Write operations will be briefly interrupted (~60-120s).
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state: `aws rds describe-db-clusters --db-cluster-identifier
  <id> --output json > /tmp/<id>-pre-$(date +%s).json`.
- Execute the CLI.
- Wait for completion: `aws rds wait db-cluster-available
  --db-cluster-identifier <id>`.

### Step 4: Post-verification — COMPLETED

After the failover finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-db-clusters --db-cluster-identifier <id>` — confirm
   `DBClusterStatus: available`.
2. Verify the writer role: `DBClusterMembers[].IsClusterWriter` — exactly
   one member has `IsClusterWriter: true`, and it is the target replica.
3. Verify the old writer is now a reader: it should have
   `IsClusterWriter: false`.
4. Test write connectivity: `mysql -h <writer-endpoint> -e "SELECT 1"`
   or `SELECT @@innodb_read_only` (should return 0 = read-write).
5. Check `AuroraReplicaLag` on all readers — should converge to < 100ms
   within 60 seconds.
6. Verify the reader endpoint load-balances across readers including the
   old writer.
7. Verify RDS Proxy (if associated) — `describe-db-proxy-target-groups`
   shows `HEALTHY` targets on the new writer.
8. Flush application DNS caches (JVM: set `networkaddress.cache.ttl=0`
   or restart; Node.js: restart; OS: `systemd-resolve --flush-caches`).

If ANY verification fails, emit `VERDICT: ERROR` with failure details —
do not claim COMPLETED.

## Output format

See § STRICT output contract for the mandatory block. Worked examples below.

### Worked example — planned failover (READY)

```text
OPERATION: planned
VERDICT: READY
TARGET: prod-orders-cluster (writer: node-1 → target: node-2)
PRE_CHECKS:
  - [PASS] prod-orders-cluster DBClusterStatus is available
  - [PASS] prod-orders-cluster has 2 readers (node-2, node-3)
  - [PASS] Target replica node-2 is available
  - [PASS] AuroraReplicaLag on node-2 is 8ms (< 30s threshold)
  - [PASS] node-2 is in us-east-1b (different AZ from current writer node-1 in us-east-1a)
  - [PASS] GlobalClusterIdentifier is empty (single-region cluster)
  - [PASS] ActivityStreamStatus is stopped
  - [PASS] RDS Proxy prod-orders-proxy target group is HEALTHY
STEPS:
  1. CONFIRM: About to failover-db-cluster prod-orders-cluster in account
     111111111111 region us-east-1. This will promote node-2 to writer and
     demote node-1 to reader. Write operations will be interrupted for
     ~60-120 seconds. Proceed? (yes/no)
  2. aws rds failover-db-cluster \
       --db-cluster-identifier prod-orders-cluster \
       --target-db-instance-identifier prod-orders-cluster-node-2
  3. aws rds wait db-cluster-available \
       --db-cluster-identifier prod-orders-cluster
POST_VERIFY: (pending execution)
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

### Worked example — unplanned failover BLOCKED (no healthy replica)

Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when formatting a BLOCKED unplanned-failover response.

### Worked example — COMPLETED (automatic failover verified)

Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when formatting a COMPLETED post-failover verification response.

### Worked example — Aurora Global Database failover (READY)

Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when formatting a global (cross-region) failover response.

## Expert heuristic — non-obvious Aurora failover behaviours (consolidated)

| Heuristic | Impact on plan |
|---|---|
| Writer endpoint is a DNS CNAME following the primary | No connection-string change for writer endpoint; but flush DNS caches. |
| RDS Proxy survives failover without drops | Verify app connects via proxy endpoint (not cluster endpoint) before claiming connection survival. |
| Failback is a second failover, not an undo | Each cycle causes a write outage. Minimize unnecessary failback. |
| `failover-db-cluster --target-db-instance-identifier` chooses the promoted replica | Specify the target for AZ-controlled planned failovers. |
| Aurora replica lag determines data loss risk | Check `AuroraReplicaLag` before planned failover; warn on unplanned. |
| Global DB replication is asynchronous (cross-region) | Unplanned global failover has RPO = replication lag. Use managed `failover-global-cluster`. |
| Split-brain risk exists only with Global DB unplanned failover | Single-region Aurora uses shared storage — atomic. Global DB detach+promote can cause split-brain if the primary is still alive. |
| Reader endpoint does NOT change during failover | Reader apps are unaffected; the old writer joins the reader pool. |
| `failover-db-cluster` returns immediately; promotion takes 30-120s | Always use `aws rds wait db-cluster-available` after the CLI. |
| Cross-AZ failover has no data transfer charge | Aurora's shared storage spans AZs transparently. |
| JVM DNS cache default TTL is 60s (or infinite) | Flush DNS cache post-failover to avoid stale writer connections. |
| Aurora Serverless v2 failover is identical to provisioned | Same CLI, same pre-checks, capacity auto-adjusts. |
| Global DB has no global writer endpoint | Each region has its own cluster endpoint; use Route 53 for automatic regional failover. |

## Anti-Patterns — NEVER

- NEVER execute `failover-db-cluster` without verifying at least 1 healthy
  reader in `available` status. A failover with no available reader leaves
  the cluster without a writable primary.

- NEVER execute `failover-db-cluster` on a cluster in `modifying`,
  `upgrading`, or `failing-over` state. Wait for `available` first. A
  concurrent state change causes undefined behavior.

- NEVER use standalone `failover-db-cluster` on a Global Database writer.
  Global DB clusters require `failover-global-cluster` for coordinated
  cross-region failover. Standalone failover on a global writer can
  desynchronize the global cluster.

- NEVER perform an unplanned Global Database failover (detach + promote)
  without confirming the primary region is truly unreachable. A false-
  positive outage detection causes split-brain — both regions have active
  writers writing to divergent storage volumes. This is unrecoverable
  without manual data reconciliation.

- NEVER claim "connections survive failover" without verifying the
  application connects through the RDS Proxy endpoint, not the cluster
  endpoint. The proxy endpoint is separate; direct cluster-endpoint
  connections do NOT benefit from proxy pooling.

- NEVER skip the DNS cache flush step. After failover, the writer endpoint
  DNS updates in 30-60 seconds at the RDS layer, but the JVM, OS resolver,
  and application framework caches may hold the old IP for their TTL
  duration (JVM default: 60s; some configs: infinite). Stale DNS causes
  write operations to hit the old writer (now a reader) and fail with
  "read-only" errors.

- NEVER failback immediately after a failover without a reason. Each
  failback is another failover event with a 30-120s write outage. Only
  failback if the AZ preference or instance-specific configuration matters.
  Otherwise, leave the new writer in place.

- NEVER assume `AuroraReplicaLag` is always negligible. Under heavy write
  load, lag can spike to seconds or minutes. Always check lag before a
  planned failover. High lag during unplanned failover means data loss.

- NEVER use the reader endpoint for write operations. The reader endpoint
  (`cluster-ro-*`) load-balances across readers, which are read-only.
  Write operations must target the writer endpoint (`cluster-*`). Using
  the reader endpoint for writes produces "read-only" errors.

- NEVER skip post-failover verification. A cluster in `available` status
  may still have:
  - The wrong instance as writer (failover targeted the wrong replica).
  - Stale reader lag (replicas not yet caught up).
  - RDS Proxy targets still pointing to the old writer (takes 10-30s
    to update).
  Always run all post-verification checks before claiming COMPLETED.

- NEVER initiate a failover during peak write traffic without surfacing
  the write outage impact. Planned failover causes 60-120 seconds of
  write unavailability. Schedule for off-peak or use RDS Proxy to
  minimize application impact.

- NEVER rely solely on Aurora automatic failover for disaster recovery
  without testing. Automatic failover works for instance-level failures
  but NOT for region-level outages. For regional DR, use Aurora Global
  Database with a documented and tested failover runbook.

- NEVER forget that Aurora Global Database does NOT have a global writer
  endpoint. After a global failover, application connection strings must
  be updated to the new primary region's cluster endpoint. Use Route 53
  health checks and weighted routing policies to automate this.

- NEVER execute `failover-global-cluster` without verifying cross-region
  replication lag (`AuroraGlobalDBReplicationLag` in CloudWatch). High
  lag means the secondary region is behind — promoting it causes data
  loss for the lagged writes.

- NEVER assume Aurora PostgreSQL failover behaves identically to Aurora
  MySQL. While the CLI commands are the same, Aurora PostgreSQL has
  different connection handling characteristics (longer connection
  re-establishment times, different SSL behavior). Always test failover
  for your specific engine.

## Pre-flight safety checks (run before any failover CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing failover
  operation (`failover-db-cluster`, `failover-global-cluster`), emit:
  `CONFIRM: About to <operation> on <cluster> in account <account> region
  <region>. This will promote <replica> to writer and cause a ~60-120s
  write outage. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture pre-state for rollback.** Before failover:
  `aws rds describe-db-clusters --db-cluster-identifier <id> --output json
  > /tmp/<id>-pre-$(date +%s).json`. Document the current writer and
  reader roles for post-failover verification.

- **Verify healthy replica count BEFORE failover.** At least 1 reader in
  `available` status. No healthy reader = BLOCKED.

- **Verify AuroraReplicaLag BEFORE planned failover.** Target replica lag
  < 30 seconds. Higher lag = data loss risk.

- **Verify RDS Proxy target health.** If a proxy is associated,
  `describe-db-proxy-target-groups` must show `HEALTHY`. Unhealthy proxy
  targets cause connection failures during failover.

- **Verify Global DB replication lag BEFORE global failover.**
  `AuroraGlobalDBReplicationLag` in CloudWatch < 5 seconds. Higher lag =
  data loss in the secondary region.

- **Plan DNS cache flush.** After failover, flush:
  - JVM: `System.setProperty("networkaddress.cache.ttl", "0")` or restart.
  - OS: `systemd-resolve --flush-caches` (Linux) or `dscacheutil -flushcache`
    (macOS).
  - Application framework: restart or clear connection pools.

- **Batch limit for fleet-wide failover.** If failing over multiple
  clusters, process one at a time: emit the plan for one cluster, CONFIRM,
  execute, verify, then proceed to the next. Do NOT failover multiple
  production clusters simultaneously — a systematic issue cascades.

- **Plan the failback window.** After a planned failover, schedule a
  failback window during off-peak hours if AZ preference matters.
  Document that failback is another failover event (not an undo).

## Recent AWS features (2024-2026)

Feature notes moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load when deciding whether a recent feature changes the plan.

## References (load on demand)

- [references/failover-procedures.md](references/failover-procedures.md) — per-operation failover procedures, endpoint behavior, DNS flush, timing benchmarks
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (BLOCKED, COMPLETED, global READY)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command listing
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert deep dive, recent AWS features

## Domain

AWS CloudOps / Aurora Failover, High Availability & Disaster Recovery.

## AWS documentation

- **Amazon Aurora User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html
- **Aurora High Availability** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Concepts.AuroraHighAvailability.html
- **Aurora Failover** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.FaultTolerance.html
- **Aurora Global Database** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
- **Aurora Global Database failover** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-disaster-recovery.html
- **RDS Proxy** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/rds-proxy.html
- **Aurora endpoints** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Endpoints.html
- **AWS CLI RDS reference** — https://docs.aws.amazon.com/cli/latest/reference/rds/
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **AWS Well-Architected Framework — Reliability** — https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html
