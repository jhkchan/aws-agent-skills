# Advanced patterns — lambda-cost-optimizer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Mindset — four principles

Four principles guide every recommendation:

- **The cost curve is U-shaped.** As memory increases, duration usually
  drops faster than the per-GB-second rate rises — up to an inflection
  point. The optimal memory is workload-specific; Power Tuning measures
  it empirically.
- **Provisioned concurrency is an insurance premium, not a discount.**
  It charges for idle time. Cost-justified ONLY when traffic is
  consistent AND cold-start latency is customer-visible.
- **Invocation frequency is the multiplier.** Rank candidates by
  invocation count × duration before deep-diving into tuning.
- **Architecture and placement are cross-cutting savings.** ARM64
  delivers ~20% discount. Workloads >15 minutes must move to Fargate.
  Orchestration chains (10+ functions) cost more than a single Step
  Functions state machine.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Memory and CPU are coupled at 1769 MB = 1 vCPU.** CPU-bound workloads
  see step-function duration improvement at this boundary.
- **The U-curve minimum is workload-specific.** Memory-bound functions may
  hit minimum cost at 3 GB; pure I/O functions may be cheapest at 128 MB.
  Never assume; always measure via Power Tuning.
- **Power Tuning measures COST, not just speed.** Read the cost column,
  not just the duration column.
- **SnapStart is Java-only and off by default.** Eliminates 1-3 s of init
  time. One-line config change, no code modification for most workloads.
- **ESM default batch size is conservative (10).** Increasing to 100-10000
  reduces invocation count by 10-1000x. Pair with
  `MaximumBatchingWindowInSeconds`.
- **MaximumBatchingWindowInSeconds defaults to 0.** Setting to 1-5 s
  reduces invocation count but adds latency.
- **Lambda Layers can INCREASE cold start if over-used.** Each Layer is a
  separate .zip; extraction overhead slows init.
- **ARM64 is ~20% cheaper AND often faster.** Migration is one-line for
  interpreted runtimes; compiled runtimes may need ARM build artifacts.
- **Lambda's 15-minute timeout is a hard ceiling.** Workloads exceeding
  it MUST be migrated to Fargate.
- **Provisioned concurrency charges even with zero invocations.** A
  function at 1 GB with 10 concurrent executions, no traffic: $394/month
  idle. This is the #1 provisioned-concurrency cost trap.
- **Step Functions Standard charges per state transition.** For
  orchestration-heavy chains, evaluate Express workflow (per-invocation)
  vs Standard (per-state-transition).
- **The request fee at scale is non-trivial.** At 1B invocations/month,
  the request fee alone is $200/month. Batching via ESM is the only lever.
- **Power Tuning itself costs money — each execution invokes the target
  function ~50-200 times across 5-10 memory settings.** The Step
  Functions state machine runs in Express mode and costs ~$0.02 per
  tuning run in Step Functions charges, plus the Lambda invocation
  costs for the test calls (typically $0.01-$0.05 depending on
  function duration and memory). Total cost per Power Tuning run:
  $0.03-$0.07. This is negligible for a one-time tuning sweep but
  matters at scale: tuning 500 functions costs $15-$35. Expert rules:
  (1) batch-tune only the top 20% of functions by invocation count —
  they account for 80%+ of spend; (2) re-tune quarterly or after
  code changes, not weekly; (3) use the Power Tuning `totalPayload`
  parameter to pass realistic test payloads that match production
  input — synthetic payloads understate CPU-bound duration and
  overstate I/O-bound duration.
- **SnapStart increases memory usage by capturing the full JVM (or
  runtime) heap snapshot.** The snapshot is restored on cold start
  instead of re-initializing the runtime. The snapshot size (Java:
  200-800 MB depending on loaded classes) counts toward the
  function's memory allocation. A function at 2048 MB with a 600 MB
  snapshot has 1448 MB available for execution. If the function's
  peak memory usage + snapshot size exceeds the configured memory,
  you get OOM kills that did NOT occur before SnapStart was enabled.
  Expert rule: after enabling SnapStart, re-run Power Tuning — the
  optimal memory point often shifts UPWARD because the snapshot
  consumes headroom that was previously available for execution.
- **Each Lambda Layer adds ~50-200ms of cold start init time for .zip
  extraction, independent of layer content size.** The init cost is
  per-layer (extraction + mount), not per-byte. A function with 5
  layers of 1 MB each pays 5x the extraction overhead of a function
  with 1 layer of 5 MB. Expert rules: (1) consolidate related
  dependencies into a single layer rather than splitting by
  package — fewer layers = fewer extraction cycles; (2) prefer a
  fat deployment package over layers for single-function use;
  (3) use layers ONLY when the same dependency is shared across
  3+ functions (the per-function extraction overhead is offset by
  reduced package upload/deploy time); (4) monitor InitDuration
  before and after adding a layer — if it increases by > 200ms,
  flatten the layers.

## Step 3 deep dive: code-level optimizations

**Code-level optimizations:**
- **Lazy initialization:** Move SDK clients, DB connections to global scope
  (outside handler). Lambda reuses execution environments across invocations.
- **Connection reuse:** Instantiate HTTP clients and DB drivers globally.
  New connections per invocation add 50-500 ms TLS overhead.
- **Package reduction:** Remove unused deps. Use `pip install --no-deps`.
- **SnapStart (Java):** `aws lambda update-function-configuration --function-name <name> --snap-start '{"ApplyOn":"PublishedVersions"}'` then `publish-version`.

## Step 4 deep dive: batch tuning example, caveat, SQS long polling

Example: 1M messages/hour, batch 10 → 1000: invocation count drops 99%.
Caveat: larger batches increase per-invocation duration. Net saving is
positive when duration scales sub-linearly (I/O-bound, amortized setup).

**SQS long polling:** Ensure `ReceiveMessageWaitTimeSeconds` >= 1 s to
reduce empty ReceiveMessage calls.

## Step 5 deep dive: ARM64 (Graviton2) migration CLI

**ARM64 (Graviton2) migration:** ~20% cheaper per GB-second. Low-risk for
interpreted runtimes (Node, Python, Ruby); moderate-risk for compiled
runtimes (Java JNI, .NET native libs, Go CGO).

```bash
aws lambda update-function-configuration --function-name <name> --architectures arm64
aws lambda publish-version --function-name <name>
```

## Step 5 deep dive: Step Functions migration pricing

**Step Functions migration:** Standard charges per state transition
($0.025/1,000); Express charges per invocation + duration. Evaluate which
is cheaper for the workload volume.

## Recent AWS features (2024-2026)

- **Lambda SnapStart expansion (2024-2025):** Originally Java-only, now
  expanding to additional runtimes. Check current support matrix.
- **Lambda ARM64 (Graviton2) GA:** All major runtimes support arm64.
  ~20% cheaper compute and often better price-performance.
- **AWS Lambda Power Tuning:** De facto standard for empirical memory
  tuning. Deployed via SAR. Supports parallel invocation, custom payload,
  visualization URL output.
- **Lambda Insights:** Provides `memory_used`, `cpu_total_time`, and other
  runtime metrics beyond the default AWS/Lambda namespace. Enable via
  extension Layer. Required for memory-utilization analysis.
- **Provisioned Concurrency autoscaling (2024):** Application Auto Scaling
  supports provisioned concurrency on Lambda aliases via target-tracking
  on `ProvisionedConcurrencyUtilization`.
- **Event Source Mapping enhancements (2024-2025):** `MaximumBatchingWindowInSeconds`
  tunable (1-300 s). `FunctionResponseTypes: ["ReportBatchItemFailures"]`
  for partial-batch failure reporting on SQS.
- **Lambda Function URLs (2024):** Dedicated HTTP(S) endpoints without
  API Gateway cost.
- **Step Functions Express Workflow pricing refinement (2024):** Per-
  invocation + per-GB-second pricing, distinct from Standard's per-state-
  transition pricing.

