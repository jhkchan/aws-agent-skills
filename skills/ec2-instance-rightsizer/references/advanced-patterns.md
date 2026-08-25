# Advanced Patterns (load on demand) — EC2 Instance Rightsizer

Quick start rules, Mindset principles, the Step 0 expert-behaviour catalogue, hibernation trade-offs, confidence levels, family-migration tables, workload sizing, Savings Plans and Spot deep-dives, and 2024-2026 feature notes, moved verbatim from SKILL.md.


---

## Quick start — four headline rules (moved from SKILL.md)

- **Memory data is the #1 gate.** Without CWAgent `MemoryUtilization`
  (or `mem_used_percent`), you CANNOT confidently recommend a downsize.
  CPU alone is insufficient — a database at 3% CPU may be using 85% of
  RAM for buffer cache. The expert principle: 14-day CPU < 5% + memory
  from CWAgent confirming < 50% = downsize candidate.
- **Cost formula (memorise this):**
  `monthly_od_cost = hourly_rate × 730 hours/month`
  `monthly_saving = (current_hourly - proposed_hourly) × 730`
- **Idle = stop or terminate.** An instance below 5% CPU for 14
  consecutive days with negligible network and disk I/O is a stop
  candidate first; downsize is the fallback if the workload must stay
  available.
- **Graviton2 requires AMI + application compatibility testing.** A
  Graviton migration is NEVER a one-click operation. You need an arm64
  AMI, architecture-verified application stack, and a test pass. This
  is the #1 reason Graviton recommendations stall — surface it
  explicitly.

## Mindset — four principles (moved from SKILL.md)

EC2 right-sizing is a risk-managed cost decision, not a pure
utilization exercise. The goal is the smallest instance type that
preserves the workload's latency, throughput, memory-headroom, and
credit-depletion SLOs — not the absolute cheapest type that boots.

Four principles guide every recommendation:

- **Utilization data is the foundation, but workload context is the
  override.** A web server at 15% CPU is a downsize candidate; a
  database at 15% CPU but 80% memory is NOT (buffer cache needs RAM).
  Always pair metrics with the workload class.
- **Compute Optimizer is advisory, not authoritative.** Compute
  Optimizer analyses CPU, network, and disk at the hypervisor level
  but does NOT see guest memory unless the CWAgent is installed. Treat
  its findings as a cross-check, never the sole signal.
- **Family migration and Graviton stack on top of right-sizing.**
  Downsizing m5.2xlarge to m5.large saves 50%. Migrating m5.large to
  m6i.large saves another ~10%. Migrating m6i.large to c7g.large
  (Graviton) saves another ~20%. These compound.
- **Termination protection is a hard stop.** If `disableApiTermination`
  is true, the instance is protected. Surface it as a gate before any
  stop/terminate recommendation, never silently override it.

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

These operational gotchas route a recommendation away from the obvious
choice:

- **CWAgent memory is the load-bearing metric for downsizing.**
  `mem_used_percent` from the CWAgent is the only reliable signal for
  guest memory. Without it, a downsize recommendation is MEDIUM
  confidence at best. Databases and in-memory caches (Redis, Memcached)
  may show low CPU but high memory — downsizing these causes OOM or
  cache thrashing.
- **Compute Optimizer does NOT see guest memory.** Its
  `utilizationMetrics` include CPU, network, and disk at the hypervisor
  level. A finding of `Overprovisioned` based on low CPU may be wrong
  if the instance is memory-bound. Always cross-check with CWAgent.
- **CPU credits on t-family are finite.** A t3.large earns 36
  credits/hour and can burst to 2 vCPUs. If `CPUCreditBalance` trends
  to 0, the instance is throttled to baseline (20% of a vCPU). Enabling
  `T2/T3 Unlimited` lets the instance borrow future credits at $0.05/vCPU-
  hour — this can be MORE expensive than migrating to m-family.
- **Graviton2 requires arm64 AMI.** You cannot change the architecture
  of an existing instance. Graviton migration requires launching a NEW
  instance from an arm64 AMI, testing application compatibility, and
  cutting over. This is a multi-step process, not a one-liner.
- **Savings Plans reduce the savings from right-sizing.** If an
  instance is covered by a Compute Savings Plan at a 40% discount, the
  effective hourly rate is already reduced. The dollar saving from
  downsizing is calculated on the DISCOUNTED rate, not the on-demand
  rate. Surface this explicitly.
- **Hibernation requires prerequisites.** Hibernation (RAM-to-disk
  suspend) requires the instance to be EBS-backed, have enough root EBS
  volume for the RAM dump, and be a supported instance family. For
  truly idle instances, stop is simpler than hibernate.
- **Spot instances have volatile pricing.** Right-sizing a Spot
  instance still saves money (fewer vCPUs = lower Spot bid), but the
  savings percentage varies with Spot market price. Use the on-demand
  rate as a conservative baseline.
- **Generation upgrades are free savings.** Migrating m4 to m6i
  (same x86, newer generation) is lower risk than cross-architecture
  (Graviton) and delivers ~15-25% price-performance improvement. Always
  evaluate generation upgrade before Graviton.
- **Termination protection blocks stop/terminate.** An instance with
  `disableApiTermination = true` cannot be terminated without first
  disabling protection. For idle-instance recommendations, surface this
  as a mandatory pre-step.
- **EBS-optimized is default on current-gen.** Older instances (m4,
  c4) may have billed separately for EBS optimization. Current-gen
  (m6i, c7g) includes it. This is a minor but non-zero cost factor in
  generation migrations.

## Step 1 — Hibernation vs stop (moved from SKILL.md)

**Hibernation vs stop:**
| Factor | Stop | Hibernate |
|---|---|---|
| Simplicity | Simple: `aws ec2 stop-instances` | Requires config: `hibernationOptions` |
| Restart speed | Cold boot (1-3 min) | RAM restored (30-60 sec) |
| Prerequisites | EBS-backed | EBS-backed + root volume >= RAM size + supported family |
| Use case | General idle instances | Instances with long warm-up (JVM, heavy init) |

For most idle instances, stop is sufficient. Reserve hibernation for
instances with expensive initialization (large JVM heaps, ML model
loading, database warm cache).

## Step 2 — Confidence levels (moved from SKILL.md)

**Confidence levels:**
| Data available | Confidence for downsize |
|---|---|
| CPU + Memory (CWAgent) + 30-day window + Compute Optimizer agrees | HIGH |
| CPU + Memory (CWAgent) + 14-day window | MEDIUM |
| CPU only (no CWAgent) | LOW — surface as "install CWAgent and re-evaluate" |
| Compute Optimizer only (no CloudWatch pull) | LOW — always verify with raw metrics |

## Step 3: Instance-family migration — generation and cross-family tables (moved from SKILL.md)

Current-generation instances deliver better price-performance than
previous generations. Migrating within the same architecture (x86_64
to x86_64) is lower risk than cross-architecture (Graviton).

**Generation migration paths (x86_64):**
| From | To | Price-performance improvement | Risk |
|---|---|---|---|
| m4 | m6i or m7i | ~20-30% | LOW — same ISA, newer silicon |
| c4 | c6i or c7i | ~25-35% | LOW |
| r4 | r6i or r7i | ~20-30% | LOW |
| t2 | t3 or t4g | ~15-25% | LOW (t4g is Graviton — cross-reference Step 4) |
| m5 | m6i | ~10-15% | LOW |
| c5 | c6i | ~10-15% | LOW |
| m5 | m7i | ~20-25% | LOW — latest generation |

**Cross-family migration (same generation):**
| Workload shift | From | To | Rationale |
|---|---|---|---|
| General → compute-bound | m6i | c6i | CPU-heavy workloads (CI/CD, batch processing) |
| General → memory-bound | m6i | r6i | In-memory caches, large datasets |
| Compute → general | c6i | m6i | Workload balanced out (more RAM needed) |
| Memory → general | r6i | m6i | Memory overprovisioned |


## Step 3 — same-architecture migration note (moved from SKILL.md)


This is safe for same-architecture migrations. For Graviton, see Step 4
— you cannot modify the architecture of a running instance.

## Step 5 — Credit economics table (moved from SKILL.md)

**Credit economics:**
| Instance | vCPUs | Baseline perf | Credits/hour | Max burst |
|---|---|---|---|---|
| t3.nano | 2 | 5% | 6 | 2 vCPUs for ~3 min |
| t3.micro | 2 | 10% | 12 | 2 vCPUs for ~6 min |
| t3.small | 2 | 20% | 24 | 2 vCPUs for ~12 min |
| t3.medium | 2 | 20% | 24 | 2 vCPUs for ~12 min |
| t3.large | 2 | 30% | 36 | 2 vCPUs for ~18 min |
| t3.xlarge | 4 | 40% | 96 | 4 vCPUs for ~24 min |
| t3.2xlarge | 8 | 40% | 192 | 8 vCPUs for ~24 min |

## Step 5 — When Unlimited is cheaper than m-family (moved from SKILL.md)

**When Unlimited is cheaper than m-family:**
```
Unlimited surcharge = $0.05/vCPU-hour for borrowed credits
  If borrowed credits < ~150 hours/month per vCPU:
    Unlimited is cheaper than migrating to m-family.
  If borrowed credits > ~150 hours/month per vCPU:
    Migrate to m-family (consistent CPU is cheaper than sustained borrowing).
```

## Step 6: Workload-specific sizing rules (moved from SKILL.md)

Different workload classes have different right-sizing tolerance.

| Workload class | Right-sizing tolerance | Key metric | Minimum viable |
|---|---|---|---|
| Web server (Nginx, Apache) | HIGH — can downsize aggressively | CPU p95, connection count | 2 vCPU for HA |
| Application server (Tomcat, JVM) | MEDIUM — need JVM heap headroom | Memory utilization, GC pause | Enough RAM for heap + 30% overhead |
| Database (PostgreSQL, MySQL) | LOW — memory is buffer cache | Memory utilization, disk I/O | Memory must hold working set |
| Batch processing | HIGH — can use Spot, tolerate latency | CPU avg, job completion time | Size to job deadline |
| CI/CD runner | HIGH — can scale on demand | CPU during builds | t3.medium for small repos |
| ML inference | LOW — latency-sensitive | GPU utilization, p99 latency | GPU memory for model |
| Cache (Redis, Memcached) | VERY LOW — memory is data | Memory utilization, evictions | Memory must hold full dataset |
| Dev/test | VERY HIGH — can stop when idle | Uptime | t3.micro/nano |

**Database special case:**
Never recommend downsizing a production database based on CPU alone.
Databases use memory for buffer cache (InnoDB buffer pool, PostgreSQL
shared_buffers). Low CPU + high memory utilization means the cache is
working. Downsizing memory reduces cache hit ratio, which increases
disk I/O, which increases latency — a cascading performance regression.

## Step 7: Savings Plans and pricing model impact (moved from SKILL.md)

Right-sizing interacts with pricing commitments. Always check active
Savings Plans and RIs before computing dollar savings.

**Compute Savings Plans:**
- Commit to $/hour spend for 1 or 3 years.
- Apply to ANY instance family, size, AZ, region, OS, or tenancy.
- Right-sizing a covered instance saves at the COMMITTED rate, not
  on-demand. Example: m5.2xlarge at $0.384/h OD, covered by a 40% off
  plan → effective $0.230/h. Downsizing to m5.large at $0.096/h OD →
  effective $0.058/h. Monthly saving: ($0.230 - $0.058) × 730 = $125/mo
  (NOT $210/mo at OD rates).

**Instance Savings Plans / Reserved Instances:**
- Commit to a specific instance family + region.
- Right-sizing WITHIN the committed family is fine (m5.2xlarge →
  m5.large keeps the RI coverage).
- Right-sizing ACROSS families (m5 → c5) loses RI coverage for the
  uncovered family. Surface this as a cost: "migrating from m5 to c5
  saves on compute but the existing m5 RI becomes unused."

**Spot instances:**
- Right-sizing Spot instances saves at the Spot rate, which fluctuates.
- Use the on-demand rate as a conservative baseline for savings math.
- Smaller Spot instances are less likely to be interrupted (lower
  capacity footprint).

**Decision: right-size first, then optimize pricing model.**
Always right-size the instance type BEFORE buying a Savings Plan or RI.
Committing to an oversized instance locks in the waste.

## Step 8: Spot vs on-demand — interruptible workload criteria (moved from SKILL.md)

For fault-tolerant workloads (batch, CI/CD, stateless web servers),
Spot can deliver 60-90% savings vs on-demand.

**Spot right-sizing criteria:**
```
Is the workload stateless or fault-tolerant?
├── NO → Use on-demand. Spot interruption will cause data loss.
└── YES → Can it checkpoint or resume from interruption?
    ├── YES → Spot is ideal. Size the instance to minimize
    │         interruption impact (smaller = less work lost).
    └── NO → Use Spot ONLY if the workload can tolerate full restart.
```


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Graviton4 (r8g, c8g, m8g) GA (2025-2026):** Latest Graviton
  generation with higher vCPU counts and improved per-core performance.
  Evaluate against Graviton3 (m7g/c7g/r7g) for the best price-
  performance.
- **m7i, c7i, r7i (Sapphire Rapids) GA:** Intel 4th Gen Xeon instances
  with higher memory bandwidth and AVX-512. Evaluate against m6i/c6i
  for generation upgrade.
- **Compute Optimizer enhanced recommendations (2024-2025):** Now
  includes memory metrics from CWAgent in its analysis (if enrolled in
  enhanced infrastructure metrics). Cross-check findings still apply.
- **EC2 Instance Connect Endpoint (2024):** Private SSH access without
  bastion. Does not affect right-sizing but simplifies post-migration
  verification.
- **Capacity Reservations (2024-2025):** On-Demand Capacity Reservations
  can now be created for specific instance types in specific AZs.
  Useful for ensuring capacity post-right-sizing in tight markets.
- **Spot placement scores (2024):** Helps identify AZs with high Spot
  capacity for specific instance types. Use when evaluating Spot
  migration.
- **EC2 hibernation expansion (2024):** Now supports larger instance
  sizes (up to m6i.4xlarge with 64 GB RAM). Verify prerequisites
  before recommending.
