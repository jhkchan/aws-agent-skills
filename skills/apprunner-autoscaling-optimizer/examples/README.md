# End-to-end usage scenario: apprunner-autoscaling-optimizer

A walkthrough showing the skill analyzing an App Runner service for
cost optimization, identifying concurrency as overprovisioned and
recommending a 50% increase with a projected 19% cost savings. Contrasted
with the OPTIMIZED case where the service configuration already matches
the traffic pattern.

## Input (user prompt)

> We have an App Runner service `prod-api-service` that costs
> $1,200/month. Concurrency is 100, MinSize 1, MaxSize 25. We handle
> 8M requests/month with avg 2.3 instances. CPU 35%, memory 30%.
> Can we reduce cost?

```json
{
  "Service": "prod-api-service",
  "Region": "us-east-1",
  "AutoScalingConfiguration": {
    "MinSize": 1,
    "MaxSize": 25,
    "Concurrency": 100
  },
  "InstanceConfiguration": {
    "Cpu": "1 vCPU",
    "Memory": "2 GB"
  },
  "Metrics": {
    "RequestCount": "8,000,000/month",
    "AvgInstanceCount": 2.3,
    "PeakInstanceCount": 6,
    "AvgCPUUtilization": "35%",
    "AvgMemoryUtilization": "30%",
    "PeakConcurrentRequestsPerInstance": 42,
    "LatencyP95": "280ms",
    "5xxResponseCount": 12
  },
  "TrafficPattern": "dynamic (3x peak during business hours)",
  "CurrentMonthlyCost": "$1,200"
}
```

## Skill output

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
       --auto-scaling-configuration-arn <new-arn>
  3. Monitor for 7 days (latency p95, 5xx rate, instance count)
  4. If latency p95 increases > 20%, revert to concurrency 100
CURRENT_MONTHLY_COST: $1,200/month
PROJECTED_MONTHLY_COST: $970/month
TRAFFIC_PATTERN: dynamic (3x peak during business hours)
RISK: MODERATE
NOTES:
  - CPU at 35% with concurrency 100 means projected CPU at 150 is ~52%.
    Still within safe range (< 70%).
  - MaxSize reduced from 25 to 10 — peak of 6 instances * 1.5 headroom = 9.
    MaxSize 10 is sufficient.
  - If latency degrades, consider upgrading to 2 vCPU / 4 GB instead
    of reverting concurrency.
```

## Contrast — OPTIMIZED case (well-configured service)

For `prod-web-service` with concurrency 80, MinSize 1, MaxSize 10,
CPU 45%, memory 38%, and peak concurrent requests 72 per instance:

```text
TARGET: prod-web-service (region: us-east-1)
VERDICT: OPTIMIZED
REASON: All optimization dimensions are within target. Concurrency 80
        matches observed peak (72). MinSize 1 matches steady-state.
        CPU 45%, memory 38%. No VPC egress. Health check 10s.
RECOMMENDATION: (none — service is optimized)
ESTIMATED_SAVINGS: $0/month
CURRENT_MONTHLY_COST: $850/month
PROJECTED_MONTHLY_COST: $850/month
TRAFFIC_PATTERN: static (consistent 24/7)
RISK: N/A
NOTES:
  - Re-evaluate quarterly or when traffic pattern changes.
  - Monitor for CPU > 70% sustained — would indicate concurrency
    too high or instance type needs upgrading.
```

## What the skill caught that a generic assistant misses

1. **Observed vs configured concurrency analysis.** A generic assistant
   sees concurrency 100 and CPU 35% and says "looks healthy." The skill
   computes that peak concurrent requests per instance is 42, meaning 58%
   of provisioned capacity is unused — a clear concurrency increase
   opportunity.

2. **Projected CPU at new concurrency.** A generic assistant recommends
   increasing concurrency without projecting the CPU impact. The skill
   calculates that at concurrency 150, CPU would be ~52% (35% * 150/100),
   which is within safe range.

3. **MaxSize right-sizing.** A generic assistant ignores MaxSize. The
   skill flags that MaxSize 25 is excessive for a peak of 6 instances
   and recommends 10.

4. **Rollback plan.** A generic assistant does not provide a revert path.
   The skill includes the revert step and the threshold for reverting
   (latency p95 increase > 20%).

5. **Instance type alternative.** A generic assistant does not consider
   the instance type dimension. The skill notes that if latency degrades
   at higher concurrency, upgrading the instance type is an alternative
   to reverting.

6. **Cost-per-request context.** A generic assistant does not compute
   the cost per request. The skill projects the monthly savings and the
   percentage reduction.

7. **Health check analysis.** A generic assistant omits health check
   tuning. The skill includes health check interval in the optimization
   dimensions.

## Slash-command invocation

```
/aws:optimize-apprunner-autoscaling
```

## CLI routing

```bash
node cli/bin/cli.js route "optimize app runner prod-api-service"
# [Phase: Optimize | Skills routed: apprunner-autoscaling-optimizer]
```

## Live-account follow-up (optional, requires AWS CLI)

After applying the new concurrency setting:

```bash
# Monitor instance count reduction
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name InstanceCount \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average \
  --profile default

# Check latency did not degrade
aws cloudwatch get-metric-statistics \
  --namespace AWS/AppRunner \
  --metric-name Latency \
  --dimensions Name=ServiceId,Value=<service-id> \
  --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average \
  --profile default

# Verify cost reduction in Cost Explorer
aws ce get-cost-and-usage \
  --filter '{"Dimensions":{"Key":"Service","Values":["App Runner"]}}' \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --time-period Start=2026-08-01,End=2026-09-01 \
  --profile default
```
