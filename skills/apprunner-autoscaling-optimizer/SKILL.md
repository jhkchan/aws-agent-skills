---
name: apprunner-autoscaling-optimizer
description: >-
  Optimises AWS App Runner autoscaling configuration for cost and
  performance — auto-scaling configuration (MinSize/MaxSize
  provisioning), concurrency setting (requests per instance, the
  primary cost lever), CPU/memory utilization target tuning, instance
  type sizing (1 vCPU / 2 GB vs 2 vCPU / 4 GB vs 4 vCPU / 8 GB),
  health check interval tuning, scale-in cooldown, static vs dynamic
  traffic pattern analysis, cost-per-request modeling, VPC ingress/
  egress cost analysis (NAT gateway, VPC endpoints), observability
  cost, and pause/resume for non-prod cost savings. Reads App Runner
  service configuration, CloudWatch metrics, and Cost Explorer data
  to project monthly savings. Emits OPTIMIZED with specific
  recommendation and estimated savings, or
  FURTHER_OPTIMIZATION_AVAILABLE. Use when reviewing App Runner
  spend, tuning concurrency, right-sizing MinSize, or evaluating
  pause/resume for non-prod environments.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted App
  Runner service configuration and CloudWatch metrics. Live-account
  optimization uses aws apprunner describe-service, describe-auto-scaling-
  configuration, list-services, list-auto-scaling-configurations, aws
  cloudwatch get-metric-statistics (RequestCount, InstanceCount,
  CPUUtilization, MemoryUtilization, 4xx, 5xx, Latency), aws ce get-cost-
  and-usage, and aws ce get-usage-forecast (AWS CLI v2, SSO or key-based
  credentials). Pricing references us-east-1 published rates as of 2026;
  re-state regional rates from the reference matrix for other regions.
keywords:
  - App Runner
  - auto-scaling configuration
  - concurrency
  - MinSize
  - MaxSize
  - provisioned instances
  - instance type
  - 1 vCPU 2 GB
  - 2 vCPU 4 GB
  - 4 vCPU 8 GB
  - CPU utilization
  - memory utilization
  - health check
  - health check interval
  - scale-in cooldown
  - scale-out speed
  - static traffic
  - dynamic traffic
  - cost per request
  - custom domain
  - SSL certificate
  - deployment
  - VPC ingress
  - VPC egress
  - NAT gateway
  - observability cost
  - CloudWatch Logs
  - pause service
  - resume service
  - non-prod savings
  - FinOps
tags: [aws, apprunner, compute, cost-optimization, autoscaling, finops, concurrency, serverless-container, optimize]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE"
  when_to_use: >-
    Optimising App Runner autoscaling configuration, tuning concurrency
    settings, right-sizing MinSize/MaxSize, evaluating instance type
    upgrades (1/2/4 vCPU), analyzing cost-per-request, deciding whether to
    pause non-prod services, reviewing VPC egress cost, tuning health
    check intervals, or conducting a FinOps review of App Runner services.
  when_not_to_use: >-
    ECS/Fargate service autoscaling (use an ECS autoscaling skill), Lambda
    cost optimization (use lambda-cost-optimizer), EC2 instance rightsizing
    (use ec2-rightsizing-optimizer), or App Runner troubleshooting
    (deployment failures, configuration errors — use the App Runner
    troubleshooter). This skill focuses on cost-driven autoscaling
    optimization, not functional debugging.
  activation_triggers:
    - "optimise App Runner"
    - "App Runner autoscaling"
    - "App Runner concurrency"
    - "App Runner MinSize"
    - "App Runner MaxSize"
    - "App Runner instance type"
    - "App Runner cost"
    - "App Runner FinOps"
    - "App Runner pause"
    - "App Runner resume"
    - "App Runner VPC egress"
    - "App Runner health check"
    - "App Runner scale-in cooldown"
    - "App Runner cost per request"
    - "App Runner right-size"
    - "App Runner provisioned"
    - "reduce App Runner bill"
    - "App Runner non-prod savings"
  invocation_schema: >-
    Input: either (a) an App Runner service ARN + live-account context,
    (b) a service configuration document (describe-service +
    describe-auto-scaling-configuration output), OR (c) CloudWatch metrics
    (RequestCount, InstanceCount, CPUUtilization, MemoryUtilization, 4xx,
    5xx) with at least 14 days of observation. Output: a deterministic
    TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per service, where VERDICT is one of OPTIMIZED,
    FURTHER_OPTIMIZATION_AVAILABLE.
  invocation_example: >-
    # Minimal valid input (offline finding classification):
    ServiceName: prod-api-service
    AutoScalingConfiguration:
      MinSize: 1
      MaxSize: 25
      Concurrency: 100
    InstanceConfiguration:
      Cpu: 1 vCPU
      Memory: 2 GB
    Region: us-east-1
    Metrics (last 30 days):
      - RequestCount: 8,000,000/month
      - Avg InstanceCount: 2.3 (MinSize 1 is sufficient)
      - Avg CPUUtilization: 15%
      - Avg MemoryUtilization: 22%
      - 5xx rate: 0.01%
    Traffic pattern: dynamic (peak 3x baseline during business hours)
    Cost (last 30 days): $1,200/month
    Emit the standard optimization block (TARGET, VERDICT, REASON,
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).
---

# App Runner Autoscaling Optimizer

## What this skill does

Translates an App Runner service's autoscaling posture into a concrete
cost-optimization recommendation with a dollar-denominated savings
estimate. The verdict is the highest-leverage action across six dimensions
— concurrency tuning, MinSize/MaxSize right-sizing, instance type sizing,
health check optimization, VPC egress cost reduction, and pause/resume for
non-prod — applied in priority order. Always pairs the recommendation with
exact CLI commands and a projected monthly savings figure.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds (OPTIMIZED/FURTHER_OPTIMIZATION_AVAILABLE) + optimization priority | Before any recommendation |
| **Mindset** | Why concurrency is the primary lever, the MinSize baseline tradeoff, pause-for-savings | Understanding the cost model |
| **Pre-flight** | Service metadata gate — auto-scaling config, instance config, traffic pattern | Before emitting any recommendation |
| **Process** | Per-dimension analysis: concurrency, MinSize, instance type, health check, VPC, pause/resume | When choosing which optimization to apply |
| **Output format** | Structured TARGET/VERDICT/REASON/RECOMMENDATION/SAVINGS template | Formatting the response |
| **Anti-Patterns** | NEVER list — common mistakes that break scaling or increase cost | Review before risky changes |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPTIMIZED` | All optimization dimensions checked; service configuration matches traffic pattern with no actionable savings > 5% | Emit confirmation, monitoring plan |
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has actionable savings >= 5% or a structural change (pause/resume, instance type, concurrency) is recommended | Emit recommendation, CLI steps, estimated savings |

**Optimization priority (apply in this order, each may yield independent
savings):**

1. **Pause/resume for non-prod** — if the service is dev/staging/QA and
   runs 24/7, pausing outside business hours saves 100% of compute cost
   (~70% of total App Runner bill). Highest single-action savings.
2. **Concurrency tuning** — the primary lever. Higher concurrency = fewer
   instances for the same traffic = lower cost. But higher concurrency
   increases per-instance latency and memory pressure. Find the sweet spot.
3. **MinSize right-sizing** — MinSize = always-provisioned baseline. For
   static traffic, set MinSize to the steady-state instance count. For
   dynamic traffic, set MinSize to 0 (scale to zero) or 1 (always-on).
4. **Instance type sizing** — 1 vCPU/2 GB is the cheapest; 2 vCPU/4 GB
   and 4 vCPU/8 GB are 2x and 4x the cost. If CPU/memory utilization is
   low, the instance type may be overprovisioned. If concurrency is high
   and latency is elevated, a larger instance type with higher concurrency
   may be more cost-efficient.
5. **Health check optimization** — longer intervals reduce false-positive
   restarts but delay detection of unhealthy instances. Default 5s interval
   is aggressive for most workloads.
6. **VPC egress cost** — if the service uses a VPC connector, NAT gateway
   charges apply to all egress. A VPC endpoint for AWS services (S3, DynamoDB,
   etc.) eliminates NAT gateway cost for that traffic.

**Cost baselines (2026, us-east-1):**

| Instance type | Compute (per hour, provisioned) | Compute (per second, on-demand) | Best for |
|---|---|---|---|
| 1 vCPU / 2 GB | $0.063/hr | $0.0000175/s | Low-traffic, small workloads |
| 2 vCPU / 4 GB | $0.126/hr | $0.0000350/s | Standard web APIs |
| 4 vCPU / 8 GB | $0.252/hr | $0.0000700/s | CPU/memory-intensive workloads |

- On-demand billing: per-second charges only when processing requests
  (scale-to-zero eliminates idle cost).
- Provisioned billing (MinSize >= 1): per-hour charges for the baseline
  instances even when idle.
- Concurrency does not have a direct charge — it controls how many
  concurrent requests one instance handles, which indirectly controls
  how many instances the autoscaler provisions.

## Mindset

**One-line takeaway:** Concurrency is the primary cost lever. Higher
concurrency means each instance handles more simultaneous requests, so
the autoscaler provisions fewer instances — but at the cost of increased
per-request latency and memory pressure. Find the sweet spot where
concurrency is high enough to minimize instance count, but low enough to
keep latency within the SLO. Driven by three App Runner realities:

- **Concurrency determines instance count.** App Runner scales based on
  concurrent requests. With 100 concurrent requests and a concurrency
  setting of 50, the autoscaler provisions 2 instances. With a concurrency
  setting of 100, it provisions 1 instance. The cost difference is ~50%.
  The latency difference depends on the workload — a CPU-bound request at
  concurrency 100 takes longer than at concurrency 50 because the instance
  is time-slicing.

- **MinSize is the cost floor.** A MinSize of 1 means one instance is
  always provisioned and billed at the hourly rate, even at 3am with zero
  traffic. For dynamic traffic (web APIs with business-hours peaks), MinSize
  0 (scale-to-zero) eliminates the idle cost. For static traffic (always-on
  services), MinSize should match the steady-state instance count so the
  autoscaler does not over-provision.

- **Pause/resume for non-prod saves 100%.** App Runner services can be
  paused (not deleted). A paused service incurs zero compute charges. For
  dev/staging/QA environments that are only used during business hours,
  pausing outside those hours saves ~75% of the monthly compute cost
  (18 hours paused / 24 hours). Combined with scale-to-zero during business
  hours, non-prod services can run at a fraction of production cost.

## Pre-flight: service metadata gate

Run before classification. Misclassifying these produces wrong
recommendations.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws apprunner describe-service --service-arn <arn>` — capture
   `ServiceName`, `Status`, `InstanceConfiguration` (Cpu, Memory),
   `HealthCheckConfiguration` (Protocol, Interval, Timeout,
   HealthyThreshold, UnhealthyThreshold, Path), `NetworkConfiguration`
   (EgressConfiguration for VPC), `AutoScalingConfigurationSummary`
   (AutoScalingConfigurationArn).
2. Resolve the auto-scaling configuration:
   `aws apprunner describe-auto-scaling-configuration \
   --auto-scaling-configuration-arn <arn>` — capture `MinSize`, `MaxSize`,
   `Concurrency`.
3. `aws cloudwatch get-metric-statistics` for the service over the last
   14-30 days:
   - `RequestCount` (sum, 5-minute period) — traffic pattern
   - `InstanceCount` (average, 5-minute period) — actual provisioned count
   - `CPUUtilization` (average, 5-minute period) — instance sizing signal
   - `MemoryUtilization` (average, 5-minute period) — concurrency sizing signal
   - `4xxResponseCount` and `5xxResponseCount` (sum, 5-minute period) — health
   - `Latency` p50/p95/p99 (average, 5-minute period) — concurrency sizing
4. `aws ce get-cost-and-usage` — filter by `Service=App Runner` and the
   specific service tag or resource ARN for the last 30 days.
5. `aws ce get-usage-forecast` — project next 30 days based on historical
   patterns.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Service configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws apprunner describe-service --service-arn
<arn> --output json and re-plan.`

| Service attribute | Effect on optimization |
|---|---|
| `Status: PAUSED` | No compute charges. Resume-related recommendation only. |
| `MinSize: 0` (scale-to-zero) | Already optimized for idle cost. Check if cold-start latency is acceptable. |
| `MinSize >= 1` | Baseline compute cost. Check if MinSize matches steady-state instance count. |
| `Concurrency: 1` (minimum) | Maximum instance count = maximum cost. Almost always overprovisioned. |
| `Concurrency: 1000` (maximum) | Minimum instance count = minimum cost. Check if latency is within SLO. |
| `CPUUtilization < 20%` (sustained) | Instance type may be overprovisioned. |
| `CPUUtilization > 70%` (sustained) | Instance type may be underprovisioned, or concurrency too high. |
| `MemoryUtilization > 80%` (sustained) | Concurrency too high or instance memory too low. Risk of OOM. |
| `5xxResponseCount` spikes | Possible OOM from high concurrency or slow health checks. |
| VPC connector with NAT gateway | Egress cost on all outbound traffic. |
| `HealthCheckConfiguration.Interval: 1` | Aggressive health checking. May cause false-positive restarts. |
| Custom domain with managed certificate | Negligible compute overhead. No optimization needed. |

## Process — optimization analysis (apply in priority order)

### Step 0: Expert knowledge — non-obvious App Runner autoscaling behaviors

These behaviors are easy to misjudge without operational App Runner
experience. Each changes a recommendation if ignored:

- **Concurrency is the primary lever, not instance type.** Doubling
  concurrency from 50 to 100 halves the instance count for the same traffic.
  This saves ~50% of compute cost. Doubling the instance type (1 vCPU to 2
  vCPU) doubles the per-instance cost but does not reduce instance count
  (the autoscaler still provisions based on concurrency). The only reason
  to increase instance type is if the higher concurrency would cause
  CPU/memory exhaustion on the smaller instance.

- **Scale-to-zero (MinSize 0) eliminates idle cost.** App Runner bills
  per-second for on-demand usage (requests being processed). With MinSize 0
  and no traffic, the service scales to zero and compute charges stop. The
  tradeoff is cold-start latency on the first request after idle (typically
  5-30 seconds depending on container image size).

- **MinSize >= 1 means always-provisioned billing.** Each provisioned
  instance is billed per-hour regardless of traffic. A MinSize of 2 on a
  1 vCPU/2 GB service costs $0.126/hr * 730 hr/month = ~$92/month in idle
  compute. If the service has predictable business-hours traffic, set
  MinSize to 0 and accept the cold start, or set MinSize to 1 for a
  balance.

- **App Runner concurrency is not the same as Lambda concurrency.** Lambda
  concurrency = number of simultaneous invocations. App Runner concurrency
  = number of simultaneous HTTP requests per instance. The total concurrent
  capacity = instance count * concurrency setting. The autoscaler adjusts
  instance count to keep concurrent requests per instance at or below the
  concurrency setting.

- **Higher concurrency increases latency.** At concurrency 100, a single
  instance handles 100 simultaneous requests. If each request is CPU-bound
  (1 second of processing), the effective latency is ~100 seconds (serial
  processing on 1 vCPU) unless the workload is I/O-bound (async I/O allows
  true concurrency). Benchmark with realistic load before increasing
  concurrency.

- **Deployment pauses autoscaling.** During a deployment, App Runner
  replaces instances with the new version. The autoscaler does not add or
  remove instances during this window. High-traffic deployments may
  temporarily increase latency because the new instances start from zero.

- **Health check interval affects scale-out speed.** App Runner checks
  instance health every `Interval` seconds. If an instance becomes
  unhealthy, the service waits `Interval * UnhealthyThreshold` seconds
  before replacing it. A 1-second interval with 5 unhealthy-threshold = 5
  seconds detection. A 10-second interval = 50 seconds detection. Tune
  for your workload's tolerance.

- **Scale-in cooldown (default 60s) prevents flapping.** After the
  autoscaler removes an instance, it waits 60 seconds before removing
  another. This prevents rapid scale-in/scale-out cycles (flapping) on
  bursty traffic. A longer cooldown saves cost (instances stay longer at
  lower counts) but delays response to traffic drops. A shorter cooldown
  saves less but responds faster.

- **VPC egress cost via NAT gateway.** If the App Runner service uses a
  VPC connector to access private resources (RDS, ElastiCache, internal
  APIs), all outbound traffic from the VPC to the internet goes through
  the NAT gateway at $0.045/GB processed + $0.045/GB data transfer. For
  high-egress workloads, this can exceed the compute cost. Use VPC
  endpoints for AWS service traffic (S3, DynamoDB, SQS, etc.) to bypass
  the NAT gateway.

- **Custom domain SSL has negligible compute overhead.** App Runner
  manages the certificate (via AWS Certificate Manager) and terminates
  TLS at the load balancer. The TLS handshake adds < 1ms per request.
  No optimization needed for custom domains.

- **Observability cost from CloudWatch Logs.** App Runner sends
  application logs to CloudWatch Logs by default. For high-traffic
  services, log ingestion can be significant (~$0.50/GB ingested). If
  the service logs verbose output (request/response bodies, debug logs),
  reducing log verbosity or sampling can save observability cost.

- **Pause/resume is not scale-to-zero.** Pausing a service stops all
  compute and removes the endpoint. The service configuration is
  preserved; resuming recreates the endpoint. Pause/resume is for non-
  prod environments (dev/staging/QA) that are not needed outside business
  hours. Scale-to-zero (MinSize 0) is for production services that should
  stay accessible but handle zero-traffic periods.

- **MaxSize limits burst capacity.** If MaxSize is too low, the autoscaler
  cannot provision enough instances during traffic spikes, and requests
  queue or fail with 5xx. If MaxSize is too high, the autoscaler may
  provision excessively during misconfigured scaling policies. Set MaxSize
  to 2-3x the peak observed instance count.

- **Cost-per-request analysis reveals efficiency.** Total monthly cost /
  total monthly requests = cost per request. For a $1,200/month service
  handling 8M requests, that is $0.00015/request. Benchmark against
  alternative platforms (Lambda + API Gateway, ECS/Fargate, EC2) to
  determine if App Runner is the right platform.

- **Auto-scaling configuration is versioned.** `create-auto-scaling-
  configuration` creates a new version. You then `update-service` with the
  new ARN. Old configurations can be deleted once no service references
  them.

- **App Runner v2 eliminates the VPC connector requirement for private
  networking.** The v2 architecture (2025 GA) gives each service a
  native ENI in your VPC without provisioning a separate VPC connector
  resource. This removes the connector's NAT gateway dependency for
  outbound traffic and reduces egress cost by up to 60% for
  high-egress services. Services still on the v1 architecture must
  explicitly migrate; existing VPC connectors continue to work but
  are not eligible for the cost reduction. Check `NetworkConfiguration.
  EgressConfiguration` — v2 services show `EgressType: VPC` without a
  `VpcConnectorArn`.

- **The autoscaler uses a Kubernetes-style HPA algorithm under the
  hood.** App Runner runs containers on a managed Kubernetes cluster.
  The autoscaler computes desired instance count as `desired =
  ceil(currentConcurrentRequests / concurrencySetting)`, then applies
  a stabilization window (default 60 seconds for scale-in, immediate
  for scale-out). Burst traffic within a 60-second window may not
  trigger scale-in even if the concurrent request count drops — the
  autoscaler waits to confirm the drop is sustained. This explains
  why `InstanceCount` does not track `RequestCount` perfectly in
  real-time; the stabilization window introduces lag on scale-in.

- **The concurrency-vs-CPU-utilization trade-off follows a non-linear
  curve.** Below ~70% CPU utilization, increasing concurrency yields
  near-linear cost savings (fewer instances, same throughput). Above
  ~70% CPU, the OS scheduler overhead grows super-linearly: context-
  switching and memory pressure cause per-request latency to spike
  2-3x even though throughput is maintained. The sweet spot for CPU-
  bound workloads is 50-65% CPU utilization at the target concurrency.
  For I/O-bound workloads (API calls, DB queries), the ceiling is
  higher (~80% CPU) because threads spend time blocked on network I/O,
  not consuming CPU cycles. Check `CPUUtilization` at the current
  concurrency before recommending an increase.

- **Pause/resume has a hidden cost beyond zero compute.** Resuming a
  paused service pulls the container image from ECR again (cold pull,
  not cached), taking 30-120 seconds depending on image size. For
  images > 500 MB, the resume delay can exceed 2 minutes.
  Additionally, the first few requests after resume have elevated
  latency (~2x p95) as the JIT compiler and connection pools warm up.
  For dev/staging environments, schedule resume 5 minutes before the
  team needs access. The ECR data transfer for re-pulling is typically
  <$1/month but is not zero.

### Step 1: Pause/resume analysis (non-prod only)

If the service is in a non-prod environment (dev/staging/QA):

```
If service runs 24/7:
  Recommend pause outside business hours (e.g., 7pm-7am + weekends)
  Savings = monthly compute * (paused_hours / total_hours)
  Typical: 18hr/day paused on weekdays + 48hr weekends = ~75% savings

If service is already paused or uses MinSize 0:
  No pause/resume recommendation. Proceed to concurrency analysis.
```

**CLI for pause/resume automation:**

```bash
# Pause (using EventBridge scheduled rule)
aws apprunner pause-service --service-arn <arn>

# Resume
aws apprunner resume-service --service-arn <arn>
```

### Step 2: Concurrency analysis

```
current_concurrency = AutoScalingConfiguration.Concurrency
avg_concurrent_requests = max(RequestCount_per_5min / 300) (peak concurrent)
avg_instance_count = average(InstanceCount over 30 days)
observed_concurrency_per_instance = avg_concurrent_requests / avg_instance_count

If observed_concurrency_per_instance < current_concurrency * 0.5:
  → Concurrency is overprovisioned (instances are underutilized)
  → Recommend: increase concurrency to reduce instance count
  → New concurrency = current_concurrency * 1.5 (gradual increase)
  → Savings = (current_instances - projected_instances) * hourly_rate * 730

If observed_concurrency_per_instance > current_concurrency * 0.8:
  AND CPUUtilization > 60% OR MemoryUtilization > 75%:
  → Concurrency is near the limit; increasing further risks latency/OOM
  → Recommend: increase instance type (more CPU/memory per instance)
  → Then increase concurrency to match

If latency p95 > SLO target:
  → Concurrency may be too high for the workload
  → Recommend: decrease concurrency to reduce per-request latency
  → Cost increases but stays within SLO
```

### Step 3: MinSize/MaxSize right-sizing

```
If MinSize > 0:
  steady_state_instances = percentile(InstanceCount, 10) (low-traffic baseline)
  If MinSize > steady_state_instances:
    → MinSize is overprovisioned; reduce to steady_state_instances
    → If steady_state_instances = 0: recommend MinSize 0 (scale-to-zero)

If MaxSize < peak(InstanceCount):
  → MaxSize is too low; instances are hitting the cap during peaks
  → Recommend: increase MaxSize to peak(InstanceCount) * 1.5

If MaxSize > peak(InstanceCount) * 3:
  → MaxSize is excessively high; no immediate cost impact but risk of
    runaway scaling
  → Recommend: reduce MaxSize to peak(InstanceCount) * 2
```

### Step 4: Instance type analysis

```
cpu_avg = average(CPUUtilization over 30 days)
mem_avg = average(MemoryUtilization over 30 days)

If cpu_avg < 25% AND mem_avg < 40%:
  AND current instance type > 1 vCPU / 2 GB:
  → Instance type is overprovisioned
  → Recommend: downgrade to 1 vCPU / 2 GB
  → Savings = (current_hourly - new_hourly) * instance_count * 730

If cpu_avg > 70% OR mem_avg > 80%:
  → Instance type is underprovisioned
  → Recommend: upgrade to next size
  → Also consider: increasing concurrency with larger instance type
```

### Step 5: Health check optimization

```
If HealthCheckConfiguration.Interval < 5:
  AND InstanceRestartCount is high:
  → Health check interval is too aggressive; false-positive restarts
  → Recommend: increase interval to 10-15s

If HealthCheckConfiguration.Timeout > Interval * 0.5:
  → Timeout is too close to interval; health checks may always timeout
  → Recommend: set timeout to Interval * 0.3

If HealthCheckConfiguration.UnhealthyThreshold < 3:
  → Single failed check triggers replacement; too sensitive
  → Recommend: set to 3-5
```

### Step 6: VPC egress cost analysis

```
If NetworkConfiguration.EgressConfiguration uses NAT gateway:
  nat_cost = CostExplorer filter "NatGateway" for the VPC
  If nat_cost > compute_cost * 0.3:
    → NAT gateway cost is significant
    → Recommend: add VPC endpoints for AWS service traffic
    → Savings = nat_cost * (aws_service_traffic_fraction)
```

### Step 7: Synthesize — emit verdict

If any dimension yielded actionable savings >= 5%:
→ `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE`

If all dimensions are optimal (no actionable savings >= 5%):
→ `VERDICT: OPTIMIZED`

## Output format (per service)

```text
TARGET: <service-name> (region: <region>)
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <one-line summary of the primary finding>
RECOMMENDATION:
  - <specific recommendation 1>
  - <specific recommendation 2>
ESTIMATED_SAVINGS: $<monthly_savings>/month (<percentage>% of current spend)
MIGRATION_STEPS:
  1. <CLI command or action>
  2. <CLI command or action>
  3. <verification step>
CURRENT_MONTHLY_COST: $<amount>
PROJECTED_MONTHLY_COST: $<amount>
TRAFFIC_PATTERN: <static | dynamic | bursty | intermittent>
RISK: <LOW | MODERATE | HIGH>
NOTES: <caveats, monitoring recommendations>
```

### Worked example — concurrency tuning (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: prod-api-service (region: us-east-1)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Concurrency 100 is overprovisioned — observed peak is 42 concurrent
        requests per instance, meaning 58% of provisioned capacity is unused.
RECOMMENDATION:
  - Increase concurrency from 100 to 150 (gradual 50% increase)
  - Current avg 2.3 instances → projected 1.5 instances at concurrency 150
  - Monitor latency p95 for 7 days post-change
ESTIMATED_SAVINGS: $230/month (19% of current compute spend)
MIGRATION_STEPS:
  1. Create new auto-scaling configuration:
     aws apprunner create-auto-scaling-configuration \
       --auto-scaling-configuration-name prod-api-service-asg-v2 \
       --min-size 1 \
       --max-size 10 \
       --concurrency 150
  2. Apply to the service:
     aws apprunner update-service \
       --service-arn arn:aws:apprunner:us-east-1:111111111111:service/prod-api-service/abc \
       --auto-scaling-configuration-arn arn:aws:apprunner:us-east-1:111111111111:autoscalingconfiguration/prod-api-service-asg-v2/1
  3. Monitor for 7 days:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/AppRunner \
       --metric-name Latency \
       --dimensions Name=ServiceId,Value=<id> \
       --statistics Average \
       --period 300 --start-time ... --end-time ...
  4. If latency p95 increases > 20%, revert to concurrency 100
CURRENT_MONTHLY_COST: $1,200/month
PROJECTED_MONTHLY_COST: $970/month
TRAFFIC_PATTERN: dynamic (3x peak during business hours)
RISK: MODERATE
NOTES:
  - Concurrency 150 is still below the workload's CPU limit (avg
    CPUUtilization at concurrency 100 is 35%; at 150 it is projected
    ~52%).
  - If latency degrades, consider upgrading to 2 vCPU / 4 GB instead
    of reducing concurrency back.
```

### Worked example — pause/resume for non-prod (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: dev-staging-service (region: us-east-1)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Service runs 24/7 in a dev environment. Pausing outside business
        hours (7pm-7am weekdays + all weekend) saves 75% of compute.
RECOMMENDATION:
  - Pause service at 7pm and resume at 7am weekdays via EventBridge
  - Pause for entire weekend (Friday 7pm to Monday 7am)
  - Use MinSize 0 during business hours for scale-to-zero on idle
ESTIMATED_SAVINGS: $540/month (75% of current compute spend)
MIGRATION_STEPS:
  1. Create EventBridge rule for pause (cron(0 19 ? * MON-FRI *)):
     aws events put-rule --name apprunner-pause-dev \
       --schedule-expression "cron(0 19 ? * MON-FRI *)"
     aws events put-targets --rule apprunner-pause-dev \
       --targets '{"Id":"1","Arn":"<pause-lambda-arn>"}'
  2. Create EventBridge rule for resume (cron(0 7 ? * MON-FRI *)):
     aws events put-rule --name apprunner-resume-dev \
       --schedule-expression "cron(0 7 ? * MON-FRI *)"
     aws events put-targets --rule apprunner-resume-dev \
       --targets '{"Id":"1","Arn":"<resume-lambda-arn>"}'
  3. Set MinSize to 0 during business hours:
     aws apprunner create-auto-scaling-configuration \
       --auto-scaling-configuration-name dev-asg-min0 \
       --min-size 0 --max-size 5 --concurrency 50
CURRENT_MONTHLY_COST: $720/month
PROJECTED_MONTHLY_COST: $180/month
TRAFFIC_PATTERN: intermittent (only used during business hours)
RISK: LOW
NOTES:
  - Pausing the service removes the endpoint. Developers must wait for
    resume (~30-60s) before accessing the service.
  - Consider a Slack bot or CLI alias for manual pause/resume on demand.
```

### Worked example — already optimal (OPTIMIZED)

```text
TARGET: prod-web-service (region: us-east-1)
VERDICT: OPTIMIZED
REASON: All optimization dimensions are within target. Concurrency 80
        matches observed peak (72 per instance). MinSize 1 matches
        steady-state. CPU 45%, memory 38%. No VPC egress. Health check
        interval 10s is appropriate.
RECOMMENDATION: (none — service is optimized)
ESTIMATED_SAVINGS: $0/month
CURRENT_MONTHLY_COST: $850/month
PROJECTED_MONTHLY_COST: $850/month
TRAFFIC_PATTERN: static (consistent 24/7)
RISK: N/A
NOTES:
  - Re-evaluate quarterly or when traffic pattern changes.
  - Monitor for CPU > 70% sustained — would indicate concurrency is
    too high or instance type needs upgrading.
  - Consider cost-per-request benchmarking against ECS/Fargate if
    monthly cost exceeds $2,000.
```

## Anti-Patterns — NEVER

- NEVER increase concurrency without monitoring latency for at least 7 days
  post-change. Higher concurrency reduces instance count but increases per-
  request latency on CPU-bound workloads. A blind increase from 50 to 200
  can degrade p95 latency by 3-5x.

- NEVER set MinSize to 0 for a production service that requires low cold-
  start latency. App Runner cold start after scale-to-zero is 5-30 seconds
  (container pull + start). For user-facing APIs, keep MinSize at 1.

- NEVER pause a production service. Pause is for non-prod only. Pausing
  removes the endpoint and takes the service offline.

- NEVER downgrade instance type based on a single day of low utilization.
  CPU/memory utilization varies by day of week and time of day. Use at
  least 14 days of data, ideally 30, to capture the full traffic cycle.

- NEVER set MaxSize below the peak observed instance count. The autoscaler
  will hit the cap and return 5xx errors during traffic spikes.

- NEVER ignore VPC egress cost. For services with a VPC connector, NAT
  gateway charges ($0.045/GB processed + $0.045/GB data transfer) can
  exceed compute cost for high-egress workloads. Use VPC endpoints for
  AWS service traffic.

- NEVER assume App Runner is the right platform for all workloads. For
  sustained high-traffic services (> $2,000/month), ECS/Fargate or EC2 may
  be more cost-efficient. Run a cost-per-request comparison.

- NEVER change concurrency, MinSize, and instance type simultaneously. Make
  one change at a time and measure the impact for 7 days before the next.
  Simultaneous changes make it impossible to attribute cost/latency
  changes to a specific dimension.

- NEVER delete an auto-scaling configuration that is still referenced by a
  service. `delete-auto-scaling-configuration` fails if the configuration
  is in use. Use `update-service` to switch to the new configuration first.

- NEVER set health check interval to 1 second unless the workload requires
  instant failure detection. A 1-second interval with a 3-second timeout
  and 3 unhealthy threshold means 3 seconds to detect a failure — but it
  also means transient latency spikes (a slow request holding the health
  check thread) trigger false-positive restarts. Use 5-10 seconds.

- NEVER reduce concurrency to reduce latency without checking if the
  workload is CPU-bound or I/O-bound. For I/O-bound workloads (API calls,
  database queries), concurrency has minimal latency impact — the instance
  handles concurrent I/O natively. For CPU-bound workloads, concurrency
  directly increases latency.

- NEVER assume scale-to-zero eliminates all cost. App Runner charges for
  container image storage in ECR and any custom domain certificate
  management. These are typically negligible (< $5/month) but not zero.

- NEVER forget that deployments pause autoscaling. During a deployment, the
  autoscaler does not add or remove instances. High-traffic deployments may
  cause temporary latency spikes. Schedule deployments during low-traffic
  windows.

- NEVER auto-execute a state-changing App Runner CLI without the CONFIRM
  gate. Changing the auto-scaling configuration affects production traffic.
  The service briefly transitions during configuration changes.

## Pre-flight safety checks (run before any optimization CLI)

- **CONFIRMATION GATE.** Before any state-changing operation
  (`update-service`, `pause-service`, `resume-service`, `create-auto-scaling-
  configuration`, `delete-auto-scaling-configuration`), emit:
  `CONFIRM: About to <operation> on <service-name> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`.

- **Capture pre-state.** Before changing the auto-scaling configuration:
  `aws apprunner describe-service --service-arn <arn> --output json >
  /tmp/<service>-pre-$(date +%s).json` AND
  `aws apprunner describe-auto-scaling-configuration --auto-scaling-
  configuration-arn <arn> --output json > /tmp/<service>-asg-$(date +%s).json`.

- **Verify the service is not mid-deployment.** `aws apprunner describe-
  service --service-arn <arn> --query 'Status'` — confirm `RUNNING` (not
  `OPERATION_IN_PROGRESS`).

- **Verify the new auto-scaling configuration exists before applying.**
  `aws apprunner describe-auto-scaling-configuration --auto-scaling-
  configuration-arn <new-arn>` — confirm it exists and has the correct
  MinSize/MaxSize/Concurrency.

- **Monitor post-change.** For 7 days after a concurrency or instance type
  change, monitor:
  - `Latency` p95 (CloudWatch)
  - `5xxResponseCount` (CloudWatch)
  - `InstanceCount` (should decrease for concurrency increase)
  - `CPUUtilization` and `MemoryUtilization` (should increase per instance)

## Recent AWS features (2024-2026)

- **App Runner v2 native VPC networking (2025 GA):** The v2
  architecture provisions a native ENI per service in your VPC without
  a separate VPC connector resource. Eliminates the NAT gateway
  dependency for outbound traffic, reducing egress cost by up to 60%.
  Existing v1 services must explicitly migrate. Check
  `NetworkConfiguration.EgressConfiguration` for `EgressType: VPC`
  without `VpcConnectorArn`.

- **VPC connector for private resources (2024 GA):** App Runner services
  can connect to private VPC resources (RDS, ElastiCache, internal APIs)
  via a VPC connector. Egress traffic goes through the VPC's NAT gateway
  unless VPC endpoints are configured.

- **Custom auto-scaling configurations (2024):** Create reusable auto-
  scaling configurations with specific MinSize, MaxSize, and Concurrency.
  Attach to multiple services for consistent scaling behavior.

- **Observability configuration (2024-2025):** Configure CloudWatch Logs
  ingestion rate, log format (JSON vs text), and trace sampling (AWS X-Ray).
  Reducing log verbosity lowers observability cost for high-traffic services.

- **Size-aware health checks (2025):** Health check grace period for new
  instances during scale-out. The service waits for the grace period before
  checking health, giving the instance time to warm up.

- **Deployment strategies (2025):** Rolling deployment (default) replaces
  instances gradually. Blue/green deployment creates a new fleet, switches
  traffic, then tears down the old fleet. Blue/green avoids the deployment-
  pauses-autoscaling issue.

- **Cost allocation tags (2024-2025):** Tag App Runner services with cost
  allocation tags for Cost Explorer filtering. Essential for multi-service
  cost attribution.

- **App Runner observability dashboard (2025):** A pre-built CloudWatch
  dashboard for App Runner services showing RequestCount, InstanceCount,
  CPU/Memory utilization, latency, and error rates. Useful for identifying
  optimization opportunities without manual metric queries.

## Domain

AWS CloudOps / App Runner Autoscaling Cost Optimization & FinOps.

## AWS documentation

- **AWS App Runner Developer Guide** — https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html
- **App Runner auto-scaling** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-autoscaling.html
- **App Runner autoscaling configuration** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-autoscaling.html#manage-autoscaling.config
- **App Runner instance configuration** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-configure.html
- **App Runner VPC networking** — https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html
- **App Runner health checks** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-configure.html#manage-configure.health
- **App Runner API Reference** — https://docs.aws.amazon.com/apprunner/latest/api/Welcome.html
- **App Runner pricing** — https://aws.amazon.com/apprunner/pricing/
- **App Runner pause/resume** — https://docs.aws.amazon.com/apprunner/latest/dg/manage-delete.html#manage-delete.pause
- **CloudWatch App Runner metrics** — https://docs.aws.amazon.com/apprunner/latest/dg/monitor-cw.html
