# Stream Mode and Scaling — Kinesis Stream Deployer

Deep reference on provisioned vs on-demand capacity mode internals,
shard count management, update-shard-count behavior, on-demand auto-
scaling mechanics, mode switching, and cost crossover analysis. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Provisioned mode internals

In provisioned mode, each shard provides fixed throughput capacity:

| Dimension | Per-shard limit |
|---|---|
| Write data rate | 1 MiB/sec |
| Write record rate | 1,000 records/sec |
| Read data rate (shared) | 2 MiB/sec total across all GetRecords consumers |
| Read data rate (enhanced fan-out) | 2 MiB/sec per registered consumer |
| Maximum record size | 1 MiB (before base64 encoding) |
| Maximum number of shards | 10,000 per stream (soft limit; request increase) |

### Shard count sizing formula

```text
shard_count = max(
  ceil(expected_write_mib_per_sec / 1),
  ceil(expected_write_records_per_sec / 1000)
)
```

**Example:** Write throughput of 5.5 MiB/sec, 4,200 records/sec:
- Data dimension: ceil(5.5 / 1) = 6 shards
- Record dimension: ceil(4200 / 1000) = 5 shards
- Required: max(6, 5) = 6 shards
- With 25% headroom: ceil(6 × 1.25) = 8 shards

### When the record-count limit dominates

Small, frequent records (e.g., IoT telemetry at 100 bytes each) hit the
1,000 records/sec limit well before the 1 MiB/sec data limit. Always
evaluate BOTH dimensions.

```text
Example: 100-byte records
  1 MiB / 100 bytes = ~10,485 records possible per MiB
  But record limit is 1,000 records/sec
  → Record limit is reached at ~100 KB/sec of data
  → Need many more shards for high-frequency small records
```

## update-shard-count behavior (provisioned mode)

Scaling shard count in provisioned mode uses `update-shard-count`:

```bash
aws kinesis update-shard-count \
  --stream-name my-data-stream \
  --target-shard-count 10 \
  --scaling-type UNIFORM_SCALING \
  --region us-east-1
```

### Scaling mechanics

| Operation | What happens | Impact |
|---|---|---|
| Scale UP (more shards) | Shard splitting: each existing shard splits into N | Hash key range redistributed; existing consumers see rebalancing |
| Scale DOWN (fewer shards) | Shard merging: adjacent shards merge | Hash key range consolidated; consumers must re-discover shards |
| Scaling type | `UNIFORM_SCALING` (the only supported type) | Uniform redistribution of hash keys |

### Scaling best practices

- **Do not scale by more than 2x in a single operation.** Large
  increases cause more disruption during the split. Scale incrementally.
- **Scaling is asynchronous.** The stream remains ACTIVE but consumers
  may see brief rebalancing.
- **KCL auto-rebalances.** If using the Kinesis Client Library, workers
  automatically pick up new shards after a split.
- **Manual consumers must re-list shards.** If not using KCL, the
  consumer must call `ListShards` to discover the new shard layout.

### Monitoring shard count changes

```bash
aws kinesis describe-stream-summary \
  --stream-name my-data-stream \
  --query 'StreamDescriptionSummary.OpenShardCount' \
  --region us-east-1 --output text
```

## On-demand mode internals

In on-demand mode, Kinesis automatically manages shard count based on
traffic. The operator does not specify or manage shards.

### Auto-scaling behavior

- **Initial capacity:** On-demand streams start with capacity equivalent
  to 4 shards (~4 MiB/sec write, ~4,000 records/sec).
- **Scale-up trigger:** If traffic exceeds the current capacity for more
  than a few minutes, Kinesis adds shards automatically.
- **Scale-up factor:** Scales to accommodate up to 200% of the prior
  30 minutes' peak traffic.
- **Scale-down:** Gradually reduces shards when traffic drops (after a
  cooldown period to avoid flapping).
- **Max capacity:** 50,000 records/sec and 50 MiB/sec default (soft
  limit; request increase via Support).

### When on-demand makes sense

| Scenario | Recommendation |
|---|---|
| New workload, no traffic data | On-demand (eliminates guesswork) |
| Spiky/unpredictable traffic | On-demand (auto-scales with spikes) |
| Low average throughput (< 1 MiB/sec) | On-demand (cheaper than idle provisioned shards) |
| Steady, predictable, > 3 MiB/sec | Provisioned (cheaper at scale) |
| Strict cost control needed | Provisioned (fixed cost per shard-hour) |

## Mode switching

You can switch between provisioned and on-demand using
`update-stream-mode`:

```bash
aws kinesis update-stream-mode \
  --stream-arn arn:aws:kinesis:us-east-1:123456789012:stream/my-data-stream \
  --stream-mode-details StreamMode=ON_DEMAND \
  --region us-east-1
```

### Switching constraints

- **Throttled:** You can switch modes at most once every 15 minutes.
- **Shard count on switch to provisioned:** When switching FROM on-demand
  TO provisioned, the current shard count (auto-managed) becomes the
  starting provisioned shard count. Verify it is appropriate.
- **Shard count on switch to on-demand:** Shard count becomes irrelevant;
  Kinesis takes over scaling.
- **Cost model change:** The billing model changes immediately. Switching
  to on-demand starts per-GB charges; switching to provisioned starts
  per-shard charges.

### Recommended workflow for new workloads

```text
1. Start in ON_DEMAND mode (eliminates shard sizing guesswork)
2. Monitor CloudWatch metrics for 2-4 weeks:
   - IncomingBytes (write throughput)
   - IncomingRecords (write record count)
   - WriteProvisionedThroughputExceeded (should be 0 in on-demand)
3. After 2-4 weeks, evaluate cost:
   - If steady throughput > ~3 MiB/sec → switch to PROVISIONED
   - If still bursty/low → stay on-demand
4. If switching to provisioned, size shards from observed peak:
   shard_count = max(ceil(peak_mib/sec), ceil(peak_records/1000)) × 1.25
```

## Cost crossover analysis

### Pricing (us-east-1, approximate — verify current pricing)

| Component | Provisioned | On-demand |
|---|---|---|
| Per shard-hour | ~$0.015 | N/A |
| Per stream-hour | N/A | ~$0.04 |
| Per GB ingested (PUT) | ~$0.014 | ~$0.029 |
| Per consumer-shard-hour (enhanced fan-out retrieval) | ~$0.013 | ~$0.013 |
| Per million GET requests (GetRecords) | ~$0.0007 | ~$0.0007 |

### Crossover calculation

```text
Given:
  T = sustained write throughput in MiB/sec
  S_provisioned = ceil(T)  (shards needed)

Hourly cost (provisioned):
  = S_provisioned × $0.015 + (T × 3600 / 1024) × $0.014
  = ceil(T) × $0.015 + T × 0.0492

Hourly cost (on-demand):
  = $0.04 + (T × 3600 / 1024) × $0.029
  = $0.04 + T × 0.1019

Crossover (where provisioned_hourly < on_demand_hourly):
  At T = 2 MiB/sec: provisioned = $0.079, on-demand = $0.244 → provisioned
  At T = 1 MiB/sec: provisioned = $0.064, on-demand = $0.142 → provisioned
  At T = 0.5 MiB/sec: provisioned = $0.057, on-demand = $0.091 → provisioned
  At T = 0.1 MiB/sec: provisioned = $0.051, on-demand = $0.050 → ~equal

Note: crossover depends on exact pricing, which varies by region and
over time. Always verify current AWS pricing for your region.
```

**Key insight:** at very low throughput (< 0.1 MiB/sec), on-demand is
slightly cheaper because you are not paying for idle provisioned shards.
At moderate throughput (> 0.5 MiB/sec steady), provisioned is often
cheaper because the per-GB PUT cost in on-demand is roughly 2x the
provisioned per-GB PUT cost. The real advantage of on-demand is NOT
cost — it is operational simplicity (no shard management, no throttle
risk from under-provisioning).

## Retention period and cost

Retention period affects cost for both modes:

| Retention | Cost impact |
|---|---|
| 24 hours (default) | Included in base cost |
| 24-8760 hours (up to 365 days) | Additional per-shard-hour charge for long-term retention |

```bash
# Check current retention period
aws kinesis describe-stream-summary \
  --stream-name my-data-stream \
  --query 'StreamDescriptionSummary.RetentionPeriodHours' \
  --region us-east-1 --output text
```

**Best practice:** set retention to the consumer's maximum tolerable
downtime plus a buffer (e.g., if consumers can be down 4 hours, set
retention to 6-8 hours). Longer retention costs more but provides a
larger replay window for consumer recovery.

## Terraform examples

```hcl
# Provisioned stream
resource "aws_kinesis_stream" "provisioned" {
  name             = "my-data-stream"
  shard_count      = 5
  retention_period = 168

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "GetRecords.IteratorAgeMilliseconds",
    "WriteProvisionedThroughputExceeded",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = {
    Environment = "production"
  }
}

# On-demand stream
resource "aws_kinesis_stream" "on_demand" {
  name             = "my-on-demand-stream"
  retention_period = 168

  stream_mode_details {
    stream_mode = "ON_DEMAND"
  }

  tags = {
    Environment = "production"
  }
}
```

Note: In Terraform, `shard_count` is required by the provider schema even
for on-demand streams. Set it to a reasonable value; it is ignored at
runtime when `stream_mode = "ON_DEMAND"`.
