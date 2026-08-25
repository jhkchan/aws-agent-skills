# Advanced Patterns — Auto Scaling Policy Deployer

## Reasoning framework (why the provisioning order matters)

Auto Scaling policies look like "a rule that adds or removes capacity"
but the underlying model has four traps:

1. **Multiple scaling policies on the same metric fight each other.**
   Target tracking on CPU and step scaling on CPU both emit scale
   activities against the same capacity dimension. The ASG honors
   whichever alarm fires first; alarms enter conflicting states
   (target tracking ALARM while step scaling OK), producing
   oscillation. Use ONE policy type per metric dimension.

2. **Target tracking creates its own CloudWatch alarms.** Operators
   sometimes hand-author an alarm for the same metric the target
   tracking policy already manages. The two alarms double-fire on the
   same threshold breach. Target tracking's internal alarms are visible
   via `describe-alarms` and prefixed with the policy name — never
   hand-author a duplicate.

3. **Step scaling with a missing datapoint never fires.** A step
   scaling alarm with insufficient data points enters
   `INSUFFICIENT_DATA` and produces no scaling activity. Operators
   assume "no alarm = healthy" when in fact the metric isn't being
   emitted. Always set `TreatMissingData` explicitly.

4. **Predictive scaling, warm pool, capacity rebalance, and Mixed
   Instances Policy have their own silent-failure modes.** Predictive
   scaling needs 24h+ of CloudWatch data or forecasts are empty; warm
   pool instances that fail launch-template health checks silently fall
   back to cold start; capacity rebalance is a no-op on an On-Demand-only
   ASG; Mixed Instances Policy with the wrong allocation strategy
   produces unexpected instance-type selection.

## Expert heuristic: the dual-policy trap

The most dangerous scaling misconfiguration: two scaling policies on
the SAME metric dimension.

```text
Operator thinks:               What actually happens:
CPU target tracking 50% +      Both policies' alarms evaluate the same
CPU step scaling alarm 70%  →  metric; target tracking scales out at 50%,
                               step alarm fires at 70%, both activities
                               land on the same ASG; on cooldown, target
                               tracking scales back in while step alarm
                               is still ALARM; ASG oscillates.
```

The correct model: ONE reactive policy per metric dimension. If you
need both proactive and reactive scaling on CPU, use predictive
scaling (proactive) + target tracking (reactive), NOT two reactive
policies. The tell-tale signal in CloudWatch: two `ScalingPolicies`
for the same ASG both keyed on the same metric name.

## Expert heuristic: predictive scaling's history requirement

Predictive scaling looks like "ML forecasts your traffic." Two
operational truths are routinely missed:

1. **Predictive scaling needs >= 24h of CloudWatch data.** A fresh ASG
   or one with sparse traffic has empty forecasts. The `LoadMetric`
   (typically `CPUUtilization`) must have at least one full day of
   datapoints. Operators enable predictive scaling on day 1, see no
   forecasts, and assume the feature is broken. Remedy: check
   `describe-scaling-policies` for empty `LoadForecast` datapoints;
   wait 24h before validating.

2. **`Mode` controls whether capacity is pre-provisioned.** The default
   `ForecastOnly` emits forecasts but does NOT provision capacity —
   operators read "predictive scaling enabled" as "scaling is
   happening." `ForecastAndScale` is required for actual
   pre-provisioning. Verify the mode with `describe-scaling-policies`.

## Expert heuristic: warm pool drain race and capacity rebalance

The warm pool holds pre-initialized instances to speed scale-out. Two
race conditions are routinely missed:

1. **Capacity rebalance can drain the warm pool prematurely.** When a
   Spot Instance interruption is signaled, capacity rebalance launches
   a replacement from the warm pool — but the warm pool's `MinSize` is
   the buffer for scale-out, not for Spot replacement. Operators set
   `WarmPoolMinSize=0`, a Spot interruption drains the pool, and the
   next scale-out falls back to cold start. Remedy: set
   `WarmPoolMinSize >= 1` on Spot-backed ASGs.

2. **Instance refresh consumes the warm pool's instances.** A rolling
   refresh pulls instances from the warm pool to satisfy
   `MinHealthyPercentage`. Without a warm pool checkpoint, the refresh
   depletes the buffer. Remedy: enable warm pool BEFORE triggering
   instance refresh, and set `InstanceWarmup` >= the application's
   health-check grace period.

## Recent AWS features

- **Predictive scaling (ML-based forecast)**: `policy-type
  PredictiveScaling` with `MetricSpecifications`, `Mode`
  (ForecastOnly | ForecastAndScale), and `MaxCapacityBreachBehavior`
  to allow bursting above MaxSize. Requires >= 24h of `LoadMetric`
  history; verify forecast non-empty via `describe-scaling-policies`.
- **Capacity rebalance**: `--capacity-rebalance` on ASG update/create.
  Proactively launches replacement on Spot Instance interruption
  notice. No-ops silently on On-Demand-only ASGs — verify MIP presence.
- **Warm pool `InstanceReusePolicy`**: `ReuseOnScaleIn: true` returns
  terminating instances to the warm pool on scale-in events. Pair with
  `MinSize` to maintain buffer for capacity rebalance.
- **Instance refresh checkpoints**: `CheckpointPercentages` (e.g.,
  [50, 100]) with `CheckpointDelay` pause the refresh at each threshold.
  Without checkpoints, refresh runs to completion with no pause point.
- **Mixed Instances Policy allocation strategies**: `capacity-optimized`
  (recommended for Spot), `price-capacity-optimized` (cost + availability
  balance), `lowest-price` (legacy, highest interruption rate),
  `prioritized` (On-Demand fallback ordering). `capacity-optimized` with
  >= 3 overrides is the AWS-recommended production default.
- **On-Demand / Spot blend via `InstancesDistribution`**:
  `OnDemandPercentageAboveBaseCapacity` controls the On-Demand fraction
  above base; `OnDemandBaseCapacity` sets the absolute floor.
