# Instance Classes and Parameter Tuning Guide — RDS Instance Deployer

Deep reference on instance-class families, sizing heuristics, engine
parameter tuning, Multi-AZ standby semantics, Aurora Serverless v2 ACU
sizing, and Aurora Global Database topology. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Instance class families — detailed comparison

### Burstable (db.t4g, db.t3, db.t3.micro)

Burstable instances have a baseline CPU performance plus the ability to
burst above the baseline using CPU credits. When credits run out, the
instance is throttled to its baseline.

| Class | vCPU | Memory | Baseline | Credits/hour | Use when |
|---|---|---|---|---|---|
| `db.t4g.micro` | 2 | 1 GB | 10% | 12 | Dev/test, tiny workloads |
| `db.t4g.small` | 2 | 2 GB | 20% | 24 | Small dev, low-traffic apps |
| `db.t4g.medium` | 2 | 4 GB | 20% | 24 | Small prod with idle time |
| `db.t4g.large` | 2 | 8 GB | 40% | 48 | Microservice with bursty load |
| `db.t4g.xlarge` | 4 | 16 GB | 40% | 96 | Burstable prod |
| `db.t3.micro` | 2 | 1 GB | 20% | 12 | Legacy dev/test (Intel) |

**Critical: CPU credit exhaustion is the #1 burstable-instance incident.**
Monitor `CPUCreditBalance` and `CPUSurplusCreditBalance`. A workload that
sustains > baseline burns credits; once exhausted, performance drops to
baseline (10-40% of vCPU). For production OLTP, prefer `db.m*` or
`db.r*` to avoid this failure mode.

### General-purpose (db.m7g, db.m6i, db.m5)

Balanced CPU and memory. The default for most OLTP workloads.

| Class | vCPU | Memory | Network | Use when |
|---|---|---|---|---|
| `db.m7g.large` | 2 | 8 GB | up to 12.5 Gbps | Small prod (Graviton) |
| `db.m7g.xlarge` | 4 | 16 GB | up to 15 Gbps | Medium prod |
| `db.m7g.2xlarge` | 8 | 32 GB | up to 15 Gbps | Standard prod |
| `db.m7g.4xlarge` | 16 | 64 GB | up to 15 Gbps | Heavy prod |
| `db.m6i.large` | 2 | 8 GB | up to 12.5 Gbps | Intel equivalent |
| `db.m5.large` | 2 | 8 GB | up to 10 Gbps | Legacy Intel |

### Memory-optimized (db.r7g, db.r6i, db.r6g, db.x2g)

High memory-to-CPU ratio. Preferred for Aurora (storage is shared;
buffer cache matters per-instance).

| Class | vCPU | Memory | Network | Use when |
|---|---|---|---|---|
| `db.r7g.large` | 2 | 16 GB | up to 15 Gbps | Aurora / large working set |
| `db.r7g.xlarge` | 4 | 32 GB | up to 15 Gbps | Aurora production |
| `db.r7g.2xlarge` | 8 | 64 GB | up to 15 Gbps | Aurora heavy prod |
| `db.r7g.4xlarge` | 16 | 128 GB | up to 15 Gbps | Analytics + OLTP |
| `db.x2g.large` | 2 | 32 GB | up to 25 Gbps | Oracle/SAP, in-memory |

### Compute-optimized (db.c7g, db.c6i)

High CPU-to-memory ratio. Compute-heavy analytics or batch.

### Graviton (g-series) preference

Graviton instances (g) typically offer ~20% price/perf improvement over
Intel (i) for the same workload. Prefer `db.m7g`, `db.r7g`, `db.t4g`
unless a specific Intel/AMD compatibility requirement exists.

## Sizing heuristics

### Buffer cache sizing

For OLTP workloads, the buffer cache should hold the "hot" working set.

| Engine | Parameter | Recommended starting point |
|---|---|---|
| PostgreSQL | `shared_buffers` | ~25% of instance memory (conservative) |
| MySQL | `innodb_buffer_pool_size` | ~75% of instance memory |
| SQL Server | `max server memory (MB)` | total memory minus 2-4 GB for OS |
| Oracle | `sga_target` or `memory_target` | ~60-70% of instance memory |

### Connection sizing

Each connection consumes memory. Plan `max_connections` based on
`(available_memory_MB / per_connection_memory)`.

| Engine | Per-connection memory | Recommended max |
|---|---|---|
| PostgreSQL | 5-10 MB (forks a process) | 100-300; use PgBouncer / RDS Proxy beyond that |
| MySQL | 256 KB - 2 MB (thread) | 500-2000; use RDS Proxy beyond |
| SQL Server | variable | workload-dependent |

**Rule of thumb**: prefer a connection pooler (PgBouncer, RDS Proxy)
over unbounded `max_connections`. Each idle connection still consumes
memory and the engine spends CPU tracking it.

### IOPS sizing (gp3, io1, io2)

| Storage type | Baseline | Provisioned | Cost |
|---|---|---|---|
| `gp2` | 3 IOPS/GB | burst bucket | included |
| `gp3` | 3000 IOPS + 125 MB/s | up to 256,000 IOPS | baseline free; pay above |
| `io1` | n/a | up to 256,000 IOPS | per-IOPS-month |
| `io2` | n/a | up to 256,000 IOPS | per-IOPS-month (higher durability) |

**gp3 IOPS-to-storage ratio cap**: provisioned IOPS cannot exceed
500 × allocated-GB for MySQL/PostgreSQL. A `modify-db-instance`
requesting 15,000 IOPS on a 20 GB instance fails validation. Either
raise storage or drop IOPS.

## Multi-AZ standby semantics

### Non-Aurora Multi-AZ

- Synchronous replication to standby in a different AZ.
- Standby is NOT usable for reads (no read-scaling).
- Failover is automatic (60-120 seconds): standby is promoted, DNS flips.
- Client-side: connection drops during failover; app must retry.
- JVM `networkaddress.cache.ttl` defaults to 60 seconds — lower it so
  clients reconnect after DNS update.
- Enable Multi-AZ at creation (no impact) or via modify (causes 1-3
  minute I/O suspension during standby provisioning).

### Aurora cluster topology

- The CLUSTER spans AZs by default (not a per-instance setting).
- Writer instance in one AZ; Reader instances can be in others.
- Failover promotes a Reader to Writer (typically < 30 seconds for
  Aurora; faster than non-Aurora Multi-AZ).
- Reader instances ARE usable for reads (unlike non-Aurora standby).

### SQL Server Multi-AZ

- Uses Always On Availability Groups / database mirroring.
- Some features (memory-optimized tables, cross-database transactions
  in certain modes) have constraints under Multi-AZ.
- Plan the upgrade window accordingly.

### Read Replica vs Multi-AZ

| Property | Read Replica | Multi-AZ standby |
|---|---|---|
| Replication | asynchronous | synchronous |
| Standby usable for reads | YES | NO |
| Promotable to primary | YES (manual) | YES (automatic) |
| Cross-region possible | YES | NO (single region) |
| Use case | read-scaling, cross-region DR | HA within a region |

## Aurora Serverless v2 ACU sizing

Aurora Capacity Units (ACU): 2 GB memory per ACU. CPU scales with ACU.

| Workload | MinCapacity | MaxCapacity | Rationale |
|---|---|---|---|
| Dev/test | 0.5 | 4 | Lowest cost; tolerate cold-start latency |
| Production (predictable) | 4-8 | 16-32 | Avoid cold-start; cap cost at peak |
| Production (bursty) | 2-4 | 32-64 | Lower min to save cost; high max for spikes |
| Analytics | 8-16 | 64-128 | High min for sustained query load |

**Cold-start warning**: `MinCapacity: 0.5` means the cluster can scale
down to ~1 GB buffer cache. The first query after idle may take seconds
to ramp back up — unsuitable for latency-sensitive production workloads.
Use `MinCapacity: 2-4` for production.

## Aurora Global Database topology

Aurora Global Database provides a primary cluster in one region with
read-only secondary clusters in other regions. Replication is typically
< 1 second.

| Property | Primary | Secondary |
|---|---|---|
| Read/write | read + write | read-only |
| KMS CMK | one CMK in primary region | SEPARATE CMK in each secondary region |
| Failover | n/a | promotable to primary (one-way) |
| Backtrack | supported (MySQL) | NOT supported on secondary |

**After a failover/promotion**: the new primary does NOT automatically
re-establish replication back to the old primary. Operator must explicitly
re-create the Global Database topology with the new primary as source.

**KMS in secondary regions**: each secondary region requires its own CMK.
If the CMK is missing or disabled in a secondary region, replication stalls.

## Parameter group — apply methods

| Apply method | Effect |
|---|---|
| `immediate` | applies without reboot (dynamic parameters only) |
| `pending-reboot` | applies at next reboot / maintenance window |

`pending-reboot` parameters queue until the next reboot. For a new
provisioning, this is fine — the instance reboots as part of the create.
For modifying an existing production instance, schedule the reboot in
the maintenance window.

## Option group — engine-specific features

| Engine | Common options |
|---|---|
| PostgreSQL | `pgaudit` (audit logging), `pg_repack` (bloat removal), `pgvector` |
| MySQL | `MARIADB_AUDIT_PLUGIN` (audit), `SQL_SERVER_TRANSLATOR` (Babelfish) |
| SQL Server | `SQLSERVER_BACKUP_RESTORE`, `Native Encryption` |
| Oracle | `OEM_AGENT`, `SQLT`, `STATSPACK` |

Option group version must match the engine + major version. Engine
upgrades may require option group upgrades first.

## AWS documentation references

- RDS DB Instance Classes —
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.DBInstanceClass.html
- Working with DB Parameter Groups —
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithParamGroups.html
- Working with Option Groups —
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithOptionGroups.html
- Multi-AZ Deployments —
  https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html
- Aurora Serverless v2 —
  https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- Aurora Global Database —
  https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html
