# Advanced Patterns — Lambda Memory Optimizer

Deep-dive material moved verbatim from SKILL.md: Step-0 non-obvious
behaviours, data-quality short-circuits, U-curve and provisioned-
concurrency pricing math, overhead baselines, and recent AWS features.
Load on demand.

### What this skill does

Translates a Lambda function's memory configuration and runtime
behaviour into a concrete memory-tuning recommendation with a dollar-
denominated savings estimate AND a latency delta. The verdict is the
highest-leverage action across six memory dimensions — memory size,
provisioned concurrency memory footprint, init-phase memory, EFS /
container-image / Layers overhead, /tmp storage, and architecture
(ARM64 memory-to-CPU ratio) — applied in priority order. Always pairs
the recommendation with exact CLI commands or Power Tuning invocation.

### Quick start


- **The U-curve is the #1 lever.** Lambda couples vCPU to memory (1769
  MB = 1 vCPU). More memory can REDUCE total cost when faster execution
  offsets the higher per-GB-second rate. Classic example: 128 MB at 5 s
  costs $0.0000104/invocation; 512 MB at 1 s costs $0.0000083 — 20%
  CHEAPER at the higher memory. Always run Power Tuning before assuming
  128 MB is cheapest.
- **Cost formula (memorise this):**
  `cost = (invocations × duration_s × memory_GB × $0.0000166667)
         + (invocations × $0.0000002)`
- **Memory size scales the provisioned-concurrency idle bill linearly.**
  A function at 2 GB with 10 PC executions pays 16x the idle bill of
  the same concurrency at 128 MB. Right-size memory BEFORE sizing PC.
- **ARM64 has a different memory-to-CPU ratio.** After migrating from
  x86_64 to arm64, re-run Power Tuning — the U-curve minimum shifts
  because the same memory allocation yields a different vCPU slice on
  Graviton2.

### Mindset

Lambda memory optimization is a price-performance decision, not a pure
utilization exercise. The goal is the memory configuration that
minimizes dollar cost while preserving latency and error-rate SLOs —
not the absolute minimum memory that runs the code. The memory
allocation is simultaneously a CPU allocation (they are coupled at
1769 MB = 1 vCPU), so the decision affects both cost and performance.

Four principles guide every recommendation:

- **The cost curve is U-shaped.** As memory increases, duration usually
  drops faster than the per-GB-second rate rises — up to an inflection
  point. The optimal memory is workload-specific; Power Tuning measures
  it empirically.
- **Cost-optimal ≠ latency-optimal.** The Power Tuning `cheapest` field
  is the cost minimum; `fastest` is the latency minimum. The two
  usually differ. Surface both numbers and let the operator choose
  based on their priority (FinOps vs UX).
- **CPU-bound vs I/O-bound changes the shape of the U-curve.** CPU-
  bound workloads see step-function duration improvement at the 1769 MB
  (1 vCPU) boundary. Pure I/O-bound workloads may be cheapest at 128 MB
  because CPU allocation does not speed up network waits.
- **Memory size cascades into provisioned concurrency idle cost.** PC
  bills per GB-second of provisioned capacity regardless of invocations.
  Doubling memory doubles the PC idle bill. Right-size memory first,
  then size PC.

### Pre-flight: data gate — intro


Memory decisions are only as good as the underlying data. Pull these
metrics before any recommendation. Full CLI sequences are in
`references/lambda-memory-and-power-tuning.md`.

### Data-quality short-circuits

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `Duration` metric absent (function never invoked) | **NEED_MORE_INFO**. Verify trigger wiring; skip until invocations exist. |
| `Invocations` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant function." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `memory_used` (Lambda Insights) absent | Fall back to Power Tuning only; mark Memory recommendation MEDIUM confidence. |
| `InitDuration` absent | Cold-start analysis blocked; skip Step 3. |
| `cpu_total_time` / Duration < 0.5 | Function is I/O-bound — U-curve likely flat; cost minimum probably at low memory. |
| `cpu_total_time` / Duration > 0.8 | Function is CPU-bound — U-curve likely has step-function at 1769 MB. |
| Compute Optimizer enrollment `Inactive` | Proceed with CloudWatch + Power Tuning directly. |
| Compute Optimizer `lastRefreshTimestamp` > 30 days old | Stale finding. Re-run `get-lambda-function-recommendations`. |
| Function `State != Active` | Skip optimization; surface as BLOCKED. |

When CloudWatch and Compute Optimizer disagree, Power Tuning is the
tiebreaker — it measures the actual U-curve.

### Step 0: Non-obvious behaviours that change the recommendation


These operational gotchas route a recommendation away from the obvious
choice:

- **Memory and CPU are coupled at 1769 MB = 1 vCPU.** CPU-bound
  workloads see step-function duration improvement at this boundary.
  The cost minimum often lands at or just above 1769 MB for CPU-bound
  workloads.
- **The U-curve minimum is workload-specific.** Memory-bound functions
  may hit minimum cost at 3 GB; pure I/O functions may be cheapest at
  128 MB. Never assume; always measure via Power Tuning.
- **Power Tuning measures COST, not just speed.** Read the cost column,
  not just the duration column. The `cheapest` field is the cost
  minimum; the `fastest` field is the latency minimum.
- **ARM64 has a different memory-to-CPU ratio than x86_64.** After
  migrating architecture, re-run Power Tuning. The U-curve minimum
  shifts because Graviton2 vCPU allocation differs from x86_64 at the
  same memory setting.
- **SnapStart is Java-only and off by default.** SnapStart snapshots
  the init-phase memory and restores it in ~200 ms instead of re-running
  init. Eliminates 1-3 s of InitDuration. Does NOT change the per-
  invocation memory allocation — only the cold-start path.
- **EFS mounts add ~64 MB resident memory baseline.** A function with
  EFS mounted cannot run below ~192 MB without risk of OOM. Factor EFS
  overhead into the headroom calculation.
- **Container image functions have higher cold-start memory.** Image
  extraction during init allocates more memory than a zip deployment.
  Minimum recommended MemorySize for container-image functions: 256 MB.
- **Lambda Layers add init-time memory pressure.** Each layer is a
  separate zip extracted during init. Over-using layers (5+ layers)
  increases InitDuration and may push peak init memory above the
  allocation, causing cold-start OOM.
- **Environment variables are limited to 4 KB total.** Oversized env
  vars don't affect runtime memory but do affect init parse time and
  cold-start duration. Move large config to Parameter Store / Secrets
  Manager / AppConfig.
- **`/tmp` storage is independent of memory since 2022.** Allocate up
  to 10 GB via `--ephemeral-storage` without changing MemorySize. Bills
  separately at $0.0000000625/MB-second. Functions using memory as
  /tmp overflow should decouple via ephemeral storage.
- **Provisioned concurrency bills per GB-second of provisioned
  capacity.** A function at 2 GB with 10 PC executions pays 16x the
  idle bill of the same concurrency at 128 MB. Memory size cascades
  directly into PC cost.
- **Power Tuning invokes the function repeatedly.** Ensure the function
  is idempotent and downstream tolerates test load. Use
  `parallelInvocation: false` for non-idempotent functions.

### Step 1 — the U-curve math and finding the minimum (Power Tuning)

**The U-curve math:**
```
compute_cost = duration_seconds × memory_GB × $0.0000166667

Example: 128 MB at 5 s → $0.0000104/invocation
         512 MB at 1 s → $0.0000083/invocation (20% CHEAPER)
         2048 MB at 0.4 s → $0.0000133/invocation (WORSE)
```

**Finding the U-curve minimum: AWS Lambda Power Tuning.** Open-source
Step Functions tool that empirically measures the cost-duration curve.
Deploy via SAR; run an execution; read the `cheapest` and `fastest`
fields. Full deployment and execution CLI is in
`references/lambda-memory-and-power-tuning.md`.

### Step 1 — the cost-vs-latency tradeoff

**The cost-vs-latency tradeoff:** Power Tuning returns both `cheapest`
(cost-optimal) and `fastest` (latency-optimal). The two usually differ.
Always surface BOTH numbers in the recommendation block:

```text
Cost-optimal:    512 MB at 950 ms ($0.0000083/invocation)
Latency-optimal: 3008 MB at 410 ms ($0.0000205/invocation)
Current:         128 MB at 5000 ms ($0.0000104/invocation)
```

The operator chooses based on whether the priority is FinOps (cost) or
UX (latency). Never assume; always present both.

### Step 2 — pricing impact of memory on provisioned concurrency

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts, but charges for idle time. Memory size scales
the idle bill linearly.

**Pricing impact of memory on PC:**
```
PC idle cost = provisioned_concurrent_executions × memory_GB × $0.000015 × seconds_in_month

Example: 10 PC executions at 2048 MB:
  10 × 2.0 × $0.000015 × 2,592,000 = $777.60/month idle

Same concurrency at 512 MB (after Step 1 right-sizing):
  10 × 0.5 × $0.000015 × 2,592,000 = $194.40/month idle
  Saving: $583.20/month (75%) just from memory right-sizing
```

### Step 2 — right-sizing sequence

**Right-sizing sequence:** Always apply Step 1 (memory right-sizing)
BEFORE adjusting PC count. Memory reduction cascades into PC savings
without any change to the PC configuration itself.

### Step 4: EFS, container image, and Layers memory overhead


These deployment choices add resident memory overhead that affects the
minimum viable MemorySize.

**EFS overhead:**
- EFS mounts add ~64 MB resident memory baseline.
- A function with EFS cannot run below ~192 MB without OOM risk.
- If EFS is used for infrequent large-file access, consider removing
  the mount and using S3 pre-signed URLs instead.

**Container image overhead:**
- Container image functions have higher cold-start memory than zip
  deployments due to image extraction during init.
- Minimum recommended MemorySize: 256 MB.
- Optimize the image: use multi-stage builds, distroless or alpine
  base images, remove build tools from the runtime image.

**Lambda Layers overhead:**
- Each layer is a separate zip extracted during init.
- 1-3 layers: negligible overhead.
- 5+ layers: measurable InitDuration increase and init memory pressure.
- Recommendation: consolidate layers; move shared code to a runtime
  package manager (pip, npm) instead of layers where possible.

### Step 6 — ARM64 vs x86_64 memory-to-CPU key difference

**Key difference:**
```
x86_64: 1769 MB = 1 vCPU
arm64:  Similar coupling but Graviton2 cores are ~20% faster per vCPU
        for many workloads. The U-curve minimum may be at a LOWER
        memory setting on arm64 than x86_64 for the same workload.
```

### Step 6 — architecture + memory combined recommendation

**Architecture + memory combined recommendation:**
- Migrate to arm64 (20% compute discount).
- Re-run Power Tuning on arm64.
- Set MemorySize to the arm64 U-curve minimum.
- The combined saving is multiplicative, not additive.

### Step 7 — impact estimation formulas

```
current_monthly_cost =
  (monthly_invocations × avg_duration_s × current_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)
  + (pc_executions × current_memory_GB × $0.000015 × seconds_in_month)

projected_monthly_cost =
  (monthly_invocations × projected_duration_s × projected_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)
  + (pc_executions × projected_memory_GB × $0.000015 × seconds_in_month)

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly invocation count, average duration at
current and projected memory (from Power Tuning), memory in GB, PC
configuration, pricing region.

### Recent AWS features (2024-2026)


- **Lambda SnapStart expansion (2024-2025):** Originally Java-only;
  expanding to additional runtimes. Check current support matrix.
- **Lambda ARM64 (Graviton2) GA:** All major runtimes support arm64.
  ~20% cheaper compute; different memory-to-CPU ratio — re-tune after
  migration.
- **AWS Lambda Power Tuning:** De facto standard for empirical memory
  tuning. Supports parallel invocation, custom payload, visualization
  URL output, Pareto frontier visualization.
- **Lambda Insights:** Provides `memory_used`, `cpu_total_time`,
  `InitDuration`, and other runtime metrics beyond the default AWS/Lambda
  namespace. Enable via extension Layer. Required for memory-utilization
  analysis.
- **Ephemeral storage (`/tmp`) independent configuration (2022+):**
  Decouple /tmp from MemorySize via `--ephemeral-storage` up to 10 GB.
  Bills separately at $0.0000000625/MB-second.
- **Provisioned Concurrency autoscaling (2024):** Application Auto
  Scaling supports provisioned concurrency on Lambda aliases via target-
  tracking on `ProvisionedConcurrencyUtilization`.
