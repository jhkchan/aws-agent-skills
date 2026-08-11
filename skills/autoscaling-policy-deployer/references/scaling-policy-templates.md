# Scaling Policy Templates Reference

Supplementary reference for the Auto Scaling Policy Deployer skill. Use
when authoring target tracking, step scaling, scheduled scaling,
predictive scaling, warm pool, instance refresh, and Mixed Instances
Policy configurations.

## Target tracking — predefined metrics

### ASGAverageCPUUtilization (default recommendation)

```json
{
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageCPUUtilization"
  },
  "TargetValue": 50.0,
  "ScaleOutCooldown": 60,
  "ScaleInCooldown": 300
}
```

**Use when:** workload is CPU-bound (compute-heavy API, batch).
**Target guidance:** 40-60% for latency-sensitive; 60-80% for batch.

### ALBRequestCountPerTarget

```json
{
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ALBRequestCountPerTarget",
    "ResourceLabel": "app/my-alb/1234567890abcdef/targetgroup/my-tg/abcdef0987654321"
  },
  "TargetValue": 1000.0
}
```

**Use when:** workload is request-driven (web front-end, API gateway).
**ResourceLabel:** retrieve from
`aws elbv2 describe-target-groups --query 'TargetGroups[].TargetGroupArn'`
and the ALB ARN. Format: `app/<alb-name>/<alb-id>/targetgroup/<tg-name>/<tg-id>`.
**TargetValue units:** requests per instance per minute (NOT per
second). 1000 = ~16 RPS per instance.

### ASGAverageNetworkIn / ASGAverageNetworkOut

```json
{
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "ASGAverageNetworkIn"
  },
  "TargetValue": 100000000.0
}
```

**Use when:** workload is network-bound (CDN origin, streaming).
**TargetValue units:** bytes per instance per minute.

## Target tracking — custom metric

### Application-specific metric (SQS backlog per instance)

```json
{
  "CustomizedMetricSpecification": {
    "MetricName": "ApproximateNumberOfMessagesVisible",
    "Namespace": "AWS/SQS",
    "Dimensions": [{"Name": "QueueName", "Value": "my-queue"}],
    "Statistic": "Average",
    "Unit": "Count"
  },
  "TargetValue": 100.0
}
```

**Verify BEFORE attaching:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=my-queue \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

If `Datapoints` is empty, the `Dimensions` value does not match the
metric actually emitted — the policy will silently freeze capacity.

## Step scaling — alarm + step adjustments

### Scale-out policy with multiple step bounds

```json
{
  "AdjustmentType": "PercentChangeInCapacity",
  "MetricAggregationType": "Average",
  "StepAdjustments": [
    {
      "MetricIntervalLowerBound": 0,
      "MetricIntervalUpperBound": 100,
      "ScalingAdjustment": 20
    },
    {
      "MetricIntervalLowerBound": 100,
      "MetricIntervalUpperBound": 500,
      "ScalingAdjustment": 50
    },
    {
      "MetricIntervalLowerBound": 500,
      "ScalingAdjustment": 100
    }
  ]
}
```

**Important:** `MetricIntervalLowerBound`/`UpperBound` are relative to
the alarm threshold, NOT absolute metric values. If the alarm threshold
is 500 and the current metric is 700, the interval is 200 — falls in
the second step (`LowerBound=100, UpperBound=500`).

### CloudWatch alarm with explicit missing-data policy

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name my-asg-depth-high \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS --statistic Average \
  --period 60 --evaluation-periods 2 --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=my-queue \
  --treat-missing-data breaching \
  --alarm-actions arn:aws:autoscaling:<region>:<account>:scalingPolicy:...
```

**`TreatMissingData` options:**
- `breaching` — missing = alarm fires (use for scale-out)
- `notBreaching` — missing = alarm clears (use for scale-in)
- `ignore` — maintain prior state
- `missing` (default) — same as `ignore` but explicitly tracked

## Predictive scaling — MetricSpecifications

### CPU-based forecast with ForecastAndScale

```json
{
  "MetricSpecifications": [{
    "TargetValue": 40.0,
    "PredefinedMetricPairSpecification": {
      "PredefinedMetricType": "ASGCPUUtilization",
      "ResourceLabel": ""
    }
  }],
  "Mode": "ForecastAndScale",
  "SchedulingBufferTime": 300,
  "MaxCapacityBreachBehavior": "IncreaseMaxCapacity",
  "MaxCapacityBuffer": 10
}
```

**`Mode` options:**
- `ForecastOnly` — emit forecasts only, no capacity pre-provisioning
- `ForecastAndScale` — pre-provision capacity per forecast

**`MaxCapacityBreachBehavior`:**
- `HonorMaxCapacity` — never exceed MaxSize (default)
- `IncreaseMaxCapacity` — temporarily raise MaxSize by `MaxCapacityBuffer`
  when forecast demands

**Verify >= 24h history before enabling:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=my-asg \
  --start-time $(date -u -v-48H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average | jq '.Datapoints | length'
```

If datapoints < ~288 (24h of 5-min data), the forecast will be empty.

## Scheduled scaling — recurrence + timezone

### Business-hours scale-up

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-asg \
  --scheduled-action-name business-hours-scale-up \
  --recurrence "0 9 * * Mon-Fri" \
  --min-size 3 --desired-capacity 5 --max-size 10 \
  --time-zone "America/New_York"
```

### Off-hours scale-down

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name my-asg \
  --scheduled-action-name off-hours-scale-down \
  --recurrence "0 19 * * Mon-Fri" \
  --min-size 1 --desired-capacity 1 --max-size 10 \
  --time-zone "America/New_York"
```

**Cron format:** `minute hour day-of-month month day-of-week` (UTC by
default unless `--time-zone` specified). AWS cron requires the `?`
wildcard in either day-of-month OR day-of-week (use `Mon-Fri` for
day-of-week, `?` for day-of-month implicitly).

## Warm pool

### Stopped pool with reuse-on-scale-in

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name my-asg \
  --pool-state Stopped \
  --min-size 2 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'
```

**`PoolState` options:**
- `Stopped` (default) — instances pre-initialized but not billing compute
- `Running` — instances fully running (faster scale-out, higher cost)

**`InstanceReusePolicy.ReuseOnScaleIn`:** `true` returns terminating
instances to the warm pool on scale-in, preserving pre-initialized
state. Recommended for cost optimization.

## Instance refresh

### Rolling with checkpoints

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name my-asg \
  --strategy Rolling \
  --preferences '{
    "MinHealthyPercentage": 50,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [50, 100],
    "CheckpointDelay": 300,
    "SkipMatching": true
  }'
```

**`CheckpointPercentages`:** pause the refresh at each threshold. With
`[50, 100]`, the refresh pauses at 50% complete for evaluation, then at
100% before completing.

**`CheckpointDelay`:** seconds to wait at each checkpoint before
auto-resuming. Set high enough to evaluate application health.

**`SkipMatching`:** `true` skips instances whose launch template
configuration matches the current spec (faster refresh when only some
settings changed).

## Mixed Instances Policy

### On-Demand base + Spot with capacity-optimized

```json
{
  "LaunchTemplate": {
    "LaunchTemplateSpecification": {
      "LaunchTemplateName": "my-template",
      "Version": "$Default"
    },
    "Overrides": [
      {"InstanceType": "m5.large"},
      {"InstanceType": "m5a.large"},
      {"InstanceType": "m4.large"}
    ]
  },
  "InstancesDistribution": {
    "OnDemandPercentageAboveBaseCapacity": 50,
    "OnDemandBaseCapacity": 1,
    "SpotAllocationStrategy": "capacity-optimized",
    "SpotInstancePools": 3
  }
}
```

**`OnDemandBaseCapacity`:** absolute floor of On-Demand instances.
**`OnDemandPercentageAboveBaseCapacity`:** On-Demand fraction above
the base. Total On-Demand = OnDemandBaseCapacity + (DesiredCapacity -
OnDemandBaseCapacity) * OnDemandPercentageAboveBaseCapacity%.

**`SpotAllocationStrategy` options:**
- `capacity-optimized` — picks pools with deepest capacity (lowest interruption)
- `price-capacity-optimized` — balances cost and capacity
- `lowest-price` — legacy; picks cheapest pool (highest interruption)
- `prioritized` — uses override order for On-Demand fallback

**`SpotInstancePools`:** number of Spot pools to distribute across
(`lowest-price` only); ignored by `capacity-optimized`.

**`SpotMaxPrice`:** optional; omit to use On-Demand price as the ceiling
(recommended).
