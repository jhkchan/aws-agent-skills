# Worked Examples — EC2 Instance Rightsizer

Full worked examples covering downsizing, generation upgrades, Graviton
migration, burstable credit fixes, idle instance stops, already-
optimized, NEED_MORE_INFO, and an end-to-end right-sizing walkthrough.
Loaded on demand — kept out of the main SKILL.md body so the procedure
stays scannable.

## Worked example — downsize within family (overprovisioned)

```text
TARGET: i-0web01 (m5.2xlarge)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: m5.2xlarge averaging 3.2% CPU and 28% memory (CWAgent confirmed)
  over 14 days is significantly overprovisioned. Compute Optimizer
  cross-check agrees (Overprovisioned, recommends m5.large). Web server
  workload tolerates downsize (stateless, no buffer cache dependency).
  Downsizing from m5.2xlarge to m5.large saves 75% of compute cost
  while projected CPU stays under 15%.
RECOMMENDATION:
  Current: m5.2xlarge, x86_64, On-Demand, us-east-1
  Proposed: m5.large, x86_64, On-Demand, us-east-1
  Dimensions changed: cpu-mem (downsize)
  Dimensions checked: idle ✓ (>5% CPU)  cpu-mem → (3.2%/28%)
    family ✓ (m5 is current enough)  graviton ✓ (x86 web server, JNI dep)
    burstable ✓ (not t-family)  workload ✓ (web server, downsize-safe)
    pricing ✓ (On-Demand, no SP)  spot ✓ (production web server)
  Confidence: HIGH — CWAgent memory confirms 28%; Compute Optimizer
    agrees; web server workload tolerates downsize; 14-day window.
ESTIMATED_SAVINGS:
  Current monthly: $280.32
    m5.2xlarge: $0.384/h × 730 = $280.32
  Projected monthly: $70.08
    m5.large: $0.096/h × 730 = $70.08
  Monthly saving: $210.24 (75%)
  Annual saving: $2,522.88
MIGRATION_STEPS:
  1. Stop the instance:
     aws ec2 stop-instances --instance-ids i-0web01
  2. Change instance type:
     aws ec2 modify-instance-attribute --instance-id i-0web01 \
       --instance-type "{\"Value\": \"m5.large\"}"
  3. Start and verify:
     aws ec2 start-instances --instance-ids i-0web01
  4. Monitor CPUUtilization and MemoryUtilization for 7 days:
     aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
       --metric-name CPUUtilization \
       --dimensions Name=InstanceId,Value=i-0web01 \
       --start-time $(date -d '-7 days' +%FT%TZ) \
       --end-time $(date +%FT%TZ) --period 3600 \
       --statistics Average,Maximum --output json
CONFIRM: About to modify-instance-attribute on i-0web01
  (m5.2xlarge → m5.large). Monthly saving $210.24 (75%); projected CPU
  under 15%. Proceed? (yes/no)
```

## Worked example — generation upgrade + Graviton migration

```text
TARGET: i-0api02 (m5.xlarge)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: m5.xlarge running a Python/Node.js API is on a 5th-generation
  x86 instance. Migrating to m7g.xlarge (Graviton3) delivers ~17% cost
  saving AND ~20% better per-core performance. The application stack
  (Python 3.12 + Node.js 20, no native C extensions beyond numpy which
  has aarch64 wheels) is Graviton-compatible. Combined with current
  utilization (CPU 35%, Memory 50%), this is a stacked win: right-size
  stays the same size but changes generation and architecture.
RECOMMENDATION:
  Current: m5.xlarge, x86_64, On-Demand, us-east-1
  Proposed: m7g.xlarge, arm64 (Graviton3), On-Demand, us-east-1
  Dimensions changed: family (generation) + graviton (architecture)
  Dimensions checked: idle ✓  cpu-mem ✓ (35%/50% is well-sized)
    family → (m5 to m7g)  graviton → (x86 to arm64)
    burstable ✓  workload ✓ (API server, Graviton-safe)
    pricing ✓ (On-Demand)  spot ✓ (production)
  Confidence: HIGH — Python 3.12 + Node.js 20 fully support arm64;
    numpy has aarch64 wheels (verified); m7g is GA and stable.
    CWAgent confirms 50% memory utilization (no OOM risk).
ESTIMATED_SAVINGS:
  Current monthly: $140.16
    m5.xlarge: $0.192/h × 730 = $140.16
  Projected monthly: $116.80
    m7g.xlarge: $0.160/h × 730 = $116.80
  Monthly saving: $23.36 (17%)
  Annual saving: $280.32
  Performance improvement: ~20% better per-core throughput (Graviton3
    vs m5's Skylake). Effective cost-per-request drops ~31%.
MIGRATION_STEPS:
  1. Find an arm64 AMI:
     aws ec2 describe-images --owners amazon \
       --filters "Name=architecture,Values=arm64" \
       --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text
  2. Launch a test Graviton instance:
     aws ec2 run-instances --image-id ami-0newarm64 \
       --instance-type m7g.xlarge --key-name my-key \
       --security-group-ids sg-0abc123 --subnet-id subnet-0abc123 \
       --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=api-arm64-test}]"
  3. Deploy the application and verify:
     - Python 3.12 runtime works
     - numpy imports successfully (aarch64 wheel)
     - Node.js 20 runtime works
     - API responds within latency SLO
  4. Cut over DNS/load balancer to the new instance.
  5. Decommission the old m5.xlarge:
     aws ec2 terminate-instances --instance-ids i-0api02
  6. Monitor for 7 days post-cutover.
CONFIRM: About to launch a new m7g.xlarge instance for arm64 testing.
  Monthly saving $23.36 (17%) + ~20% performance improvement. The
  migration requires AMI + app testing before cutover. Proceed? (yes/no)
```

## Worked example — burstable credit exhaustion (t3 Unlimited decision)

```text
TARGET: i-0build03 (t3.large)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: t3.large has CPUCreditBalance trending to 0 for 5+ consecutive
  days, indicating the workload is sustained-high-CPU (not spiky).
  Sustained credit exhaustion on t3 means the instance is throttled to
  30% baseline. Two options: enable Unlimited (borrows credits at
  $0.05/vCPU-hour) or migrate to m6i.large (consistent CPU). At 180+
  borrowed vCPU-hours/month, m6i.large is CHEAPER than t3+Unlimited.
  The workload (CI/CD runner) is sustained-high during business hours.
RECOMMENDATION:
  Current: t3.large, x86_64, On-Demand (standard credit mode)
  Proposed: m6i.large, x86_64, On-Demand
  Dimensions changed: burstable (credit exhaustion → migrate to m-family)
  Dimensions checked: idle ✓  cpu-mem ✓ (high CPU is the issue)
    family → (t3 to m6i)  graviton ✓ (CI runner, x86 Docker images)
    burstable → (credit exhaustion, migrate off t-family)
    workload ✓ (CI/CD runner)  pricing ✓  spot ✓ (production CI)
  Confidence: HIGH — CPUCreditBalance data confirms sustained
    exhaustion; CI runner workload is sustained-high during builds;
    m6i.large provides consistent 2 vCPU without credit dependency.
ESTIMATED_SAVINGS:
  Current monthly: $60.74 + Unlimited surcharge
    t3.large base: $0.0832/h × 730 = $60.74
    Estimated Unlimited surcharge (180 borrowed vCPU-h): 180 × $0.05 = $9.00
    Total with Unlimited: $69.74/month
  Projected monthly: $70.08
    m6i.large: $0.096/h × 730 = $70.08
  Monthly saving: ($69.74 vs $70.08 — approximately cost-neutral in $)
  BUT: performance improvement is significant — m6i.large provides
  consistent 2 vCPU without throttling, eliminating build timeouts.
  Effective value: build throughput increases ~40-60% (no baseline throttle).
MIGRATION_STEPS:
  1. Stop the instance:
     aws ec2 stop-instances --instance-ids i-0build03
  2. Change instance type:
     aws ec2 modify-instance-attribute --instance-id i-0build03 \
       --instance-type "{\"Value\": \"m6i.large\"}"
  3. Start and verify:
     aws ec2 start-instances --instance-ids i-0build03
  4. Monitor CPUUtilization and build completion times for 7 days.
CONFIRM: About to modify-instance-attribute on i-0build03
  (t3.large → m6i.large). Cost is approximately neutral ($69.74 →
  $70.08/mo) but build throughput improves ~40-60% (no credit throttle).
  Proceed? (yes/no)
```

## Worked example — idle instance stop

```text
TARGET: i-0legacy06 (m5.large)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: m5.large has averaged 0.3% CPU, <1 MB/h network, and <5 ops/s
  disk I/O for 16 consecutive days. All idle criteria are met. The
  instance is EBS-backed with no termination protection. Stopping
  eliminates 100% of compute cost while preserving the root EBS volume
  for potential restart.
RECOMMENDATION:
  Current: m5.large, x86_64, On-Demand, us-east-1 (running)
  Proposed: m5.large, stopped
  Dimensions changed: idle (stop instance)
  Dimensions checked: idle → (0.3% CPU for 16 days)  cpu-mem → (idle)
    family ✓  graviton ✓  burstable ✓  workload ✓  pricing ✓  spot ✓
  Confidence: HIGH — 16-day idle pattern with negligible I/O across
    all metrics; EBS-backed (preserves root volume); no termination
    protection (safe to stop).
ESTIMATED_SAVINGS:
  Current monthly: $70.08
    m5.large: $0.096/h × 730 = $70.08
  Projected monthly: $0.00 (stopped — compute only)
  Monthly saving: $70.08 (100% of compute)
  Annual saving: $840.96
  Note: EBS volume continues to charge (~$10/month for 100 GB gp2).
        Total spend drops from $80/mo to $10/mo.
MIGRATION_STEPS:
  1. Verify no critical tags or ownership disputes:
     aws ec2 describe-instances --instance-ids i-0legacy06 \
       --query 'Reservations[0].Instances[0].Tags'
  2. Verify termination protection status:
     aws ec2 describe-instance-attribute --instance-id i-0legacy06 \
       --attribute disableApiTermination
  3. Stop the instance:
     aws ec2 stop-instances --instance-ids i-0legacy06
  4. Confirm stopped state:
     aws ec2 describe-instances --instance-ids i-0legacy06 \
       --query 'Reservations[0].Instances[0].State.Name'
  5. If the instance remains stopped for 30 days, evaluate termination
     to also eliminate EBS cost.
CONFIRM: About to stop-instances on i-0legacy06 (m5.large). Monthly
  saving $70.08 (100% compute). EBS volume preserved for restart.
  Proceed? (yes/no)
```

## Worked example — already optimized

```text
TARGET: i-0db-prod01 (r6i.2xlarge)
VERDICT: OPTIMIZED
REASON: r6i.2xlarge running PostgreSQL with CPU avg 42%, memory avg 68%
  (CWAgent), no credit exhaustion (not t-family), current generation
  (6th gen x86), Graviton evaluated but blocked by PostgreSQL extension
  dependency (PostGIS compiled for x86). No Savings Plan gap. All
  dimensions pass.
RECOMMENDATION:
  Current: r6i.2xlarge, x86_64, On-Demand, us-east-1 — no change
  Dimensions checked: idle ✓  cpu-mem ✓ (42%/68% well-balanced)
    family ✓ (r6i is current gen)  graviton ✓ (PostGIS x86 dep blocks)
    burstable ✓ (not t-family)  workload ✓ (database, memory is cache)
    pricing ✓ (no SP gap)  spot ✓ (production DB, not Spot)
  Confidence: HIGH — 30-day observation window; CWAgent memory
    confirms 68% (healthy for database buffer cache); PostGIS
    incompatibility verified (no aarch64 build available).
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if:
    (a) PostGIS releases an arm64 build (enables Graviton)
    (b) CPU drops below 20% (may indicate workload shift)
    (c) Memory drops below 40% (may indicate dataset shrinkage —
        downsize candidate for the buffer cache dimension)
    (d) Quarterly FinOps review
```

## Worked example — NEED_MORE_INFO (CWAgent memory absent)

```text
TARGET: i-0app04 (m5.xlarge)
VERDICT: NEED_MORE_INFO
REASON: m5.xlarge shows CPU avg 8% (below downsize threshold of 30%),
  but CWAgent `mem_used_percent` is absent. Without guest memory data,
  a downsize recommendation risks OOM if the workload is memory-bound
  (e.g., JVM heap, in-memory cache). Compute Optimizer shows
  Overprovisioned, but its finding is based on CPU/network only — it
  does not see guest memory either. Cannot confidently recommend
  downsize without CWAgent memory metrics.
RECOMMENDATION:
  Current: m5.xlarge, x86_64, On-Demand, us-east-1 — pending data
  Proposed: pending CWAgent memory data
  Dimensions checked: idle ✓  cpu-mem → (CPU low, memory UNKNOWN)
    family ✓  graviton ✓  burstable ✓  workload ✓  pricing ✓  spot ✓
  Confidence: LOW — no memory data to evaluate the downsize.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without memory confirmation)
  Potential (if memory < 50%): m5.xlarge → m5.large = $70.08/mo saving
MIGRATION_STEPS:
  1. Install CloudWatch Agent for memory metrics:
     aws ssm send-command \
       --document-name "AWS-ConfigureAWSPackage" \
       --instance-ids i-0app04 \
       --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}'
  2. Configure CWAgent to collect mem_used_percent.
  3. Wait 14 days for representative memory observation.
  4. Re-evaluate with CPU + memory data.
  Do NOT downsize based on CPU alone — the workload may be memory-bound.
```

## Worked example — NEED_MORE_INFO (observation window < 14 days)

```text
TARGET: i-0newapp05 (m6i.large)
VERDICT: NEED_MORE_INFO
REASON: Only 5 days of CloudWatch data available (instance launched
  recently). The 5-day CPU avg of 12% may reflect deployment spikes or
  initial testing, not steady-state. Minimum 14-day window required;
  30 days preferred to capture weekday/weekend and business-cycle
  patterns.
RECOMMENDATION:
  Current: m6i.large — pending 14+ day observation
  Proposed: pending data
  Confidence: LOW — insufficient observation window.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify)
MIGRATION_STEPS:
  1. Wait 9 more days to reach the 14-day minimum.
  2. Verify CWAgent is installed for memory metrics.
  3. Re-evaluate with a 14-30 day window.
```

## End-to-end right-sizing walkthrough (fleet of 5 instances)

This example walks through the complete workflow for a small fleet:
analyze metrics, classify each instance, calculate savings, and emit
batched migration steps.

**Fleet profile:**

| Instance | Type | Workload | CPU avg | Mem avg | Status |
|---|---|---|---|---|---|
| i-web01 | m5.2xlarge | Web server | 3.2% | 28% | Overprovisioned |
| i-api02 | m5.xlarge | API server | 45% | 60% | Well-sized, Graviton candidate |
| i-build03 | t3.large | CI runner | 85% (credit-starved) | 50% | Credit exhaustion |
| i-db04 | r5.2xlarge | PostgreSQL | 42% | 68% | Optimized |
| i-legacy05 | m5.large | Unknown (idle) | 0.3% | N/A | Idle |

**Step 1 — Pull metrics for all instances (14-30 day window):**
```bash
for instance in i-web01 i-api02 i-build03 i-db04 i-legacy05; do
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=$instance \
    --start-time $(date -d '-14 days' +%FT%TZ) \
    --end-time $(date +%FT%TZ) --period 3600 \
    --statistics Average --output json
done
```

**Step 2 — Classify each instance:**

- i-web01: FURTHER_OPTIMIZATION_AVAILABLE — downsize m5.2xlarge → m5.large
- i-api02: FURTHER_OPTIMIZATION_AVAILABLE — Graviton m5.xlarge → m7g.xlarge
- i-build03: FURTHER_OPTIMIZATION_AVAILABLE — credit exhaustion, t3.large → m6i.large
- i-db04: OPTIMIZED — well-sized, no Graviton (PostGIS x86 dep)
- i-legacy05: FURTHER_OPTIMIZATION_AVAILABLE — idle, stop instance

**Step 3 — Calculate fleet savings:**
```
i-web01:    m5.2xlarge → m5.large     saving $210.24/mo
i-api02:    m5.xlarge → m7g.xlarge    saving $23.36/mo
i-build03:  t3.large → m6i.large      ~cost-neutral (perf win)
i-db04:     no change                 $0
i-legacy05: stop                      saving $70.08/mo

Fleet monthly saving: $303.68
Fleet annual saving: $3,644.16
```

**Step 4 — Emit batched migration steps (max 5 per batch):**

Batch 1 (all 5 instances, sorted by savings):

```text
FLEET RIGHT-SIZING SUMMARY
Instances evaluated: 5
FURTHER_OPTIMIZATION_AVAILABLE: 4
OPTIMIZED: 1
Total monthly saving: $303.68
Total annual saving: $3,644.16

Per-instance recommendations:
1. i-web01:    FURTHER_OPTIMIZATION_AVAILABLE — downsize m5.2xl → m5.lg ($210.24/mo)
2. i-api02:    FURTHER_OPTIMIZATION_AVAILABLE — Graviton m5.xl → m7g.xl ($23.36/mo)
3. i-build03:  FURTHER_OPTIMIZATION_AVAILABLE — t3.lg → m6i.lg (perf, ~neutral cost)
4. i-legacy05: FURTHER_OPTIMIZATION_AVAILABLE — stop ($70.08/mo)
5. i-db04:     OPTIMIZED — no change

BATCH EXECUTION (in order of risk, lowest first):
Step 1: Stop i-legacy05 (zero risk, immediate saving)
Step 2: Downsize i-web01 (LOW risk, web server stateless)
Step 3: Migrate i-build03 (LOW risk, CI runner stateless)
Step 4: Graviton migration i-api02 (MEDIUM risk, requires AMI + app testing)

CONFIRM: Execute batch 1 (4 instances, $303.68/mo saving)?
Proceed? (yes/no)
```

**Step 5 — Post-change verification (7-day window):**
```bash
# Verify all changed instances are healthy
for instance in i-web01 i-api02 i-build03; do
  echo "=== $instance ==="
  aws ec2 describe-instances --instance-ids $instance \
    --query 'Reservations[0].Instances[0].{State:State.Name,Type:InstanceType}'
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=$instance \
    --start-time $(date -d '-7 days' +%FT%TZ) \
    --end-time $(date +%FT%TZ) --period 3600 \
    --statistics Average,Maximum --output json
done
```

If any instance shows CPU > 80% sustained or errors post-change, roll
back by reverting to the original instance type:
```bash
aws ec2 stop-instances --instance-ids <instance>
aws ec2 modify-instance-attribute --instance-id <instance> \
  --instance-type "{\"Value\": \"<original-type>\"}"
aws ec2 start-instances --instance-ids <instance>
```

---

## Error Handling, Edge Cases, and Decision Trees

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for CPUUtilization | `len(Datapoints) == 0` | Instance may be stopped. Check `describe-instances` state. If stopped, skip. |
| CWAgent `mem_used_percent` absent | `list-metrics --namespace CWAgent` returns no memory metrics | CWAgent not installed or not configured for memory. For downsize candidates, emit NEED_MORE_INFO. Upsize can proceed on CPU alone (MEDIUM confidence). |
| Datapoints present but span < 14 days | Datapoint range < 14 days | NEED_MORE_INFO. Observation window too short for right-sizing. |
| CPUCreditBalance absent (non-t-family instance) | `list-metrics` returns no CPUCreditBalance | Expected for non-burstable instances. Not an error — skip Step 5. |
| CloudWatch API throttling (`Throttling` error) | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). Fall back to 7-day window, flag LOW-confidence. |

### Compute Optimizer failures

| Failure mode | Detection | Handling |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `"status": "Inactive"` | Enable: `aws compute-optimizer update-enrollment-status --status Active`. Until enabled, proceed with CloudWatch + CWAgent only. |
| Empty `instanceRecommendations` | `len(instanceRecommendations) == 0` | Instance is Optimized or not yet analyzed. Cross-check `lastRefreshTimestamp`; if > 30 days, treat as stale. |
| `AccessDeniedException` for `compute-optimizer:*` | API error | Add `compute-optimizer:GetEC2InstanceRecommendations`. Proceed without cross-check; surface the gap. |
| Finding `NotOptimized` (no recommendation) | Finding type is empty or "NotOptimized" | No Compute Optimizer finding. Proceed with CloudWatch-driven analysis. |

### EC2 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-instances` returns empty | Instance does not exist | Skip entirely. Surface as BLOCKED. |
| `modify-instance-attribute` fails with `IncorrectInstanceState` | API error | Instance must be stopped before modify. Stop first, retry. |
| `modify-instance-attribute` fails with `InvalidParameterValueException` for type | API error | Requested instance type not available in this AZ. Check `describe-instance-types-offerings`. |
| `stop-instances` fails with `OperationNotPermitted` | API error | Termination protection or stop protection enabled. Disable protection first. |
| `run-instances` for Graviton fails with `Unsupported` | API error | Requested arm64 AMI / instance type not available in this AZ. Verify AMI architecture matches instance type. |

### Savings Plan lookup failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-savings-plans` returns empty | No active Savings Plans | Proceed with On-Demand pricing. No SP adjustment needed. |
| `describe-savings-plans` AccessDenied | API error | IAM role lacks `savingsplans:DescribeSavingsPlans`. Proceed with On-Demand pricing; surface that SP coverage is unverified. |
| Instance Savings Plan tied to a specific family | Plan committed to m5 family | Cross-family migration (m5 to c5) loses SP coverage. Surface as a cost: the SP commitment continues to charge even though the instance moved. |

### Instance is part of an Auto Scaling Group

Cannot `modify-instance-attribute` directly. Right-size the ASG Launch
Template, then refresh instances. Individual instance metrics may be
skewed by ASG-driven scale events — pull metrics at the ASG level.

**Detection:**
```bash
aws autoscaling describe-auto-scaling-instances --instance-ids i-0abc123
```

If the instance is part of an ASG:
1. Recommend updating the Launch Template with the new instance type.
2. Do NOT modify the running instance directly.
3. Surface as "ASG-managed — update Launch Template and refresh."

### Graviton with Docker containers

| Behaviour | Impact |
|---|---|
| Single-arch (amd64) Docker image | Must rebuild for arm64. |
| Multi-arch Docker image | Pull arm64 variant automatically. |
| Docker image with native binaries | Binaries must be arm64-compiled. |

**Checking Docker image architecture:**
```bash
docker manifest inspect <image>:<tag> | jq '.manifests[].platform.architecture'
# If only "amd64" appears, the image needs rebuilding.
# If "arm64" appears, the multi-arch image supports Graviton.
```

### Database with low CPU but high memory

CPU avg 5% but memory avg 80% means the buffer cache is active. NOT a
downsize candidate. Compute Optimizer may say Overprovisioned (CPU-
based) but cross-check with CWAgent overrides. If memory > 60%, the
instance is right-sized (memory is doing work). NEVER downsize a
database based on CPU alone.

### Right-sizing decision tree

```
Is the instance running?
├── NO (stopped) → Skip. Emit BLOCKED with note "instance stopped."
└── YES → Is observation window >= 14 days?
    ├── NO → NEED_MORE_INFO. Wait for 14+ days.
    └── YES → Is CPU < 5% AND Network < 10 MB/h AND Disk < 100 ops/s
              for 14+ days?
        ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (idle).
        │         Check termination protection. Recommend stop/terminate.
        └── NO → Is CPU < 30%?
            ├── YES → Is CWAgent memory < 50%?
            │   ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (downsize).
            │   └── NO (memory > 50%) → Is workload a database or cache?
            │       ├── YES → OPTIMIZED. Memory is buffer cache.
            │       └── NO → Evaluate workload-specific rules.
            └── NO (CPU > 30%) → Is CPU > 70% sustained?
                ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (upsize).
                └── NO (30-70%) → Well-utilized. Check other dimensions:
                    ├── Is instance 2+ gen old? → Generation upgrade
                    ├── Is x86_64 AND Graviton-compatible? → Graviton
                    ├── Is t-family with credit exhaustion? → Migrate
                    └── All pass → OPTIMIZED
```

Post-tree overrides (always take precedence):

| Condition | Override |
|---|---|
| CWAgent memory > 85% sustained | Do NOT downsize regardless of CPU. Upsize memory. |
| Database workload with memory > 60% | Do NOT downsize. Memory is buffer cache. |
| Compute Optimizer finding = `Underprovisioned` | Tree output overridden. Upsize is mandatory. |
| Instance is part of an ASG | Do NOT modify directly. Update Launch Template. |
| Termination protection = true | Do NOT stop/terminate without unblocking first. |
| Active Savings Plan tied to current family | Cross-family migration loses coverage. Surface cost. |

### Extended NEVER list

- NEVER assume CWAgent is installed. Check `list-metrics --namespace
  CWAgent` first. If absent, memory data is unavailable.
- NEVER downsize a database based on low CPU. Databases use memory for
  buffer cache — low CPU + high memory = the cache is working.
- NEVER modify an instance that is part of an Auto Scaling Group
  directly. Update the Launch Template instead.
- NEVER enable Unlimited on a t-family instance without checking whether
  the workload is spiking (Unlimited is good) or sustained-high
  (m-family migration is better).
- NEVER migrate to Graviton without testing on a staging arm64 instance
  first.
- NEVER recommend a generation upgrade without checking EBS-optimized
  status.
- NEVER trust a single 14-day window as permanent. Re-evaluate quarterly.
- NEVER ignore Spot interruption history when right-sizing Spot instances.
- NEVER right-size without checking active Savings Plans.
- NEVER batch-modify more than 5 instances in a single operation.
- NEVER skip the CONFIRM gate before stop, modify, or terminate.
- NEVER recommend hibernation without verifying prerequisites
  (EBS-backed, root volume >= RAM size, supported instance family).
