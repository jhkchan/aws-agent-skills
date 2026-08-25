# DocumentDB Cluster Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Activation keywords (moved from SKILL.md)


create DocumentDB cluster, DocumentDB instance, DocumentDB change
streams, DocumentDB global cluster, DocumentDB storage autoscaling,
DocumentDB subnet group, DocumentDB parameter group, DocumentDB KMS
encryption, DocumentDB backup retention, DocumentDB index, mongo shell
connect DocumentDB.


## Configuration dependency graph (moved from SKILL.md)


DocumentDB configurations are NOT independent. The cluster must exist
before instances. The subnet group must exist before the cluster. Change
streams require parameter-group configuration. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Subnet group | at least 2 subnets across 2 AZs | subnets must be private; no public DocumentDB | cluster creation |
| Security group | VPC exists | SG must allow port 27017 (or custom) from app tier | cluster network access |
| Parameter group | none (uses default initially) | change streams parameter requires cluster modification + reboot | change streams, TTL, profiling |
| KMS key | KMS key exists (if customer-managed) | KMS key cannot be changed after cluster creation without snapshot/restore | encryption at rest |
| Cluster (create-db-cluster) | subnet group, security group, KMS key, parameter group | cluster endpoint is immutable once created; storage volume auto-grows | instances, endpoints |
| Instances (create-db-instance) | cluster exists; instance class chosen | instances are created one at a time; failover priority is set per instance | compute capacity |
| Storage autoscaling | cluster exists | autoscaling ceiling must be set explicitly; hitting the ceiling stops writes | storage growth |
| Change streams | parameter group with change_streams_log_retention_duration > 0 | change stream retention can be 1-3 days; expired events are lost | CDC pipelines |
| Global cluster | primary cluster exists and is healthy | secondary clusters are read-only; failover is not automatic (must be scripted) | cross-region DR |
| Backup retention | cluster exists (set at creation or modify) | retention 1-35 days; point-in-time recovery enabled automatically with backup | PITR, snapshot restore |
| Indexes | cluster is accessible via mongo shell | creating an index on a large collection blocks; use background index builds | query performance |

**The storage-autoscaling-ceiling and index-before-query rows are the
ones a baseline model misses.** DocumentDB auto-grows storage but stops
at the ceiling. And without explicit indexes, every query is a scan. The
procedure below forces an explicit decision on each.

**Cross-dependency gotchas:**
- The subnet group must span at least 2 AZs for multi-AZ clusters.
  Single-AZ subnet groups block multi-AZ deployment.
- Change streams require the parameter
  `change_streams_log_retention_duration` to be greater than 0 in the
  cluster parameter group. The default is 0 (disabled).
- KMS key is set at cluster creation. Changing it later requires a
  snapshot-restore cycle (downtime).
- Global cluster secondary clusters are read-only. Applications must
  be designed to read from the secondary or wait for promotion during
  failover.


## Expert heuristic: MongoDB API compatibility gaps (moved from SKILL.md)


DocumentDB implements the MongoDB wire protocol but does NOT support
100% of MongoDB's API surface. A baseline model assumes "MongoDB
compatible = drop-in replacement." The expert knows the gaps.

```text
Unsupported aggregation pipeline stages (DocumentDB 5.0):
  ├── $graphLookup — NOT supported (no graph traversal)
  ├── $merge — NOT supported (use $out for materialization)
  ├── $facet — limited support (no nested $facet)
  └── $bucket / $bucketAuto — NOT supported

Unsupported features:
  ├── Transactions — supported on 4.0+ but with constraints:
  │     cross-shard transactions NOT supported (single-shard only)
  ├── Retryable writes — NOT supported (retryWrites=false always)
  ├── Change stream $lookup stage — NOT supported in pipeline
  └── Collation in indexes — NOT supported

Expert rule:
  1. Audit aggregation pipelines BEFORE migrating from MongoDB
  2. Replace $graphLookup with application-side traversal
  3. Replace $merge with a two-step $out + application merge
  4. Test with the actual driver version, not just the shell
```

**Key implication:** "MongoDB-compatible" means wire-protocol-level
compatibility, not feature parity. Unmapped aggregation stages cause
runtime errors, not syntax errors — they fail at execution time, not
parse time.


## Expert heuristic: TLS certificate rotation downtime (moved from SKILL.md)


DocumentDB clusters use a cluster certificate for TLS connections.
A baseline model assumes certificates rotate transparently. The
expert knows the rotation can cause connectivity blips.

```text
DocumentDB TLS certificate lifecycle:
  ├── Certificate is managed by AWS RDS/DocumentDB infrastructure
  ├── Rotation is automatic but NOT instant — the cluster endpoint
  │     gets a new cert, and existing connections using the old
  │     cert's fingerprint break on next TLS handshake
  ├── The rds-combined-ca-bundle.pem contains BOTH the old and
  │     new CA certs — clients using this bundle survive rotation
  └── Clients pinning a SPECIFIC certificate fingerprint break

Expert rule:
  1. NEVER pin a specific certificate fingerprint in the client
  2. ALWAYS use rds-combined-ca-bundle.pem (contains all CAs)
  3. When AWS announces CA rotation, update the CA bundle in
     application containers BEFORE the rotation date
  4. Use connection pooling with health checks — pools that don't
     validate TLS on reconnect will mask rotation failures
```

**Key implication:** TLS certificate rotation is transparent ONLY
if clients use the combined CA bundle. Pinned certificates or stale
CA bundles cause silent connection failures during rotation.


## Step 14 — CloudWatch metrics (moved from SKILL.md)


| Metric | What it measures | Alert threshold |
|---|---|---|
| DatabaseCpuUtilization | CPU across instances | > 80% sustained 5 min |
| DatabaseFreeStorageSpace | Free storage (bytes) | < 20% of ceiling |
| DatabaseConnections | Active connections | Approaching max |
| DatabaseMemoryUsagePercentage | RAM utilization | > 90% sustained |
| DatabaseReplicaLag | Replica lag (seconds) | > 30 seconds |

