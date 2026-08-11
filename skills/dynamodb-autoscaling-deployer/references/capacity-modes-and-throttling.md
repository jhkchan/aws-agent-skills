# Capacity Modes and Throttling — DynamoDB Auto-Scaling Deployer

Deep reference on DynamoDB capacity modes (on-demand vs provisioned),
the mode-switch lifecycle, throttle metrics, and monitoring patterns.
Loaded on demand by the skill.

## Capacity modes overview

DynamoDB supports two capacity modes:

| Mode | Billing | Scaling | Cost model |
|---|---|---|---|
| PROVISIONED | Per capacity unit-hour (RCU/WCU) | Manual or auto-scaling | Lower cost for steady workloads |
| ON-DEMAND (PAY_PER_REQUEST) | Per request unit | Instant, automatic | Higher per-unit cost, no idle cost |

## On-demand mode

In on-demand mode, DynamoDB instantly allocates capacity for any
read/write request. There is no provisioning, no auto-scaling policy,
and no throttle risk under normal conditions.

**Key characteristics:**
- Capacity is allocated per-request (no pre-provisioning).
- Scales to double the previous peak traffic instantly.
- No scaling policy configuration needed.
- Cost is per read/write request unit (higher than provisioned for
  steady workloads).

**When to use:**
- New workloads with unknown traffic patterns.
- Spiky, unpredictable workloads.
- Short-lived workloads (dev/test, event-driven).

## Provisioned mode with auto-scaling

In provisioned mode, you specify RCU/WCU and DynamoDB reserves that
capacity. Auto-scaling adjusts the provisioned values based on target
utilization.

**Key characteristics:**
- You pay for provisioned capacity whether or not it is consumed.
- Auto-scaling adjusts RCU/WCU within Min/Max bounds.
- Lower cost for steady-state workloads (you can tune to ~70%
  utilization).
- Requires scaling policy configuration for table and each GSI.

**When to use:**
- Steady, predictable workloads.
- Cost-optimized production workloads.
- Workloads where capacity planning is possible.

## Mode switch lifecycle

```text
PROVISIONED (with auto-scaling policies)
  → policies: 2 scalable targets (table RCU/WCU) + N GSI targets
  → policies: 2 scaling policies (table) + N GSI policies
  → all active and managing capacity

Switch to ON-DEMAND:
  aws dynamodb update-table --table-name <name> --billing-mode PAY_PER_REQUEST
  → ALL scalable targets and scaling policies are DETACHED
  → DynamoDB switches to per-request capacity allocation
  → no auto-scaling configuration needed

Switch back to PROVISIONED:
  aws dynamodb update-table --table-name <name> --billing-mode PROVISIONED
  → table returns to provisioned mode with STATIC capacity
  → scalable targets and policies are NOT re-attached
  → must re-register targets and re-create policies from scratch
```

**Key implication:** switching modes is destructive to auto-scaling
configuration. Document all scaling parameters (Min/Max, TargetValue,
cooldowns) before switching to on-demand.

## Capacity mode auto-switching (2024-2025)

DynamoDB can now automatically switch between on-demand and
provisioned modes based on usage patterns:

- Analyzes 24-hour usage windows.
- Recommends or applies the cost-optimal mode.
- Requires opt-in (not enabled by default).
- Useful for workloads with diurnal traffic patterns (high during
  day, low at night).

**Enable auto-switching (where available):**

```bash
aws dynamodb update-table \
  --table-name my-table \
  --billing-mode PROVISIONED_AND_ON_DEMAND_AUTO_SWITCH
```

**Warning:** auto-switching to on-demand will detach all scaling
policies. Auto-switching back to provisioned will NOT re-attach
them. If you use auto-switching, document your scaling parameters.

## Throttling

Throttling occurs when consumed capacity exceeds provisioned capacity.
Each throttled request returns a `ProvisionedThroughputExceededException`.

### Throttle causes

| Cause | Description |
|---|---|
| Under-provisioning | Provisioned capacity too low for the workload |
| Hot partitions | Uneven key distribution concentrates load on few partitions |
| Auto-scaling lag | Traffic burst exceeds scale-out speed (ScaleOutCooldown too high) |
| MaxCapacity reached | Auto-scaling hit the ceiling and cannot scale further |
| GSI not auto-scaled | GSI capacity is static while table is auto-scaled |

### CloudWatch metrics for throttle detection

| Metric | Description | Alert threshold |
|---|---|---|
| `ThrottledRequests` | Count of throttled requests | > 0 (any throttle is actionable) |
| `ConsumedReadCapacityUnits` | Actual RCU consumed | Compare to ProvisionedReadCapacityUnits |
| `ConsumedWriteCapacityUnits` | Actual WCU consumed | Compare to ProvisionedWriteCapacityUnits |
| `ProvisionedReadCapacityUnits` | Current provisioned RCU | Should track consumed closely |
| `ProvisionedWriteCapacityUnits` | Current provisioned WCU | Should track consumed closely |
| `ReadThrottleEvents` | Read-side throttle events | > 0 |
| `WriteThrottleEvents` | Write-side throttle events | > 0 |

### Throttle alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name dynamodb-throttle-my-table \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=my-table \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:alerts
```

### Consumed-vs-provisioned dashboard

Monitor the gap between consumed and provisioned capacity:

```
Consumed / Provisioned = Utilization

If utilization > 80% consistently:
  → auto-scaling is not keeping up
  → check ScaleOutCooldown (may be too high)
  → check MaxCapacity (may be too low)
  → consider on-demand mode

If utilization < 30% consistently:
  → over-provisioned
  → lower MinCapacity
  → consider lower TargetValue
```

## GSI-specific throttling

GSIs have their own capacity and can throttle independently of the
table. Common scenarios:

| Scenario | Table | GSI | Result |
|---|---|---|---|
| Table auto-scaled, GSI not | Scales fine | Static capacity | GSI queries throttle |
| Both auto-scaled correctly | Scales fine | Scales fine | No throttle |
| Hot key on GSI | Fine | Throttles on specific partition | GSI-specific throttle |
| Write burst to table | Scales write | GSI write capacity may lag | GSI write throttle |

**Key rule:** ALWAYS configure auto-scaling for EVERY GSI, not just
the table. A table with 3 GSIs needs 8 total scaling configurations.

## References

- [DynamoDB capacity modes](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html)
- [DynamoDB metrics](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [Capacity mode auto-switching](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html)
- [GSI best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes.html)
