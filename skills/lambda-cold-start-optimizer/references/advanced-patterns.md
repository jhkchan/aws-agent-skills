# Advanced patterns — lambda-cold-start-optimizer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Mindset — five principles

Five principles guide every recommendation:

- **InitDuration is the cold-start signal.** Lambda reports
  `InitDuration` separately from `Duration` in CloudWatch and Lambda
  Insights. InitDuration includes only the init phase; Duration includes
  only the handler execution. The cold-start end-to-end latency is
  `InitDuration + Duration` on the first invocation of a new container.
- **SnapStart removes InitDuration for Java.** When enabled, Lambda
  takes a snapshot of the initialized execution environment and
  restores it on cold start. InitDuration drops from 1-3 s to ~200 ms
  (restore overhead). This is a 90%+ reduction for Java.
- **Provisioned concurrency removes cold starts entirely.** It
  pre-initializes N execution environments and keeps them warm. No
  InitDuration, no cold start. But it charges for idle time — the
  classic cost-vs-latency trade-off.
- **Runtime choice matters for init speed.** Compiled runtimes (Java,
  .NET, Go) have slower init than interpreted runtimes (Node.js,
  Python) due to JIT warmup and framework bootstrap. Go has near-zero
  init. Java has the highest init. SnapStart narrows the gap for Java.
- **Package size correlates with init time.** A 50 MB fat JAR takes
  longer to download, extract, and load than a 5 MB trimmed package.
  Layers add overhead because each layer is a separate .zip that Lambda
  extracts independently.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **VPC cold start is solved (since 2019).** Hyperplane ENIs reduced
  VPC cold-start overhead from 5-10 s to <100 ms. Do NOT attribute
  cold-start latency to VPC without verifying ENI health.
- **SnapStart is Java-only.** It snapshots the JVM after init. Node.js,
  Python, and Go do not benefit. Never recommend SnapStart for non-Java.
- **SnapStart requires versioned aliases.** You cannot enable SnapStart
  on `$LATEST`. Publish a version, create an alias, then enable.
- **SnapStart has a restore cost (~150-200 ms).** For ultra-low-latency
  APIs (<100 ms SLO), provisioned concurrency is still needed on top.
- **Provisioned concurrency charges for idle.** A function at 1 GB with
  10 provisioned and no traffic costs ~$394/month idle. Always pair
  with a cost-justification check.
- **Provisioned concurrency does not support `$LATEST`.** Attach to a
  version or alias. Publish a version first.
- **X-Ray tracing adds 10-50 ms overhead** per traced invocation.
  Evaluate sampling rate for ultra-low-latency functions.
- **Lambda Insights adds ~10-20 ms overhead** via the extension Layer.
  The telemetry value outweighs the cost for cold-start analysis.
- **Lambda Layers can INCREASE init time.** Each Layer is a separate
  .zip extracted independently. Keep Layers to 3-5 maximum.
- **ARM64 may have different init profiles.** Benchmark both
  architectures with Power Tuning before assuming parity.
- **EFS mount adds 100-500 ms on cold starts.** Use provisioned
  concurrency or local /tmp for latency-critical paths.
- **Runtime deprecation blocks optimizations.** Deprecated runtimes
  (nodejs16, java8, python3.7) may not support SnapStart, ARM64, or
  current Lambda Insights. Check deprecation status first.
- **Init code runs once per execution environment.** Lambda reuses
  environments across invocations. Global-scope code runs once per
  container lifecycle, not per invocation.

## Step 1 deep dive: latency-vs-memory curve and Power Tuning

Memory is the first lever because Lambda couples vCPU to memory (1769 MB
= 1 vCPU). More memory gives more CPU, which speeds up both init and
handler execution for CPU-bound workloads.

**The latency-vs-memory curve:**
```
cold_start_latency = InitDuration(memory) + Duration(memory)

Example: 512 MB at 3200 ms init + 1800 ms handler = 5000 ms cold start
         2048 MB at 1400 ms init + 600 ms handler  = 2000 ms cold start (60% reduction)
         3072 MB at 1100 ms init + 400 ms handler  = 1500 ms cold start (70% reduction)
```

**Finding the latency-optimal memory: AWS Lambda Power Tuning.** Open-
source Step Functions tool that empirically measures the duration curve
across memory settings. For cold-start optimization, read the `fastest`
field (not `cheapest`). Full deployment and execution CLI is in
`references/cold-start-metrics-and-power-tuning.md`.

## Step 1 deep dive: cost-latency trade-off note

**Cost-latency trade-off note:** Higher memory increases per-invocation
cost. For cold-start optimization, accept the cost increase ONLY if the
latency reduction is SLO-critical. If the function is also cost-
sensitive, evaluate provisioned concurrency as an alternative (Step 2).

## Step 2 deep dive: what provisioned concurrency is

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts entirely. It is the most powerful cold-start
mitigation but charges for idle time.

## Step 2 deep dive: scheduling note

**Scheduling note:** Provisioned concurrency takes 1-2 minutes to
initialize after configuration. For predictable traffic spikes (e.g.,
morning rush), schedule capacity increases 5-10 minutes in advance via
Application Auto Scaling scheduled actions.

## Step 3 deep dive: SnapStart enablement CLI, expected impact, caveats

**Enabling SnapStart:**
```bash
# 1. Enable SnapStart on the function
aws lambda update-function-configuration \
  --function-name <name> \
  --snap-start '{"ApplyOn":"PublishedVersions"}'

# 2. Publish a version (SnapStart snapshots the version, not $LATEST)
aws lambda publish-version --function-name <name>

# 3. Create or update an alias pointing at the version
aws lambda update-alias \
  --function-name <name> \
  --name prod \
  --function-version <new-version>

# 4. Verify SnapStart status
aws lambda get-function-configuration \
  --function-name <name> --qualifier <version> \
  --query 'SnapStart.{OptimizationStatus:OptimizationStatus,ApplyOn:ApplyOn}'
```

**Expected impact:**

| Metric | Before SnapStart | After SnapStart |
|---|---|---|
| InitDuration | 1500-3500 ms | 150-250 ms (restore overhead) |
| Cold-start reduction | — | 85-95% |
| Handler Duration | Unchanged | Unchanged |

**SnapStart caveats:**
- **Network connections are NOT restored.** Database connections,
  HTTP clients, and TCP sockets established in init are reset on
  snapshot restore. Re-establish connections in the handler or use a
  lazy-init pattern that checks connection validity.
- **Unique values per invocation.** If init generates a unique ID or
  randomness, it will be identical across restored snapshots. Use
  `SecureRandom` or generate uniqueness in the handler, not in init.
- **CRDT / caching libraries.** Some caching libraries (Caffeine,
  Guava Cache) may behave unexpectedly across snapshot restores. Test
  thoroughly.

## Step 4 deep dive: why init-phase optimization

Regardless of runtime, the init phase is where most cold-start time
lives. Move heavy initialization OUTSIDE the handler into global scope,
so it runs once per warm container, not per invocation.

## Step 4 deep dive: runtime-specific connection reuse patterns

**Runtime-specific connection reuse patterns:**

| Runtime | DB library | Pattern |
|---|---|---|
| Node.js | pg, mysql2 | `const pool = new Pool({...})` at module scope |
| Python | psycopg2, pymysql | Global connection with lazy-init + validity check |
| Java | HikariCP | `DataSource` as static field |
| Go | database/sql | `sql.Open()` at package level |

## Step 5 deep dive: VPC cold start — key fact and failure modes

**The key fact:** Since 2019, Lambda uses Hyperplane ENIs for VPC-
attached functions. Cold-start overhead dropped from 5-10 s to <100 ms.
VPC attachment is NO LONGER a primary cold-start driver.

**When VPC still causes latency:**

| Condition | Fix |
|---|---|
| ENI limit hit | Request limit increase; consolidate into fewer subnets |
| Subnet IP exhaustion | Expand subnet CIDR; use dedicated Lambda subnets |
| SecurityGroup stale reference | Update SG references |
| NAT Gateway latency | Use VPC endpoints for AWS service traffic (S3, DynamoDB, SQS) |

## Step 5 deep dive: when to suspect VPC

**Recommendation:** If VPC cold-start latency is <100 ms (hyperplane
ENI working), VPC is NOT the bottleneck. If >500 ms, investigate
ENI/subnet/SG issues.

## Step 6 deep dive: init speed by runtime

**Init speed by runtime (typical, no SnapStart):**

| Runtime | Typical InitDuration | Notes |
|---|---|---|
| Go (provided.al2023) | <100 ms | Compiled binary, near-zero init |
| Node.js 20+ | 100-300 ms | V8 JIT warmup |
| Python 3.12 | 100-300 ms | Interpreter startup |
| Ruby 3.x | 200-400 ms | Interpreter startup |
| .NET 8 | 500-1500 ms | CLR + ASP.NET Core bootstrap |
| Java 21 (no SnapStart) | 1500-3500 ms | JVM + framework bootstrap |
| Java 21 (with SnapStart) | 150-250 ms | Snapshot restore |

## Step 6 deep dive: ARM64 (Graviton)

**ARM64 (Graviton):** ~20% better price-performance AND often faster
init for interpreted runtimes. Verify ARM compatibility for compiled
runtimes before migration.

## Step 7 deep dive: package trimming (Proguard, tree-shaking, layers)

**Java fat JAR trimming (Proguard):**
```bash
# Use Proguard or aws-lambda-java-serialization to strip unused classes
# Maven configuration for thin JAR + Proguard:
# See references/cold-start-metrics-and-power-tuning.md for full config

# Alternative: use Lambda Layers for shared dependencies
aws lambda publish-layer-version \
  --layer-name shared-deps \
  --zip-file fileb://deps.zip \
  --compatible-runtimes java21
```

**Node.js / Python package trimming:**
- Use `esbuild` or `webpack` to tree-shake unused dependencies.
- Remove `node_modules` dev dependencies (`devDependencies`).
- Use `pip install --no-deps` and install only runtime deps.
- Split shared code into a Lambda Layer.

**Layer usage caution:** Layers reduce the main package size but add
extraction overhead. Use at most 3-5 Layers. Each Layer is extracted
independently at init.

## Expert heuristic (full)

Lambda cold-start optimization follows a clear priority order: memory-to-
CPU scaling (Power Tuning finds the latency-optimal memory, where more
memory gives more vCPU and both init and handler speed up for CPU-bound
workloads — 1769 MB = 1 vCPU is the inflection point), SnapStart
(eliminates the init phase entirely for Java by restoring a pre-
initialized snapshot, dropping InitDuration from 1-3 s to ~200 ms), and
provisioned concurrency (for latency-critical paths where even SnapStart
is not fast enough — it pre-initializes environments and keeps them
warm, at idle cost). The heuristic: if Java, enable SnapStart first;
if still latency-sensitive and sync, add provisioned concurrency; if
not Java, optimize init phase (global-scope connection pooling) and
tune memory via Power Tuning. VPC cold start is solved (hyperplane ENI)
and rarely the bottleneck.

## Recent AWS features (2024-2026)

- **Lambda SnapStart (2024-2025):** Java-only, stable on java21+. Check
  current support matrix for additional runtimes.
- **Hyperplane ENI (GA since 2019):** VPC cold-start overhead <100 ms.
  VPC is no longer a cold-start driver.
- **Lambda ARM64 (Graviton) GA:** All major runtimes support arm64.
  ~20% better price-performance; often faster init for interpreted
  runtimes.
- **AWS Lambda Power Tuning:** Supports latency mode (`fastest`) and
  cost mode (`cheapest`).
- **Lambda Insights:** Provides `InitDuration`, `memory_used`,
  `cpu_total_time`, `coldStarts`. Required for cold-start analysis.
- **Provisioned Concurrency autoscaling (2024):** Application Auto
  Scaling on Lambda aliases via target-tracking on
  `ProvisionedConcurrencyUtilization`.
- **Runtime deprecation (2024-2026):** nodejs16, java8, python3.7
  deprecated. Upgrading unlocks SnapStart, ARM64, current Insights.
- **EFS for Lambda (GA):** Adds 100-500 ms on cold starts. Use /tmp or
  provisioned concurrency for latency-critical paths.

