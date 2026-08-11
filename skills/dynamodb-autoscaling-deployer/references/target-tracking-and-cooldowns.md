# Target Tracking and Cooldowns — DynamoDB Auto-Scaling Deployer

Deep reference on target tracking scaling policy internals, cooldown
tuning, the utilization metric lifecycle, and how Application Auto
Scaling evaluates and adjusts DynamoDB capacity. Loaded on demand.

## Target tracking policy anatomy

A target tracking scaling policy adjusts capacity to keep a specific
CloudWatch metric at a target value. For DynamoDB, the predefined
metrics are:

| PredefinedMetricType | What it tracks | Resource |
|---|---|---|
| `DynamoDBReadCapacityUtilization` | Consumed RCU / Provisioned RCU (%) | Table or GSI |
| `DynamoDBWriteCapacityUtilization` | Consumed WCU / Provisioned WCU (%) | Table or GSI |

These are MANAGED metrics — Application Auto Scaling creates and
maintains the CloudWatch alarms internally. You do NOT create alarms
yourself for target tracking.

## Policy configuration fields

```json
{
  "TargetValue": 70,
  "PredefinedMetricSpecification": {
    "PredefinedMetricType": "DynamoDBReadCapacityUtilization"
  },
  "ScaleOutCooldown": 60,
  "ScaleInCooldown": 60,
  "DisableScaleIn": false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `TargetValue` | double | required | Target utilization (10-90) |
| `PredefinedMetricType` | string | required | `DynamoDBReadCapacityUtilization` or `DynamoDBWriteCapacityUtilization` |
| `ScaleOutCooldown` | integer | 60 | Seconds between scale-out actions |
| `ScaleInCooldown` | integer | 0 | Seconds between scale-in actions |
| `DisableScaleIn` | boolean | false | If true, only scales OUT (never reduces capacity) |

## How target tracking works internally

```text
1. Application Auto Scaling creates two CloudWatch alarms:
   → high alarm: triggers when utilization > TargetValue for data points
   → low alarm: triggers when utilization < TargetValue for data points

2. Every evaluation interval (~60 seconds for DynamoDB):
   → CloudWatch reports DynamoDBReadCapacityUtilization
   → if utilization > TargetValue: trigger scale-out
   → if utilization < TargetValue: trigger scale-in

3. Scale-out action:
   → calculate new capacity = current * (utilization / TargetValue)
   → clamp to MaxCapacity
   → respect ScaleOutCooldown (skip if last scale-out was < N seconds ago)
   → call UpdateTable with new RCU/WCU

4. Scale-in action:
   → calculate new capacity = current * (utilization / TargetValue)
   → clamp to MinCapacity
   → respect ScaleInCooldown
   → call UpdateTable with new RCU/WCU
```

## Cooldown tuning guide

### ScaleOutCooldown

| Value | Behavior | When to use |
|---|---|---|
| 0 | Scale out immediately | Latency-sensitive workloads, burst-tolerant |
| 60 (default) | Wait 60s between scale-outs | Standard steady-state workloads |
| 120-300 | Conservative scale-out | Workloads with metric noise or oscillation |

### ScaleInCooldown

| Value | Behavior | When to use |
|---|---|---|
| 0 (default) | Scale in immediately | Cost-optimized, steady workloads |
| 60 | Wait 60s between scale-ins | Mild oscillation protection |
| 300 | Wait 5 min between scale-ins | Highly oscillating workloads (prevents flapping) |

### DisableScaleIn

Setting `DisableScaleIn: true` means the policy ONLY scales out.
Capacity never decreases. Use when:
- You want to pre-provision for peak and avoid any risk of throttle
  during scale-in.
- You are running a load test and want capacity to ramp up but not
  down.

## Target utilization math

Application Auto Scaling calculates the desired capacity as:

```
desired_capacity = current_capacity * (actual_utilization / target_value)
```

Example with TargetValue=70 and actual utilization=85%:

```
desired = current * (85 / 70) = current * 1.21
→ capacity increases by ~21%
→ new utilization ≈ 85% / 1.21 ≈ 70% (back to target)
```

**Key implication:** target tracking is self-correcting. If the
adjustment overshoots or undershoots, the next evaluation cycle
corrects. The target value determines the STEADY-STATE utilization,
not the peak.

## Min/Max capacity envelope

The scalable target defines the bounds:

```
MinCapacity ≤ desired_capacity ≤ MaxCapacity
```

- If desired < Min: set to Min (capacity floor).
- If desired > Max: set to Max (capacity ceiling). At this point,
  throttling may occur if traffic exceeds Max capacity.

**Choosing Min:**
- Set to the minimum capacity you need during off-peak hours.
- Lower Min = lower cost during idle periods.
- Too low: cold-start latency when traffic ramps up.

**Choosing Max:**
- Set to the maximum capacity your budget allows.
- Higher Max = more headroom for traffic bursts.
- Check account-level DynamoDB throughput limits before setting Max.

## Common policy failures

| Symptom | Cause | Fix |
|---|---|---|
| Capacity stuck at Min | Utilization below target; scale-in working as expected | Lower TargetValue or accept lower cost |
| Capacity stuck at Max | Traffic exceeds MaxCapacity; scale-out capped | Increase MaxCapacity or switch to on-demand |
| Flapping (capacity oscillates) | ScaleInCooldown too low | Increase ScaleInCooldown to 60-300s |
| Throttling despite auto-scaling | ScaleOutCooldown too high; traffic bursts faster than scale-out | Lower ScaleOutCooldown, increase Min, or switch to on-demand |
| Policy not adjusting at all | Scalable target not registered; table in on-demand mode | Verify `describe-scalable-targets`; ensure PROVISIONED billing mode |

## References

- [Target tracking policies](https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-target-tracking.html)
- [DynamoDB auto-scaling](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html)
- [Application Auto Scaling cooldowns](https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-target-tracking.html#application-auto-scaling-cooldowns)
