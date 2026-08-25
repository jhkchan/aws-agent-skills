---
name: lambda-cold-start-optimizer
description: 'Optimises AWS Lambda cold-start latency across seven dimensions: memory allocation vs initialization time (Power Tuning latency-optimal memory), provisioned concurrency (allocation sizing and autoscaling for latency-critical paths), SnapStart (Java only — init snapshot eliminates 1-3 s of init), init phase optimization (lazy initialization, global-scope connection pooling), VPC cold start penalty (hyperplane ENI elimination since 2019), runtime selection (compiled vs interpreted, ARM64 Graviton), and deployment package size reduction (Layers, Proguarded JARs, slim ZIPs). Covers EFS mount latency, runtime deprecation impact, X-Ray overhead, and CloudWatch Lambda Insights init-duration telemetry. Emits OPTIMIZED when cold-start p95 < SLO and all init-phase levers applied, or FURTHER_OPTIMIZATION_AVAILABLE with the highest-leverage remaining lever.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Lambda Insights traces. Live-account optimization uses aws lambda list-functions, aws lambda get-function-configuration, aws lambda get-function-event-invoke-config, aws lambda list-provisioned-concurrency-configs, aws lambda get-event-source-mapping, aws cloudwatch get-metric-statistics (Duration, InitDuration, Invocations...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Reducing Lambda cold-start latency, sizing provisioned concurrency for latency-sensitive APIs, enabling SnapStart for Java functions, optimizing the init phase (lazy initialization, connection reuse), evaluating VPC cold-start impact, selecting a runtime for fast startup, trimming deployment package size, diagnosing EFS mount latency, assessing X-Ray tracing overhead, or reading Lambda Insights init-duration telemetry.
  when_not_to_use: Lambda cost optimization without a latency focus (use lambda-cost-optimizer), Lambda functional debugging (invocation errors, timeouts, configuration bugs — use the Lambda troubleshooter), or API Gateway latency optimization (use the API Gateway optimizer). This skill targets cold-start and init-phase latency, not dollar cost or functional correctness.
  activation_triggers: optimise Lambda cold start, Lambda init duration, Lambda InitDuration, Lambda provisioned concurrency, Lambda SnapStart Java, Lambda lazy initialization, Lambda connection reuse, Lambda VPC cold start, Lambda hyperplane ENI, Lambda runtime selection, Lambda ARM64 Graviton, Lambda deployment package size, Lambda Layers cold start, Lambda Proguard, Lambda EFS mount latency, Lambda X-Ray overhead, Lambda Insights, Lambda runtime deprecation, reduce Lambda latency, Lambda p95 latency
  invocation_schema: 'Input: either (a) a function identifier + live-account context, (b) a Lambda Insights metrics export (Duration, InitDuration, Invocations, ColdStarts), OR (c) function metadata (Runtime, MemorySize, Architecture, VpcConfig, SnapStart config, ProvisionedConcurrency config, TracingConfig, package size). Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_LATENCY_IMPACT/MIGRATION_STEPS block per function, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline classification):\nFunctionName: order-api-prod\nRuntime: java21\nMemorySize: 512 MB\nArchitecture: x86_64\nRegion: us-east-1\nSnapStart: NOT_ENABLED\nVpcConfig: subnet-aaa, subnet-bbb (VPC attached)\nTracingConfig: Active\nPackage size: 52 MB (fat JAR, untrimmed)\nProvisionedConcurrency: 0\nMetrics (last 30 days):\n  - Duration avg: 1800 ms, p95: 2400 ms\n  - InitDuration avg: 3200 ms (cold start), p95: 4100 ms\n  - Invocations: 8,000,000/month\n  - ColdStarts: ~120,000/month (1.5% of invocations)\n  - Errors: 0\nSLO: p95 end-to-end < 1000 ms\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_LATENCY_IMPACT, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, cold start, initialization time, InitDuration, provisioned concurrency, SnapStart, Java, power tuning, memory allocation, lazy initialization, connection pooling, VPC, hyperplane ENI, runtime selection, ARM64, Graviton, deployment package, Lambda Layers, Proguard, EFS mount, X-Ray overhead, Lambda Insights, runtime deprecation, latency optimization
  tags: lambda, compute, serverless, performance, cold-start, latency, snapstart, provisioned-concurrency
---

# Lambda Cold Start Optimizer

## What this skill does

Translates a Lambda function's cold-start posture into a concrete
latency-optimization recommendation with a millisecond-denominated
estimated latency impact. The verdict is the highest-leverage action
across seven dimensions — memory allocation, provisioned concurrency,
SnapStart, init phase optimization, VPC cold start, runtime selection,
and deployment package size — applied in priority order. Always pairs
the recommendation with exact CLI commands (or Power Tuning invocation).

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cold-start formula | First read |
| Mindset | Why SnapStart + provisioned concurrency are the heavy levers | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a function |
| Pre-flight data gate | CloudWatch metrics, Lambda Insights | Before any recommendation |
| Step 0 non-obvious behaviours | VPC hyperplane ENI, SnapStart Java-only, X-Ray overhead | Edge cases |
| Step 1 Memory allocation | Power Tuning for latency-optimal memory | The CPU-bound dimension |
| Step 2 Provisioned concurrency | Allocation, scheduling, autoscaling | Latency-sensitive APIs |
| Step 3 SnapStart (Java) | Init snapshot, versioned alias requirement | Java functions |
| Step 4 Init phase optimization | Lazy init, connection pooling, global scope | All runtimes |
| Step 5 VPC cold start | Hyperplane ENI elimination, when VPC still hurts | VPC-attached functions |
| Step 6 Runtime selection | Compiled vs interpreted, ARM64 Graviton | Architecture decisions |
| Step 7 Package size | Layers, Proguarded JARs, slim ZIPs | Large deployment packages |
| Step 8 Impact estimation | Latency math and worked examples | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, version publish, alias | Before any apply CLI |

## Quick start

- **SnapStart is the heaviest single lever for Java.** It eliminates
  the entire init phase (1-3 s for typical Spring/Java workloads) by
  restoring a pre-initialized snapshot. One-line config change, no code
  modification for most workloads. Available ONLY for Java (java21 and
  later supported runtimes).
- **Provisioned concurrency eliminates cold starts entirely — at a
  price.** It pre-initializes execution environments and keeps them
  warm. Use it ONLY for latency-critical paths (sync APIs, interactive
  endpoints) where a cold start violates the SLO. It charges for idle
  time; the cost-vs-latency trade-off must be explicit.
- **VPC cold start is largely solved (since 2019).** Hyperplane ENIs
  eliminated the 5-10 s VPC cold-start penalty. VPC-attached functions
  now see <100 ms overhead on cold starts. If a function still shows
  high VPC cold-start latency, check for ENI throttling or stale
  configuration, not the VPC itself.
- **The init phase is where most cold-start time lives.** Move SDK
  clients, DB connections, and heavy imports to global scope (outside
  the handler). Lambda reuses execution environments across invocations;
  global-scope init runs once per warm container, not per invocation.

## Mindset

Cold-start optimization is a latency-vs-cost decision, not a pure
utilization exercise. The goal is the memory/concurrency/runtime/package
configuration that minimizes cold-start InitDuration AND steady-state
Duration while preserving the cost envelope — not the absolute minimum
init time at any cost.

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

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Runtime = Java AND SnapStart NOT enabled AND InitDuration p95 > 1 s | **FURTHER_OPTIMIZATION_AVAILABLE** (SnapStart) | Step 3 — enable SnapStart, publish version |
| Latency-sensitive API (sync) AND cold-start p95 > SLO AND no provisioned concurrency | **FURTHER_OPTIMIZATION_AVAILABLE** (provisioned concurrency) | Step 2 — add provisioned concurrency sized to baseline |
| Memory < 1769 MB AND Duration scales with memory (CPU-bound) AND InitDuration > 500 ms | **FURTHER_OPTIMIZATION_AVAILABLE** (memory) | Step 1 — increase memory to Power Tuning latency optimum |
| SDK clients / DB connections initialized inside handler (per-invocation) | **FURTHER_OPTIMIZATION_AVAILABLE** (init phase) | Step 4 — move to global scope |
| Package size > 20 MB AND runtime = Java AND no Proguard/SnapStart | **FURTHER_OPTIMIZATION_AVAILABLE** (package) | Step 7 — trim fat JAR, enable Proguard |
| Architecture = x86_64 AND runtime is ARM-compatible AND latency-sensitive | **FURTHER_OPTIMIZATION_AVAILABLE** (architecture) | Step 6 — migrate to arm64 for better price-performance |
| Runtime is deprecated (e.g., nodejs16, java8) AND function is latency-sensitive | **FURTHER_OPTIMIZATION_AVAILABLE** (runtime) | Step 6 — upgrade to current runtime |
| TracingConfig = Active AND X-Ray overhead > 50 ms per invocation | **FURTHER_OPTIMIZATION_AVAILABLE** (tracing) | Step 0 — evaluate sampling rate |
| All dimensions verified AND cold-start p95 < SLO AND SnapStart enabled (Java) | **OPTIMIZED** | Emit post-state verification |
| InitDuration metrics absent (Lambda Insights not enabled) | **FURTHER_OPTIMIZATION_AVAILABLE** (observability) | Enable Lambda Insights for init-duration visibility |
| Observation window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Cold-start optimization decisions require init-duration telemetry. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/cold-start-metrics-and-power-tuning.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Function configuration: `aws lambda get-function-configuration`
2. Duration + InitDuration (14-30 day window): `aws cloudwatch get-metric-statistics` with Lambda Insights
3. Cold-start count: Lambda Insights `coldStarts` metric or `Invocations` vs unique container IDs
4. SnapStart config: `aws lambda get-function-configuration --query 'SnapStart'`
5. Provisioned concurrency configs: `aws lambda list-provisioned-concurrency-configs`
6. VPC config: `aws lambda get-function-configuration --query 'VpcConfig'`
7. Tracing config: `aws lambda get-function-configuration --query 'TracingConfig'`
8. Package size: `aws lambda get-function-configuration --query 'CodeSize'`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `InitDuration` absent (Lambda Insights not enabled) | Enable Lambda Insights. Fall back to `Duration` spikes; mark confidence MEDIUM. |
| `Invocations` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant function." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| Cold-start count absent | Estimate from ConcurrentExecutions + traffic-pattern analysis. Mark confidence MEDIUM. |
| Function `State != Active` | Skip optimization; surface as BLOCKED. |
| Runtime = java8 (legacy) | SnapStart not supported. Recommend runtime upgrade first (Step 6). |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

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

### Step 1: Memory allocation vs initialization time

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

**Decision gate after Power Tuning (latency mode):**

| Power Tuning `fastest` vs current MemorySize | Verdict | Action |
|---|---|---|
| `fastest` at higher memory AND InitDuration reduction > 500 ms | **FURTHER_OPTIMIZATION_AVAILABLE** (memory upsize) | Set MemorySize to `fastest`. Verify cost envelope. |
| `fastest` == current | No memory finding | Proceed to other dimensions. |
| `fastest` at lower memory (rare for cold start) | No finding — current is already latency-optimal | Proceed. |

**Cost-latency trade-off note:** Higher memory increases per-invocation
cost. For cold-start optimization, accept the cost increase ONLY if the
latency reduction is SLO-critical. If the function is also cost-
sensitive, evaluate provisioned concurrency as an alternative (Step 2).

### Step 2: Provisioned concurrency (allocation, scheduling, autoscaling)

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts entirely. It is the most powerful cold-start
mitigation but charges for idle time.

**When provisioned concurrency is justified:**

| Condition | Recommendation |
|---|---|
| Sync API (API Gateway, ALB, Function URL) AND cold-start p95 > SLO | Provisioned concurrency sized to p50-p75 of ConcurrentExecutions |
| Interactive endpoint (user-facing, <1 s SLO) AND cold starts visible | Provisioned concurrency with autoscaling |
| Async event-driven (SQS, Kinesis, EventBridge) | Do NOT use provisioned concurrency. Cold starts are absorbed by the queue/stream. |
| Batch job (rare invocations) | Do NOT use provisioned concurrency. Use on-demand. |

**Sizing provisioned concurrency:**
```bash
# Target: p50-p75 of observed ConcurrentExecutions
aws lambda put-provisioned-concurrency-config \
  --function-name <name> --qualifier <alias> \
  --provisioned-concurrent-executions <p50-p75 value>

# Autoscaling via Application Auto Scaling
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id function:<name>:<alias> \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity <min> --max-capacity <max>
```

**Scheduling note:** Provisioned concurrency takes 1-2 minutes to
initialize after configuration. For predictable traffic spikes (e.g.,
morning rush), schedule capacity increases 5-10 minutes in advance via
Application Auto Scaling scheduled actions.

### Step 3: SnapStart (Java only — initialization snapshot)

SnapStart is the single highest-impact optimization for Java Lambda
functions. It takes a snapshot of the initialized JVM and restores it on
cold start, eliminating 1-3 s of JVM + framework init.

**Eligibility:**
- Runtime: java21 (or later supported Java runtimes). SnapStart is
  supported on Corretto distributions.
- NOT available for: Node.js, Python, Go, Ruby, .NET.
- NOT available for: container-image functions (zip-only).

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

### Step 4: Init phase optimization (lazy initialization, connection pooling)

Regardless of runtime, the init phase is where most cold-start time
lives. Move heavy initialization OUTSIDE the handler into global scope,
so it runs once per warm container, not per invocation.

**The global-scope pattern (Python):**
```python
# BAD — per-invocation init
def handler(event, context):
    client = boto3.client('dynamodb')  # Re-created every invocation
    db = psycopg2.connect(...)          # 200-500 ms TLS overhead every time

# GOOD — global-scope init, reused across invocations
_DDB = boto3.client('dynamodb')  # Created once per container
_db = None
def _get_db():
    global _db
    if _db is None:
        _db = psycopg2.connect(...)
    return _db
def handler(event, context):
    db = _get_db()
```

**Runtime-specific connection reuse patterns:**

| Runtime | DB library | Pattern |
|---|---|---|
| Node.js | pg, mysql2 | `const pool = new Pool({...})` at module scope |
| Python | psycopg2, pymysql | Global connection with lazy-init + validity check |
| Java | HikariCP | `DataSource` as static field |
| Go | database/sql | `sql.Open()` at package level |

**Init-phase checklist:**

| Symptom | Fix |
|---|---|
| InitDuration > 500 ms (non-Java) | Move SDK clients, DB connections to global scope |
| InitDuration > 1 s (Java, no SnapStart) | Enable SnapStart (Step 3) |
| InitDuration spikes after deploy | Check for new heavy dependencies in import chain |
| DB connection per invocation | Use global connection pool with validity check |
| HTTP client per invocation | Use global HTTP client with keep-alive |

### Step 5: VPC cold start penalty (hyperplane ENI elimination)

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

**VPC cold-start diagnostic CLI:**
```bash
aws ec2 describe-network-interfaces \
  --filters Name=description,Values="AWS Lambda VPC ENI*" \
  --query 'NetworkInterfaces[*].{Id:NetworkInterfaceId,Subnet:SubnetId,Status:Status}' \
  --output table

aws ec2 describe-subnets --subnet-ids <subnet-ids-from-VpcConfig> \
  --query 'Subnets[*].{SubnetId:SubnetId,AvailableIPs:AvailableIpAddressCount,CIDR:CidrBlock}' \
  --output table
```

**Recommendation:** If VPC cold-start latency is <100 ms (hyperplane
ENI working), VPC is NOT the bottleneck. If >500 ms, investigate
ENI/subnet/SG issues.

### Step 6: Runtime selection (compiled vs interpreted, ARM64 Graviton)

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

**Recommendation framework:**

| Current runtime | Recommendation |
|---|---|
| Java (no SnapStart) | Enable SnapStart (Step 3). If still slow, evaluate migration. |
| Java (SnapStart, still slow) | Init phase optimization (Step 4) + memory tuning (Step 1). |
| nodejs16 (deprecated) | Upgrade to nodejs20+. Deprecated runtimes miss optimizations. |
| java8 (deprecated) | Upgrade to java21. java8 does not support SnapStart. |
| python3.7 (deprecated) | Upgrade to python3.12. |

**ARM64 (Graviton):** ~20% better price-performance AND often faster
init for interpreted runtimes. Verify ARM compatibility for compiled
runtimes before migration.

### Step 7: Deployment package size reduction

Package size correlates with init time. Lambda downloads, extracts, and
loads the deployment package on every cold start. Larger packages mean
longer init.

**Package size thresholds:**

| Package size | Impact | Recommendation |
|---|---|---|
| <5 MB | Negligible init overhead | No action |
| 5-20 MB | Moderate init overhead | Evaluate dependency trimming |
| 20-50 MB | Significant init overhead (100-500 ms) | Trim aggressively |
| >50 MB | Severe init overhead (500+ ms) | Refactor: Proguard, Layers, or container image |

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

### Step 8: Impact estimation

Compute the latency impact for each recommendation:

```
current_cold_start_p95 = InitDuration_p95 + Duration_p95
projected_cold_start_p95 = projected_InitDuration_p95 + projected_Duration_p95
latency_reduction_ms = current_cold_start_p95 - projected_cold_start_p95
latency_reduction_pct = (latency_reduction_ms / current_cold_start_p95) × 100
```

Always state assumptions: cold-start frequency (invocations per day
that are cold starts), InitDuration at current and projected memory
(from Power Tuning), SLO threshold, and whether SnapStart is enabled.

## Configuration dependency graph

```
                     ┌─────────────────┐
                     │ Runtime = Java? │
                     └────────┬────────┘
                              │
                   ┌──────────┴──────────┐
                   YES                   NO
                   │                     │
            ┌──────▼──────┐      ┌───────▼───────┐
            │ Enable      │      │ Init phase    │
            │ SnapStart   │      │ optimization  │
            │ (Step 3)    │      │ (Step 4)      │
            └──────┬──────┘      └───────┬───────┘
                   │                     │
                   └──────────┬──────────┘
                              │
                     ┌────────▼────────┐
                     │ Cold-start p95  │
                     │ > SLO?          │
                     └────────┬────────┘
                              │
                   ┌──────────┴──────────┐
                   YES                   NO
                   │                     │
            ┌──────▼──────┐      ┌───────▼───────┐
            │ Add prov.   │      │ Check memory  │
            │ concurrency │      │ + package +   │
            │ (Step 2)    │      │ runtime (1,7) │
            └─────────────┘      └───────────────┘
```

Decision order: SnapStart (if Java) → init phase optimization →
provisioned concurrency (if latency-critical) → memory tuning →
runtime/package optimization.

## Output format

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <memory> MB, <runtime>, <architecture>, <SnapStart>, <provisioned concurrency>, <package size>
  Proposed: <memory> MB, <runtime>, <architecture>, <SnapStart>, <provisioned concurrency>, <package size>
  Dimensions changed: <memory | provisioned_concurrency | snapstart | init_phase | vpc | runtime | package>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: <ms> (InitDuration: <ms> + Duration: <ms>)
  Projected cold-start p95: <ms>
  Latency reduction: <ms> (<pct>%)
  SLO: p95 < <ms>
  Cold-start frequency: ~<count>/day (<pct>% of invocations)
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <function-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Self-check EVERY emitted block
against these rules before returning the response. Do NOT substitute
markdown headings, camelCase, or bold variants for the literal labels.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Latency reduction: 0 ms`.** If every dimension nets zero latency
   delta, the verdict MUST be `OPTIMIZED`. A cost-only improvement is
   surfaced in REASON as a cost note, NOT as latency savings.

2. **NEVER show latency math that does not balance.**
   `Current cold-start p95 − Projected cold-start p95` MUST equal
   `Latency reduction`, rounded to whole milliseconds.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend SnapStart for non-Java runtimes.** SnapStart is
   Java-only. Recommending it for Node.js, Python, or Go is a
   misclassification.

5. **NEVER recommend SnapStart without warning about the versioned-alias
   requirement.** SnapStart requires published versions; `$LATEST` does
   not support it. The MIGRATION_STEPS MUST include `publish-version`.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER attribute cold-start latency to VPC without verifying ENI
   health.** Since 2019, hyperplane ENIs reduced VPC cold start to
   <100 ms. If VPC latency is diagnosed, cite the specific ENI/subnet/SG
   evidence.

8. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Java 21 function with InitDuration p95 of 3200 ms and SnapStart
  NOT enabled. Enabling SnapStart eliminates 90% of init phase (snapshot
  restore drops InitDuration from 3200 ms to ~200 ms). Function is a
  sync API with cold-start p95 exceeding the 1000 ms SLO.
RECOMMENDATION:
  Current: 512 MB, java21, x86_64, SnapStart OFF, no PC, 52 MB
  Proposed: 512 MB, java21, x86_64, SnapStart ON, no PC, 52 MB
  Dimensions changed: snapstart (Step 3)
  Dimensions checked: memory ✓  provisioned_concurrency ✓  snapstart → (enable)
    init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — SnapStart supported on java21; no container-image.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 5000 ms (InitDuration: 3200 ms + Duration: 1800 ms)
  Projected cold-start p95: 2000 ms (InitDuration: 200 ms + Duration: 1800 ms)
  Latency reduction: 3000 ms (60%)
  SLO: p95 < 1000 ms — pair with provisioned concurrency for full SLO.
MIGRATION_STEPS:
  1. Enable SnapStart:
     aws lambda update-function-configuration --function-name order-api-prod
       --snap-start '{"ApplyOn":"PublishedVersions"}'
  2. Publish a version: aws lambda publish-version --function-name order-api-prod
  3. Update alias: aws lambda update-alias --function-name order-api-prod
       --name prod --function-version <new-version>
  4. Verify: aws lambda get-function-configuration --function-name order-api-prod
       --qualifier <new-version> --query 'SnapStart.OptimizationStatus'
  5. Monitor InitDuration for 7 days. If SLO unmet, add provisioned concurrency.
CONFIRM: About to enable SnapStart on order-api-prod (publish version,
  update alias). Projected cold-start reduction: 3000 ms (60%). Proceed?
```

**Self-check before emit:**
- [ ] `Current cold-start p95 − Projected cold-start p95 == Latency reduction`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] SnapStart recommendation includes `publish-version` step?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, latency-reducing recommendation. |
| `OPTIMIZED` | All dimensions pass (SnapStart enabled for Java, init optimized, cold-start p95 < SLO, no remaining levers). |
| `NEED_MORE_INFO` | Data gate failed: InitDuration metrics absent, window < 14 days, or Lambda Insights not enabled with no fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: function State != Active, IAM denies lambda:GetFunction, runtime deprecated and blocks all optimizations. |

**Zero-latency-impact rule:** If latency reduction == 0 ms for every
dimension, verdict MUST be `OPTIMIZED`, never
`FURTHER_OPTIMIZATION_AVAILABLE`. Exception: a cost-only improvement
(without latency change) is surfaced in REASON as a cost note, not as
latency savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend SnapStart for non-Java runtimes.** SnapStart is
   Java-only (java21+). Recommending it for Node.js, Python, Go, or
   Ruby is a fundamental misclassification.

2. **NEVER enable provisioned concurrency without verifying that the
   function is latency-critical (sync API, interactive endpoint).**
   Provisioned concurrency for async/event-driven workloads is pure
   waste — cold starts are absorbed by the queue or stream.

3. **NEVER attribute cold-start latency to VPC without verifying ENI
   health.** Since 2019, hyperplane ENIs reduced VPC cold start to
   <100 ms. Diagnosing "VPC cold start" without checking ENI/subnet/SG
   is a false positive.

4. **NEVER recommend a memory increase for cold-start optimization
   without citing Power Tuning latency data.** Memory increases cost;
   the latency improvement must be measured, not assumed.

5. **NEVER enable SnapStart without warning about the versioned-alias
   requirement and network-connection reset.** SnapStart requires
   published versions and resets TCP connections on restore. Missing
   these caveats causes production failures.

Extended anti-patterns in `references/error-handling-and-edge-cases.md`.

## Expert heuristic

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

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval.
- **Publish a version before enabling SnapStart.** SnapStart applies to
  published versions, not `$LATEST`.
- **Test SnapStart before cutover.** Network connections reset on
  restore; verify DB reconnection logic.
- **Verify provisioned concurrency cost envelope.** Idle charges must be
  justified by the latency SLO.
- **Test memory changes via staging alias.** Higher memory increases
  cost; verify latency improvement justifies.
- **SnapStart + DB connections.** Ensure connection validity checks
  (lazy reconnect) are in place.
- **Provisioned concurrency removal causes cold starts.** Verify SLO
  tolerates cold starts.
- **Power Tuning invokes the function.** Ensure idempotency.
- **Bulk-operation limit:** 5 functions per batch, sorted by estimated
  latency impact.

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

## References

- `references/cold-start-metrics-and-power-tuning.md` — Power Tuning
  deployment (latency mode), Lambda Insights metrics, memory-to-CPU
  mapping, SnapStart CLI sequences, ARM64 matrix, package thresholds.
- `references/worked-examples.md` — SnapStart enablement, provisioned
  concurrency sizing, init phase refactor, memory tuning, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough.

## Domain

AWS CloudOps / Lambda Serverless Cold-Start Latency Optimization.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-snapstart.html
- **Lambda provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
- **Lambda VPC networking** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html
- **Lambda memory configuration** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- **Lambda runtime deprecation** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- **CloudWatch Lambda Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights.html
- **AWS Lambda Power Tuning (OSS)** — https://github.com/alexcasalboni/aws-lambda-power-tuning
- **AWS CLI Lambda reference** — https://docs.aws.amazon.com/cli/latest/reference/lambda/
- **Well-Architected — Performance Efficiency** — https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html
