# Error Handling, Edge Cases, and Decision Trees — Lambda Cost Optimizer

Detailed error-handling tables, operational edge cases, the memory
optimization decision tree, and remediation guidance. Loaded on demand
when specific failure modes or edge cases need resolution.

## CLI and data-source failure handling

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for Duration | `len(Datapoints) == 0` | Verdict: `NEED_MORE_INFO`. The function may be dormant, or IAM denies cloudwatch:GetMetricStatistics. |
| `memory_used` (Lambda Insights) absent | `list-metrics` returns no match for LambdaInsights namespace | Lambda Insights extension not installed. Fall back to Power Tuning only; mark Memory recommendation MEDIUM confidence. |
| Datapoints present but `SampleCount < 168` (less than 7 days) | `len(Datapoints) < window_days * 24 * 0.7` | Verdict: `NEED_MORE_INFO`. Observation window not representative. |
| CloudWatch API throttling (`Throttling` error) | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). Fall back to 7-day window, flag LOW-confidence. |

### Compute Optimizer failures

| Failure mode | Detection | Handling |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `"status": "Inactive"` | Enable: `aws compute-optimizer update-enrollment-status --status Active`. Until enabled, proceed with CloudWatch + Power Tuning. |
| Empty `lambdaFunctionRecommendations` | `len(lambdaFunctionRecommendations) == 0` | Function is Optimal or not yet analyzed. Cross-check `lastRefreshTimestamp`; if > 30 days, treat as stale. |
| `AccessDeniedException` for `compute-optimizer:*` | API error | Add `compute-optimizer:GetLambdaFunctionRecommendations`. Proceed without cross-check; surface the gap. |

### Lambda API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-function-configuration` returns `ResourceNotFoundException` | API error | Function does not exist in this region. Skip entirely. |
| `update-function-configuration` fails with `ResourceConflictException` | API error | Another update is in progress. Wait for `State == Active`, retry. |
| `update-function-configuration` for arm64 fails with `InvalidParameterValueException` | API error | Deployment package contains x86-only native binaries. Migration blocked. |
| `publish-version` fails with `ResourceConflictException` | API error | Function code changed during publish. Retry after `State == Active`. |
| `update-event-source-mapping` fails with `InvalidParameterValueException` for batch size | API error | Requested batch size exceeds the max for the source. Re-check source-specific limit. |
| SnapStart enable fails with `SnapStartNotSupported` | API error | Runtime does not support SnapStart (only Java 11+ Corretto). Surface as finding; do not block. |

### Power Tuning failures

| Failure mode | Detection | Handling |
|---|---|---|
| Step Functions execution fails with `AccessDeniedException` | Execution status `FAILED` | Power Tuning IAM role lacks `lambda:InvokeFunction` on the target. Verify role trust policy. |
| Execution `TIMED_OUT` | Execution status `TIMED_OUT` | Function timeout too high for Power Tuning's parallel invocations. Reduce `num` or set a lower `powerValues` range. |
| Execution output shows `all-strategies-failed` | Output payload contains error | Function is erroring at all tested memory settings. Fix functional errors before optimizing cost. |

## Operational edge cases

### CloudWatch metrics missing or incomplete

| Scenario | Detection | Action |
|---|---|---|
| Duration Datapoints empty for entire window | `len(Datapoints) == 0` | Zero invocations in window. If dormant, emit ALREADY_OPTIMAL with note. If trigger exists but no invocations, upstream may be misconfigured — surface as BLOCKED. |
| Invocations present but Duration absent | Invocations Sum > 0, Duration empty | Rare CloudWatch propagation issue. Re-query with `--period 3600`. If still absent, fall back to timed `aws lambda invoke` and extrapolate. LOW confidence. |
| Memory utilization absent | `list-metrics` returns no LambdaInsights metrics | Install `AWS-Lambda-Insights-Extension` Layer. Until installed, Power Tuning is the only memory signal; MEDIUM confidence. |
| Metrics window < 14 days | Datapoints span < 14 days | Workload may reflect atypical load. Emit NEED_MORE_INFO; wait for 14+ days. |

### Compute Optimizer has no recommendations

| Scenario | Detection | Action |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `Inactive` | Enable it. Until enabled, proceed with CloudWatch + Power Tuning only. |
| Active but no Lambda findings | `lambdaFunctionRecommendations` array empty | Function is `Optimized` or not yet analyzed (analysis runs every 24h). Cross-check `lastRefreshTimestamp`. |
| `AccessDeniedException` on `compute-optimizer:*` | API error | IAM role lacks permissions. Add `compute-optimizer:GetLambdaFunctionRecommendations`. Proceed without cross-check. |

### Function uses container image deployment

Lambda functions deployed from a container image (`PackageType: Image`)
require adjusted optimisation workflow:

| Behaviour | Impact on optimisation |
|---|---|
| `CodeSize` is opaque (container layers) | Cannot assess package-size impact on cold start. Use InitDuration metric directly. |
| Lambda Layers are NOT supported | Cannot recommend Layer-based package optimisation. The container image IS the deployment package. |
| ARM64 migration requires multi-arch build | Container image must be built for `linux/arm64` (e.g., `docker buildx build --platform linux/arm64`). |
| Memory tuning still applies | Power Tuning works identically regardless of deployment type. Run it normally. |

**Detection:**
```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{PackageType: .PackageType, ImageUri: .Code.ImageUri}'
```

If `PackageType: Image`, adjust the recommendation:
1. Run Power Tuning normally (memory tuning applies to container functions).
2. Skip any Lambda Layers recommendation.
3. For ARM64 migration, require a multi-arch container build.
4. For package-size optimisation, recommend multi-stage Docker builds instead of Layers.

## Extended NEVER list (supplementary anti-patterns)

These supplement the top 5 anti-patterns kept inline in SKILL.md.

- NEVER assume the request fee ($0.0000002/request) is negligible. At
  1 billion invocations/month it is $200/month. For ESM-triggered
  functions, batch-size tuning is the only lever to reduce this.

- NEVER recommend SnapStart for non-Java runtimes. SnapStart is Java-only
  (Corretto 11+). Recommending it for Node.js or Python is a hard error.

- NEVER enable SnapStart on a Java function that uses JNI with native
  libraries or holds network connections in the global scope without
  reconnection logic. SnapStart restores from a snapshot; native state
  may be invalid post-restore.

- NEVER trust a single Power Tuning run as permanent. Workload duration
  drifts over time (new dependencies, data growth, downstream latency
  changes). Re-run Power Tuning quarterly or after major deploys.

- NEVER recommend a memory setting above the function's actual need just
  because "more memory = faster." Past the U-curve minimum, additional
  memory INCREASES cost without proportional duration reduction.

- NEVER conflate latency optimization with cost optimization. A memory
  upsize that improves p95 latency may be cost-neutral or cost-increasing.
  Surface both dimensions explicitly.

- NEVER skip the CONFIRM gate before `update-function-configuration`.

- NEVER batch-update more than 5 functions in a single output block.

- NEVER assume the Compute Optimizer memory recommendation is the cost-
  optimal setting. Compute Optimizer optimizes for utilization; Power
  Tuning optimizes for cost. They may disagree; Power Tuning wins for
  cost decisions.

- NEVER recommend Step Functions Express workflow without comparing the
  per-invocation cost to Standard workflow per-state-transition cost.

- NEVER recommend Lambda Layers as a universal best practice. Layers add
  cold-start overhead if over-used. Use only for shared dependencies
  across 3+ functions.

- NEVER ignore `IteratorAge` on Kinesis/DynamoDB Streams ESMs when
  increasing batch size. If `IteratorAge` is rising, the function cannot
  keep up — increasing batch size without increasing parallelism will
  make it worse.

- NEVER recommend `MaximumRetryAttempts=0` on an ESM without confirming
  the downstream has its own retry/DLQ.

## Memory optimization decision tree

Route a memory recommendation through this tree BEFORE running Power
Tuning. It ranks candidates by dollar impact.

```
Is Invocations > 1M/day?
├── YES → High-impact candidate. Prioritise first.
│   └── Is Duration > 3 s AND Memory < 512 MB?
│       ├── YES → Likely CPU-bound at low memory.
│       │         INCREASE memory (U-curve expected).
│       │         Power Tuning typically finds optimum at 1024-3008 MB.
│       └── NO → Is Duration < 500 ms AND Memory > 1024 MB?
│           ├── YES → Memory is over-provisioned.
│           │         DECREASE memory.
│           └── NO → Memory is near-optimal.
│                     Run Power Tuning to confirm; focus on ARM64 or
│                     invocation frequency instead.
└── NO → Low-volume function (< 1M invocations/day).
         Dollar impact of memory tuning is negligible (< $5/month).
         Focus on architecture (ARM64) or duration reduction instead.
```

Post-tree overrides (always take precedence):

| Condition | Override |
|---|---|
| Lambda Insights `memory_used` > 80% sustained | Do NOT downsize. Function is near memory ceiling. |
| Compute Optimizer finding = `Underprovisioned` | Tree output overridden. Upsize is mandatory. |
| Function deploys via container image (`PackageType: Image`) | Power Tuning still works but package-size signal is opaque. Confidence MEDIUM. |
| Function runtime is `provided.al2` (custom) | U-curve shape depends on custom runtime. Always Power Tune; never guess. |

## Remediation guidance

### For OPPORTUNITY_FOUND — memory tuning

1. Run Power Tuning to confirm the optimal memory.
2. `aws lambda update-function-configuration --function-name <name> --memory-size <new>`.
3. `aws lambda publish-version --function-name <name>`.
4. Test via staging alias or weighted routing.
5. Cutover: `aws lambda update-alias --function-name <name> --name prod --function-version <new>`.
6. Monitor Duration and Errors for 7 days.

### For OPPORTUNITY_FOUND — provisioned concurrency removal

1. `aws lambda delete-provisioned-concurrency-config --function-name <name> --qualifier <alias>`.
2. Monitor cold-start Duration for 7 days.
3. If latency SLO violated, re-add at lower value (e.g., p50 of ConcurrentExecutions).

### For OPPORTUNITY_FOUND — provisioned concurrency right-sizing

1. `aws lambda put-provisioned-concurrency-config --function-name <name> --qualifier <alias> --provisioned-concurrent-executions <new>`.
2. Verify utilization stabilizes at 60-80% of provisioned.

### For OPPORTUNITY_FOUND — ARM64 migration

1. `aws lambda update-function-configuration --function-name <name> --architectures arm64`.
2. Test thoroughly on arm64 (native deps, performance).
3. Publish and cutover via alias.

### For OPPORTUNITY_FOUND — ESM batch tuning

1. `aws lambda update-event-source-mapping --uuid <uuid> --batch-size <new> --maximum-batching-window-in-seconds <window>`.
2. Monitor `IteratorAge` (Kinesis/DynamoDB) or approximate age of oldest message (SQS) for 7 days.

### For OPPORTUNITY_FOUND — SnapStart enable (Java)

1. `aws lambda update-function-configuration --function-name <name> --snap-start '{"ApplyOn":"PublishedVersions"}'`.
2. `aws lambda publish-version --function-name <name>`.
3. Point alias at new version.
4. Monitor InitDuration — should drop to near zero.

## Production edge cases

### Provisioned concurrency on sporadic traffic

**Scenario:** 10 provisioned concurrency but receives 0.5 invocations/minute.

**Problem:** Idle cost = 10 × 1.0 GB × 730h × 3600s × $0.000015 = $394.20/month. Over 99% idle.

**Resolution:**
1. Pull 30-day `ConcurrentExecutions`. If p99 < 3, provisioned value is far above need.
2. Check whether cold-start latency is customer-visible (for batch, usually acceptable).
3. If cold starts acceptable: `aws lambda delete-provisioned-concurrency-config`.
4. If some warm capacity needed: switch to Application Auto Scaling with target tracking on `ProvisionedConcurrencyUtilization`.

### ARM64 incompatibility — native libraries

**Scenario:** Python function uses `numpy`, `scipy`, or custom C extension compiled for x86_64.

**Detection before migration:**
```bash
pip install --platform aarch64 --only-binary=:all: <package-name>
# If this fails, the package has no arm64 wheel
```

**Resolution:**
1. Identify all native dependencies.
2. For Python: verify arm64 wheel availability. Problem packages: `pycrypto` (use `pycryptodome`), legacy `numpy` (upgrade to 1.20+).
3. For Java: verify JNI libraries have arm64 builds.
4. For Go: recompile with `GOARCH=arm64 GOOS=linux`.
5. If critical dependency has no arm64 support, do NOT migrate.

### ESM batch size impact on total cost

**Scenario:** SQS-triggered function, batch size 10 → 1000 reduces invocation count 99%.

**Problem:** Batch-size tuning has a non-linear cost curve. For CPU-bound workloads, compute cost is unchanged (same GB-seconds). Only the request fee drops.

**Worked math (1M messages/hour, 50 ms processing per message):**
```
Batch size 10:   100,000 invocations × 0.5 s each
Batch size 100:  10,000 invocations × 5.0 s each
  Request fee saving: 90% (100,000 to 10,000 invocations)
  Compute saving: 0% (100,000 × 0.5 = 10,000 × 5.0 = same GB-seconds)

Batch size 1000: 1,000 invocations × 50 s each
  PROBLEM: 50 s may exceed timeout. Must increase timeout accordingly.
```

**Resolution:**
1. Calculate optimal batch size where invocation-count saving is not eaten by duration increase.
2. Verify timeout accommodates longer per-batch duration.
3. Ensure `FunctionResponseTypes: ["ReportBatchItemFailures"]` for SQS.
4. Monitor `IteratorAge` or `ApproximateAgeOfOldestMessage` for 7 days.
5. For I/O-bound workloads: batch 10→100 saves 80-90% on request fees AND 10-30% on compute. For CPU-bound: only request fee saving applies.
