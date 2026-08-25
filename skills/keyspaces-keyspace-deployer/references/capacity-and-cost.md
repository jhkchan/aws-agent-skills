# Capacity Modes and Cost Model — Keyspaces Keyspace Deployer

Deep reference on Keyspaces capacity modes (on-demand vs provisioned),
the RU-based cost model, the crossover analysis for switching modes,
auto-scaling configuration for provisioned tables, and CloudWatch
metrics for capacity monitoring. Loaded on demand by the skill — kept
out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Capacity mode fundamentals

### On-demand (PAY_PER_REQUEST)

On-demand mode charges per request unit (RU) consumed. There is no
minimum commitment and no capacity planning required.

| Property | Value |
|---|---|
| Read RU price | ~$1.25 per million read RUs |
| Write RU price | ~$2.50 per million write RUs |
| Minimum capacity | None (zero to billions of RUs) |
| Best for | Unpredictable, spiky, or new workloads |
| Billing | Per-request (pay only for what you consume) |

One read RU = one strongly consistent read of up to 4 KB (or two
eventually consistent reads). One write RU = one write of up to 1 KB.

### Provisioned (PROVISIONED)

Provisioned mode charges per capacity unit-hour regardless of usage.

| Property | Value |
|---|---|
| Read capacity unit price | ~$0.0001484 per RCU-hour |
| Write capacity unit price | ~$0.0002968 per WCU-hour |
| Minimum capacity | 1 RCU / 1 WCU |
| Best for | Steady, predictable workloads |
| Billing | Per-capacity-unit-hour (reserved whether used or not) |

One read capacity unit (RCU) = one strongly consistent read per second
of up to 4 KB. One write capacity unit (WCU) = one write per second of
up to 1 KB.

### Switching modes

```bash
# Switch from on-demand to provisioned
aws keyspaces update-table \
  --keyspace-name my_keyspace \
  --table-name my_table \
  --capacity-spec '{
    "throughputMode": "PROVISIONED",
    "provisionedThroughput": {
      "readCapacityUnits": 500,
      "writeCapacityUnits": 1000
    }
  }'

# Switch from provisioned to on-demand
aws keyspaces update-table \
  --keyspace-name my_keyspace \
  --table-name my_table \
  --capacity-spec '{"throughputMode": "PAY_PER_REQUEST"}'
```

Switching takes effect immediately. You can switch once per table per
billing period without penalty, but frequent switching causes billing
surprises.

## The on-demand vs provisioned crossover

The crossover point is where provisioned becomes cheaper than on-
demand. This depends on sustained utilization.

```text
Crossover analysis (write capacity example):
  Provisioned: $0.0002968 per WCU-hour
  On-demand:   $2.50 per million write RUs

  If 1 WCU is utilized 100% for 1 hour:
    Provisioned cost:  $0.0002968 (flat)
    On-demand cost:    $0.009 per 3600 writes = ~$0.009
    → Provisioned is 30x cheaper at 100% utilization

  If 1 WCU is utilized 15% for 1 hour (540 writes):
    Provisioned cost:  $0.0002968 (flat)
    On-demand cost:    540 * $0.0000025 = $0.00135
    → Provisioned is still cheaper at 15% utilization

  If 1 WCU is utilized 5% for 1 hour (180 writes):
    Provisioned cost:  $0.0002968 (flat)
    On-demand cost:    180 * $0.0000025 = $0.00045
    → On-demand is cheaper below ~10% sustained utilization
```

**Rule of thumb:** the crossover is at approximately 10-15% sustained
utilization of provisioned capacity. Above this threshold, provisioned
(with auto-scaling) is cheaper. Below it, on-demand is cheaper.

## Workload-based mode selection

```text
Workload profile:
  ├── New workload, unknown traffic → on-demand for 1-2 months
  │     → switch to provisioned + auto-scaling once patterns emerge
  │
  ├── Spiky / unpredictable (10x peaks) → on-demand
  │     → provisioned would need high max capacity = expensive
  │
  ├── Steady, predictable → provisioned + auto-scaling
  │     → cheapest option for sustained traffic
  │
  ├── Low traffic (< 100 RUs/sec average) → on-demand
  │     → minimum provisioned cost exceeds on-demand cost
  │
  └── High traffic (> 10,000 RUs/sec sustained) → provisioned + auto-scaling
        → significant savings over on-demand at scale
```

## Auto-scaling for provisioned mode

Auto-scaling adjusts provisioned capacity based on target tracking.
It uses Application Auto Scaling with the `cassandra` service
namespace.

### Registering scalable targets

```bash
# Register write capacity as scalable (min: 100, max: 5000)
aws application-autoscaling register-scalable-target \
  --service-namespace cassandra \
  --resource-id keyspace/my_keyspace/table/my_table \
  --scalable-dimension cassandra:table:WriteCapacityUnits \
  --min-capacity 100 \
  --max-capacity 5000

# Register read capacity as scalable (must be registered separately)
aws application-autoscaling register-scalable-target \
  --service-namespace cassandra \
  --resource-id keyspace/my_keyspace/table/my_table \
  --scalable-dimension cassandra:table:ReadCapacityUnits \
  --min-capacity 100 \
  --max-capacity 5000
```

### Target tracking policies

```bash
# Write capacity auto-scaling (target 70% utilization)
aws application-autoscaling put-scaling-policy \
  --policy-name my-table-write-autoscaling \
  --service-namespace cassandra \
  --resource-id keyspace/my_keyspace/table/my_table \
  --scalable-dimension cassandra:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "CassandraWriteCapacityUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

### Cooldown tuning

| Parameter | Default | Recommended | Rationale |
|---|---|---|---|
| ScaleOutCooldown | 60s | 60s | Scale out fast to handle bursts before throttling occurs |
| ScaleInCooldown | 300s | 300s | Scale in slowly to avoid flapping during brief traffic dips |
| TargetValue | 70% | 50-70% | Lower target = more headroom but higher cost; higher target = cheaper but closer to throttling |

### Auto-scaling limits

- Minimum capacity: 1 unit
- Maximum capacity: configurable (default soft limit: 40,000 per
  table per region)
- Scaling step: auto-scaling adjusts in steps of ~10-20% of current
  capacity
- Scale-out time: 1-5 minutes (CloudWatch alarm + cooldown + scaling
  activity)
- Scale-in time: 5-15 minutes (longer cooldown to prevent flapping)

## CloudWatch metrics for capacity monitoring

| Metric | Unit | Description |
|---|---|---|
| `ConsumedReadCapacityUnits` | Count | RUs consumed by reads (per-minute sum or average) |
| `ConsumedWriteCapacityUnits` | Count | RUs consumed by writes |
| `ProvisionedReadCapacityUnits` | Count | Configured read capacity (provisioned mode) |
| `ProvisionedWriteCapacityUnits` | Count | Configured write capacity (provisioned mode) |
| `ReadThrottleEvents` | Count | Read requests throttled (provisioned mode, exceeded capacity) |
| `WriteThrottleEvents` | Count | Write requests throttled |
| `Storage` | Bytes | Total table storage |
| `SystemErrors` | Count | Server-side errors |

### Monitoring consumed vs provisioned

```bash
# Compare consumed vs provisioned write capacity (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Cassandra \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=Keyspace,Value=my_keyspace Name=TableName,Value=my_table \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1

aws cloudwatch get-metric-statistics \
  --namespace AWS/Cassandra \
  --metric-name ProvisionedWriteCapacityUnits \
  --dimensions Name=Keyspace,Value=my_keyspace Name=TableName,Value=my_table \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

If `ConsumedWriteCapacityUnits` consistently exceeds 70% of
`ProvisionedWriteCapacityUnits`, either increase provisioned capacity
or let auto-scaling handle it.

If `WriteThrottleEvents` > 0, the provisioned capacity is too low.
Either increase capacity, enable auto-scaling, or switch to on-demand.

## Terraform capacity example

```hcl
resource "aws_keyspaces_table" "events" {
  keyspace_name = aws_keyspaces_keyspace.app.name
  table_name    = "user_events"

  schema_definition {
    column {
      name = "user_id"
      type = "uuid"
    }
    column {
      name = "event_time"
      type = "timestamp"
    }
    partition_key {
      name = "user_id"
      type = "uuid"
    }
    clustering_key {
      name    = "event_time"
      type    = "timestamp"
      order_by = "DESC"
    }
  }

  capacity_specifier {
    throughput_mode = "PROVISIONED"
    read_capacity_units  = 500
    write_capacity_units = 1000
  }

  point_in_time_recovery_enabled = true

  encryption_specification {
    type                 = "CUSTOMER_MANAGED_KEYS"
    kms_key_identifier   = aws_kms_key.keyspaces.arn
  }
}

# Auto-scaling on write capacity
resource "aws_appautoscaling_target" "write" {
  service_namespace  = "cassandra"
  resource_id        = "keyspace/${aws_keyspaces_keyspace.app.name}/table/${aws_keyspaces_table.events.table_name}"
  scalable_dimension = "cassandra:table:WriteCapacityUnits"
  min_capacity       = 100
  max_capacity       = 5000
}

resource "aws_appautoscaling_policy" "write" {
  name               = "write-autoscaling"
  service_namespace  = "cassandra"
  resource_id        = aws_appautoscaling_target.write.resource_id
  scalable_dimension = "cassandra:table:WriteCapacityUnits"
  policy_type        = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "CassandraWriteCapacityUtilization"
    }
  }
}
```

## Expert heuristic: on-demand vs provisioned RU crossover (moved from SKILL.md)

The capacity mode decision is the primary cost lever. The crossover
point where provisioned becomes cheaper than on-demand depends on
workload predictability.

```text
Workload profile analysis:
  ├── Unpredictable / spiky / new workload → on-demand (no capacity planning)
  │     on-demand: $1.25 per million read RUs, $2.50 per million write RUs
  │
  ├── Steady, predictable traffic → provisioned with auto-scaling
  │     provisioned: $0.0001484 per read capacity unit-hour
  │                 $0.0002968 per write capacity unit-hour
  │     → crossover at ~10-15% sustained utilization of provisioned capacity
  │
  └── Hybrid: start on-demand, switch to provisioned after traffic stabilizes
        → on-demand for first 1-2 months (understand traffic)
        → switch to provisioned with auto-scaling once patterns emerge
```

**Key implication:** the crossover is roughly at 10-15% sustained
utilization. If provisioned capacity units are utilized more than 15%
of the time on average, provisioned is cheaper. Below 15%, on-demand is
cheaper. For new workloads with unknown traffic, start on-demand and
switch to provisioned after 1-2 months once traffic patterns stabilize.
Monitor `ConsumedReadCapacityUnits` and `ConsumedWriteCapacityUnits` to
make the data-driven switch.

## Step 10 — CloudWatch metrics and observability (moved from SKILL.md)

Keyspaces emits CloudWatch metrics automatically (no enable needed).
Key metrics for monitoring and auto-scaling:

| Metric | Description | Use case |
|---|---|---|
| `ConsumedReadCapacityUnits` | RUs consumed by reads | Capacity planning, auto-scaling trigger |
| `ConsumedWriteCapacityUnits` | RUs consumed by writes | Capacity planning, auto-scaling trigger |
| `ProvisionedReadCapacityUnits` | Configured read capacity | Provisioned mode monitoring |
| `ProvisionedWriteCapacityUnits` | Configured write capacity | Provisioned mode monitoring |
| `Storage` | Total table storage (bytes) | Cost monitoring |
| `SystemErrors` | Server-side errors | Error monitoring |
| `UserErrors` | Client-side errors (bad CQL) | Application debugging |
| `ConnectionAttempts` | CQL connection attempts | Connectivity monitoring |
| `SuccessfulRequestCount` | Successful CQL requests | Throughput monitoring |
| `SuccessfulConnectionCount` | Established CQL connections | Pool monitoring |

```bash
# Monitor consumed write capacity (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Cassandra \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=Keyspace,Value=my_app_keyspace Name=TableName,Value=user_events \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum Average \
  --region us-east-1
```

## Step 11 — Auto-scaling for provisioned mode (moved from SKILL.md)

For provisioned capacity tables, auto-scaling adjusts capacity units
based on utilization. Target tracking scales based on a target
utilization percentage of consumed vs provisioned RUs.

```bash
# Enable auto-scaling on write capacity (target 70% utilization)
aws application-autoscaling register-scalable-target \
  --service-namespace cassandra \
  --resource-id keyspace/my_app_keyspace/table/user_events \
  --scalable-dimension cassandra:table:WriteCapacityUnits \
  --min-capacity 100 \
  --max-capacity 5000

aws application-autoscaling put-scaling-policy \
  --policy-name user-events-write-autoscaling \
  --service-namespace cassandra \
  --resource-id keyspace/my_app_keyspace/table/user_events \
  --scalable-dimension cassandra:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "CassandraWriteCapacityUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

# Repeat for read capacity (scalable-dimension: ReadCapacityUnits)
```

**Scale-in vs scale-out cooldowns:** scale-out (60s) is faster than
scale-in (300s) to handle bursts quickly while avoiding flapping during
traffic dips.

