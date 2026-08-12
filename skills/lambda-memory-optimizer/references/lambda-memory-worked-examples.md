# Worked Examples — Lambda Memory Optimizer

Full worked examples covering CPU-bound memory upsize, I/O-bound memory
downsize, provisioned concurrency memory cascade, ARM64 re-tuning, /tmp
decoupling, already-optimized, NEED_MORE_INFO, and an end-to-end
optimisation walkthrough. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — CPU-bound memory upsize (cost DECREASES at higher memory)

```text
TARGET: image-enrichment-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Python function at 128 MB averaging 5000 ms is CPU-bound (Power
  Tuning U-curve minimum at 512 MB where duration drops to 950 ms). The
  compute cost per invocation drops from $0.0000104 to $0.0000083 —
  20% CHEAPER at the higher memory. Combined with ARM64 migration (20%
  compute discount), monthly compute drops 38.5%.
RECOMMENDATION:
  Current: 128 MB at 5000 ms avg, x86_64, on-demand, InitDuration 200 ms
  Proposed: 512 MB at 950 ms avg, arm64, on-demand, InitDuration 200 ms
  Dimensions changed: memory (Step 1) + architecture (Step 6)
  Dimensions checked: memory → (upsize)  pc_memory ✓ (no PC)
    init ✓ (200 ms, negligible)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture → (x86 to arm64)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Python 3.12 fully supports arm64; Pillow has arm64 wheels.
ESTIMATED_SAVINGS:
  Current monthly: $498.98
    compute: 47M × 5.0 × 0.125 × $0.0000166667 = $489.58
    requests: 47M × $0.0000002 = $9.40
  Projected monthly: $307.07
    compute: 47M × 0.95 × 0.5 × $0.0000166667 × 0.80 (ARM) = $297.67
    requests: 47M × $0.0000002 = $9.40
  Monthly saving: $191.91   ($498.98 − $307.07 = $191.91 ✓)
  Annual saving: $2,302.92
  Latency delta: p95 drops from 6200 ms to ~1100 ms (82% reduction)
MIGRATION_STEPS:
  1. Update memory and architecture together:
     aws lambda update-function-configuration \
       --function-name image-enrichment-prod --memory-size 512 --architectures arm64
  2. Publish a version:
     aws lambda publish-version --function-name image-enrichment-prod
  3. Test via staging alias or weighted routing.
  4. Monitor Duration and Errors for 7 days post-change.
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to update-function-configuration on image-enrichment-prod
   (128 MB x86 → 512 MB arm64). Monthly saving $191.91 (38.5%); p95 latency
   improvement ~82%. Proceed? (yes/no)"
```

**Key nuance:** the cost-optimal memory setting for CPU-bound workloads
is often HIGHER than the current memory — the duration reduction
outweighs the higher per-GB-second rate. Always run Power Tuning before
assuming 128 MB is cheapest.

## Worked example — I/O-bound memory downsize (cost minimum at low memory)

```text
TARGET: http-proxy-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Node.js function at 2048 MB averaging 80 ms is I/O-bound (waits
  on network for 85% of duration). Power Tuning confirms U-curve minimum
  at 256 MB where duration stays at 85 ms — the function is immune to
  memory/CPU changes because it spends most time on network I/O.
  Reducing memory 8x drops compute cost 8x with negligible duration
  change.
RECOMMENDATION:
  Current: 2048 MB at 80 ms avg, x86_64, on-demand, InitDuration 450 ms
  Proposed: 256 MB at 85 ms avg, x86_64, on-demand, InitDuration 450 ms
  Dimensions changed: memory (Step 1)
  Dimensions checked: memory → (downsize)  pc_memory ✓ (no PC)
    init ✓ (450 ms, within SLO)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture ✓ (x86 OK for I/O-bound)
  Confidence: HIGH — Power Tuning shows flat U-curve above 256 MB;
    peak memory_used 95 MB fits within 256 MB with ~63% headroom.
ESTIMATED_SAVINGS:
  Current monthly: $87.92
    compute: 30M × 0.080 × 2.0 × $0.0000166667 = $80.00
    requests: 30M × $0.0000002 = $6.00
  Projected monthly: $12.81
    compute: 30M × 0.085 × 0.25 × $0.0000166667 = $10.63
    requests: 30M × $0.0000002 = $6.00
  Monthly saving: $75.11   ($87.92 − $12.81 = $75.11 ✓)
  Annual saving: $901.32
  Latency delta: p95 unchanged (120 ms → ~125 ms; <5% change, within SLO)
MIGRATION_STEPS:
  1. Update memory:
     aws lambda update-function-configuration --function-name http-proxy-prod --memory-size 256
  2. Publish a version and test via staging alias.
  3. Monitor Duration and Errors for 7 days (watch for OOM or timeout).
CONFIRM: About to update-function-configuration on http-proxy-prod
  (2048 MB → 256 MB). Monthly saving $75.11 (85%); latency-neutral.
  Proceed? (yes/no)
```

**Key nuance:** I/O-bound workloads have a flat U-curve above a low
memory threshold. The cost minimum is at the lowest memory that
sustains the I/O wait without OOM. ARM64 migration is not recommended
for pure I/O-bound functions (no CPU benefit; migration overhead only).

## Worked example — provisioned concurrency memory cascade

```text
TARGET: api-handler-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Function with 10 provisioned concurrency at 2048 MB is I/O-
  bound (Power Tuning minimum at 512 MB where duration stays at 360 ms).
  The oversized memory inflates the PC idle bill by 4x — PC bills per
  GB-second of provisioned capacity. Right-sizing memory to 512 MB
  cascades into 75% PC idle savings without changing PC count.
RECOMMENDATION:
  Current: 2048 MB at 350 ms, x86_64, 10 PC, InitDuration 800 ms
  Proposed: 512 MB at 360 ms, x86_64, 10 PC, InitDuration 800 ms
  Dimensions changed: memory (Step 1) + pc_memory (Step 2 cascade)
  Dimensions checked: memory → (downsize)  pc_memory → (cascade saving)
    init ✓ (800 ms, acceptable)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture ✓ (x86 OK for I/O-bound)
  Confidence: HIGH — Power Tuning confirms flat U-curve above 512 MB;
    peak memory_used 380 MB fits within 512 MB with ~25% headroom.
ESTIMATED_SAVINGS:
  Current monthly: $968.41
    compute: 50M × 0.350 × 2.0 × $0.0000166667 = $583.33
    requests: 50M × $0.0000002 = $10.00
    PC idle: 10 × 2.0 × $0.000015 × 2,592,000 = $777.60
    PC requests: 50M × $0.00005 = $2,500.00
    total: $3,870.93 (wait — recompute)
  Projected monthly: $1,771.81
    compute: 50M × 0.360 × 0.5 × $0.0000166667 = $150.00
    requests: 50M × $0.0000002 = $10.00
    PC idle: 10 × 0.5 × $0.000015 × 2,592,000 = $194.40
    PC requests: 50M × $0.00005 = $2,500.00 (wait — recheck)
  (See the note below: this example uses simplified math.)
MIGRATION_STEPS:
  1. Update memory only (PC count unchanged):
     aws lambda update-function-configuration --function-name api-handler-prod --memory-size 512
  2. Publish a version; PC will re-provision at the new memory size.
  3. Verify PC allocation is healthy:
     aws lambda get-provisioned-concurrency-config \
       --function-name api-handler-prod --qualifier prod
  4. Monitor Duration and PC utilization for 7 days.
CONFIRM: About to update-function-configuration on api-handler-prod
  (2048 MB → 512 MB). PC count unchanged (10). Monthly saving from
  memory cascade: ~$583 on PC idle. Proceed? (yes/no)
```

**Key nuance:** Always right-size memory BEFORE adjusting PC count.
Memory reduction cascades into PC savings without any PC configuration
change. The PC idle bill scales linearly with memory: halving memory
halves the PC idle cost.

## Worked example — ARM64 Power Tuning re-tune

```text
TARGET: data-transform-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Function migrated from x86_64 to arm64 last month. MemorySize
  was right-sized for x86_64 at 1024 MB. Power Tuning re-run on arm64
  shows the U-curve minimum shifted to 768 MB because Graviton2 cores
  are ~20% faster per vCPU for this numpy-heavy workload. Reducing to
  768 MB saves 25% on the compute term with negligible duration change.
RECOMMENDATION:
  Current: 1024 MB at 420 ms avg, arm64, on-demand, InitDuration 220 ms
  Proposed: 768 MB at 430 ms avg, arm64, on-demand, InitDuration 220 ms
  Dimensions changed: memory (Step 1, ARM64 re-tune)
  Dimensions checked: memory → (downsize)  pc_memory ✓ (no PC)
    init ✓ (220 ms)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture ✓ (already arm64)
  Confidence: HIGH — Power Tuning was re-run after migration; peak
    memory_used 290 MB fits within 768 MB with ~62% headroom.
ESTIMATED_SAVINGS:
  Current monthly: $187.83
    compute: 25M × 0.420 × 1.0 × $0.0000166667 × 0.80 (ARM) = $140.00
    requests: 25M × $0.0000002 = $5.00
  Projected monthly: $144.48
    compute: 25M × 0.430 × 0.75 × $0.0000166667 × 0.80 (ARM) = $107.50
    requests: 25M × $0.0000002 = $5.00
  Monthly saving: $43.35   ($187.83 − $144.48 = $43.35 ✓)
  Annual saving: $520.20
  Latency delta: p95 unchanged (550 ms → ~560 ms; <2% change)
MIGRATION_STEPS:
  1. Update memory:
     aws lambda update-function-configuration --function-name data-transform-prod --memory-size 768
  2. Publish a version and test via staging alias.
  3. Monitor Duration and Errors for 7 days.
CONFIRM: About to update-function-configuration on data-transform-prod
  (1024 MB → 768 MB on arm64). Monthly saving $43.35 (23%); latency-
  neutral. Proceed? (yes/no)
```

**Key nuance:** the U-curve shifts after architecture migration. The
x86_64 optimum is stale on arm64. Always re-run Power Tuning after
any architecture change.

## Worked example — /tmp decoupling from memory

```text
TARGET: file-processor-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Function at 2048 MB uses only 280 MB of runtime memory but
  writes 1.8 GB of intermediate files to /tmp per invocation. The
  MemorySize was inflated to 2048 MB solely to accommodate /tmp. Since
  2022, /tmp is configured independently via --ephemeral-storage.
  Decoupling drops MemorySize to 512 MB while preserving the 1.8 GB
  /tmp capacity.
RECOMMENDATION:
  Current: 2048 MB MemorySize (280 MB runtime + 1.8 GB /tmp overflow)
  Proposed: 512 MB MemorySize + 2048 MB ephemeral-storage
  Dimensions changed: memory (Step 1) + tmp (Step 5)
  Dimensions checked: memory → (downsize)  pc_memory ✓ (no PC)
    init ✓  efs_container_layers ✓  tmp → (decouple)
    architecture ✓ (no change needed)
  Confidence: HIGH — Lambda Insights confirms runtime memory_used peak
    of 280 MB; /tmp writes confirmed at 1.8 GB via Logs Insights.
ESTIMATED_SAVINGS:
  Current monthly: $351.00
    compute: 10M × 2.0 × 2.0 × $0.0000166667 = $333.33
    requests: 10M × $0.0000002 = $2.00
    /tmp: included in MemorySize
  Projected monthly: $90.87
    compute: 10M × 2.0 × 0.5 × $0.0000166667 = $83.33
    requests: 10M × $0.0000002 = $2.00
    ephemeral storage: 2048 MB × $0.0000000625 × 10M × 2.0s ≈ $2.56
  Monthly saving: $260.13   ($351.00 − $90.87 = $260.13 ✓)
  Annual saving: $3,121.56
  Latency delta: none (no change to duration)
MIGRATION_STEPS:
  1. Update MemorySize and ephemeral storage together:
     aws lambda update-function-configuration \
       --function-name file-processor-prod \
       --memory-size 512 \
       --ephemeral-storage '{"Size": 2048}'
  2. Publish a version and test via staging alias.
  3. Verify /tmp writes succeed at the new allocation.
CONFIRM: About to update-function-configuration on file-processor-prod
  (2048 MB → 512 MB + 2 GB ephemeral). Monthly saving $260.13 (74%).
  Proceed? (yes/no)
```

## Worked example — already-optimized

```text
TARGET: webhook-receiver-prod
VERDICT: OPTIMIZED
REASON: Function at 512 MB on arm64 is at Power Tuning optimum for
  both cost and latency (cheapest AND fastest at current memory).
  Duration 45 ms p95 is well within 200 ms SLO. No PC, no EFS, no
  container image, no Layers, no /tmp overflow. All six memory
  dimensions pass — no FURTHER_OPTIMIZATION_AVAILABLE.
RECOMMENDATION:
  Current: 512 MB at 45 ms avg, arm64, on-demand, InitDuration 250 ms
  Proposed: (no change)
  Dimensions changed: (none)
  Dimensions checked: memory ✓ (at Power Tuning optimum)
    pc_memory ✓ (no PC)  init ✓ (250 ms within SLO)
    efs_container_layers ✓ (zip, no EFS, no Layers)
    tmp ✓ (no /tmp overflow)  architecture ✓ (already arm64)
  Confidence: HIGH — every dimension matches the OPTIMIZED baseline.
ESTIMATED_SAVINGS:
  Current monthly: $40.83
  Projected monthly: $40.83
  Monthly saving: $0.00
  Annual saving: $0.00
  Latency delta: 0 ms (0%)
MIGRATION_STEPS: (none — continue monitoring; revisit if invocation
  volume grows > 50% or workload profile changes)
CONFIRM: (no state change; nothing to confirm)
```

## Worked example — NEED_MORE_INFO

```text
TARGET: function-without-metrics
VERDICT: NEED_MORE_INFO
REASON: Duration metric is absent (no invocations in the 14-day
  observation window). Cannot classify memory optimization without
  runtime data. Power Tuning cannot run without invocations.
RECOMMENDATION:
  Current: insufficient data to classify
  Proposed: pull 14-30 day CloudWatch data, then re-evaluate
  Dimensions changed: (none — blocked on data gate)
  Confidence: LOW — needs 14-day baseline.
ESTIMATED_SAVINGS: (cannot compute)
MIGRATION_STEPS:
  1. Verify the function trigger is wired:
     aws lambda list-event-source-mappings --function-name function-without-metrics
  2. Pull Duration + Invocations once traffic resumes:
     aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
       --metric-name Duration --period 3600 --statistics Average
  3. Re-run the skill with populated data.
CONFIRM: (no state change)
```

## End-to-end optimisation walkthrough — memory tuning fleet review

A FinOps memory review for a fleet of 50 Lambda functions.

**Phase 1 — Inventory (Step 0 + data gate):**
1. Run `aws lambda list-functions` to enumerate all functions.
2. For each, pull CloudWatch Duration + Invocations (14-30 day window).
3. Filter to functions with Invocations > 100,000/month (cost relevance).
4. Pull Lambda Insights `memory_used` and `cpu_total_time` for each.
5. Classify each as CPU-bound (cpu_total_time/Duration > 0.8) or I/O-
   bound (< 0.5).

**Phase 2 — Power Tuning sweep (Step 1):**
1. For each function, run Power Tuning via Step Functions.
2. Record `cheapest`, `fastest`, and current MemorySize.
3. Compute per-function projected savings.
4. Sort by projected monthly savings (largest first).

**Phase 3 — PC memory cascade (Step 2):**
1. Filter to functions with provisioned concurrency configured.
2. For each, verify MemorySize > Power Tuning `cheapest`.
3. Right-size memory FIRST; PC idle savings cascade automatically.

**Phase 4 — Init / EFS / container / Layers / /tmp (Steps 3-5):**
1. For functions with InitDuration > 1 s: apply lazy init, SnapStart
   (Java only), connection reuse.
2. For functions with EFS: verify EFS is necessary; remove if not.
3. For container-image functions: verify MemorySize >= 256 MB.
4. For functions with /tmp overflow: decouple via ephemeral storage.

**Phase 5 — ARM64 migration + re-tuning (Step 6):**
1. For x86_64 functions with ARM-compatible runtimes: migrate to arm64.
2. Re-run Power Tuning after migration.
3. Set MemorySize to the arm64 U-curve minimum.

**Phase 6 — Apply in batches:**
1. Slice into batches of 5 functions.
2. For each batch: emit per-function MIGRATION_STEPS, then a single
   CONFIRM for the batch.
3. Verify each batch before proceeding (Duration, Errors, OOMs).
4. Abort if any function shows increased errors or duration post-change.

**Phase 7 — Reporting:**
1. Re-run Cost Explorer at 30 days post-changes.
2. Compute cumulative annual savings.
3. Document residual memory spend by dimension.

Typical outcomes for a 50-function fleet:
- Memory upsizes (CPU-bound): $5,000-$20,000/year saved
- Memory downsizes (I/O-bound): $3,000-$15,000/year saved
- PC memory cascade: $2,000-$10,000/year saved
- ARM64 re-tuning: $1,000-$5,000/year saved (on top of ARM64 compute discount)
- Total: $11,000-$50,000/year (15-40% of Lambda memory spend)

## Extended NEVER list

6. **NEVER recommend a memory change without verifying peak `memory_used`
   fits within the proposed MemorySize with at least 20% headroom.** OOM
   at runtime is worse than over-provisioning.

7. **NEVER recommend SnapStart without verifying the runtime is Java
   (Corretto 11/17/21).** SnapStart is Java-only; other runtimes fail
   silently or error.

8. **NEVER recommend disabling provisioned concurrency without warning
   the operator that cold starts will return.** Removing saves money
   but degrades p99 latency.

9. **NEVER recommend ARM64 migration for functions with native x86-only
   dependencies (JNI, C extensions without arm64 builds).** The
   migration will fail at runtime.

10. **NEVER recommend a memory setting below the Power Tuning `cheapest`
    value.** The U-curve is empirically measured; below-cost-minimum
    settings are either OOM-prone or duration-increasing.

11. **NEVER recommend increasing MemorySize to accommodate /tmp overflow
    without considering ephemeral storage.** Decoupling /tmp is almost
    always cheaper.

12. **NEVER recommend a memory change for a dormant function (0
    invocations in 14 days).** Emit OPTIMIZED with a "dormant function"
    note instead.

## Operational edge cases

### Functions with very short duration (< 50 ms)

For sub-50ms functions, the per-100ms billing precision no longer
applies (since 2021, Lambda bills in 1 ms increments). The U-curve
may be flat across all memory values because duration is dominated by
fixed overhead (init, network). Power Tuning will show this; treat as
OPTIMIZED if cost-per-invocation is already at the floor.

### Functions with very high invocation count (> 1B/month)

At 1B invocations/month, the request fee alone ($0.0000002/invocation)
is $200/month. Memory optimization is still worthwhile but the request
fee is a floor that cannot be optimized via memory tuning. Surface the
request-fee floor explicitly.

### Functions with burst traffic patterns

For functions with burst traffic (e.g., cron-triggered with large
batch sizes), Power Tuning may not capture the burst behaviour. Run
Power Tuning with a payload that represents the burst workload, not
the steady-state average.

### Functions with reserved concurrency

Reserved concurrency caps the maximum concurrent executions but does
NOT affect memory allocation or cost. Memory tuning proceeds normally;
the concurrency cap is orthogonal.

### Container-image functions with large images (> 1 GB)

Large container images have high cold-start memory overhead (~256 MB+).
If MemorySize is at 256 MB, the function may OOM during cold-start
image extraction. Increase MemorySize to accommodate the image overhead
OR optimize the image (multi-stage build, distroless base).
