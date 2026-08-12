# EC2 Spot Diversification and Allocation Strategy Reference

Load this reference when planning, tuning, or auditing a Spot Fleet or
ASG with Spot capacity. The tables below cover allocation strategies,
diversification math, instance family selection, and the Spot placement
score.

## Allocation strategies

| Strategy | Behavior | When to use | Cost vs interruption trade-off |
|---|---|---|---|
| `capacity-optimized` | Launches from pools with the lowest interruption rate (most spare capacity). Does NOT consider price. | Production workloads (recommended default) | Slightly higher cost, dramatically fewer interruptions |
| `capacity-optimized-prioritized` | Same as capacity-optimized, but honors the `Priority` field in Overrides when pools have equal capacity. | When you have preferred instance types but want capacity optimization | Same as above, with type preference |
| `price-capacity-optimized` (2024+) | Balances price and capacity — selects pools with low interruption rate AND low price. | When cost optimization matters but you want better than lowest-price | Middle ground |
| `diversified` | Distributes Spot Instances across all pools in the Overrides list. | When you have many pools (5+) and want even distribution | Moderate cost, moderate interruptions |
| `lowest-price` | Launches from the cheapest pool(s). `InstancePoolsToUseCount` controls how many cheapest pools. | Dev/test, stateless, interruption-tolerant workloads ONLY | Lowest cost, highest interruption rate |

**Recommendation for production:** `capacity-optimized` with 3+
instance families across 3+ AZs. The 5-8% cost premium over
`lowest-price` is offset by the 5-10x reduction in interruption
frequency.

## Diversification math

Spot pools are (instance family, AZ) combinations. Interruption rates
are roughly independent across pools. The more independent pools, the
lower the probability of simultaneous interruptions.

| Pools | P(all interrupted simultaneously) | Availability |
|---|---|---|
| 1 pool | 1-5% per hour | ~95-99% |
| 3 pools (1 family, 3 AZs) | 0.01-0.1% | ~99.5% |
| 6 pools (2 families, 3 AZs) | < 0.01% | ~99.8% |
| 9 pools (3 families, 3 AZs) | < 0.001% | ~99.9% |
| 12+ pools (4+ families, 3+ AZs) | Negligible | ~99.95%+ |

**Minimum recommendation:** 3 instance families x 3 AZs = 9 pools for
99.9% Spot availability.

## Instance family selection

Mix Intel (x86), AMD (x86), and Graviton (arm64) for true pool
independence:

| Architecture | Family examples | Spot characteristics |
|---|---|---|
| Intel x86 | `c5`, `m5`, `r5` | Mature pools; moderate interruption rates |
| AMD x86 | `c5a`, `m5a`, `r5a`, `m6a` | Often cheaper than Intel; good availability |
| Graviton (arm64) | `c6g`, `m6g`, `r6g`, `c7g`, `m7g` | Newer pools; often lower interruption rates; requires arm64 application support |

### Recommended diversification combos

**General purpose (web servers, APIs):**
```
m6a.large, m6i.large, c6g.large
across us-east-1a, us-east-1b, us-east-1c
= 9 pools
```

**Compute-optimized (batch, ML inference):**
```
c5.large, c6a.large, c6g.large
across us-east-1a, us-east-1b, us-east-1c
= 9 pools
```

**Memory-optimized (databases, caching):**
```
r5.large, r6a.large, r6g.large
across us-east-1a, us-east-1b, us-east-1c
= 9 pools
```

## Graviton (arm64) considerations

Graviton instances often have lower Spot interruption rates because the
capacity is newer and less saturated. They also offer better
price-performance for many workloads.

**Application requirements:**
- Container images must be multi-arch (or arm64-native)
- Compiled languages (Go, Rust, C++) need arm64 builds
- Interpreted languages (Python, Node.js, Ruby) work natively
- Java works (JVM is architecture-independent); verify JNI libraries
- Verify all dependencies have arm64 variants

**Testing:**
```bash
# Run an arm64 test instance
aws ec2 run-instances \
  --instance-type c6g.large \
  --image-id <arm64-ami> \
  --key-name <key> \
  --security-group-ids <sg>

# Verify the application starts and passes health checks
```

## Spot placement score

`get-spot-placement-scores` forecasts the likelihood of fulfilling a
Spot request for a given capacity in a given Region or set of AZs.

```bash
aws ec2 get-spot-placement-scores \
  --instance-types c5.large,m5.large,c6g.large \
  --target-capacity 100 \
  --target-capacity-type spot \
  --region-names us-east-1 us-east-2 us-west-2 \
  --single-availability-zone true
```

### Score interpretation

| Score | Meaning | Action |
|---|---|---|
| 10 | Highly recommended — ample capacity | Launch with confidence |
| 7-9 | Good — sufficient capacity | Launch; monitor for early interruptions |
| 4-6 | Marginal — limited capacity | Add more diversification or reduce target capacity |
| 1-3 | Poor — very likely unfulfilled | Do NOT launch; choose a different Region or instance types |

### Score usage

- Run `get-spot-placement-scores` BEFORE launching a large Spot Fleet
  (> 20 instances) to validate the Region has sufficient capacity.
- Re-run periodically (daily or weekly) — capacity changes over time.
- Use the `--single-availability-zone` flag to get per-AZ scores for
  more granular placement decisions.
- The score does NOT guarantee future availability — it is a snapshot.

## ASG capacity rebalance

The `CapacityRebalance` feature on Auto Scaling Groups proactively
monitors Spot placement risk signals. When EC2 detects that a Spot
Instance is at elevated interruption risk, the ASG:

1. Launches a replacement instance (proactive, before the 2-minute
   warning).
2. Waits for the replacement to pass health checks.
3. Then places the at-risk instance in `Terminating:Wait` (firing the
   lifecycle hook).
4. The graceful-shutdown pipeline drains the at-risk instance.

This reduces the actual interruption rate experienced by the workload
because replacements are launched BEFORE the interruption, not after.

### Enabling capacity rebalance

```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name prod-web-asg \
  --capacity-rebalance
```

### Capacity rebalance event

When capacity rebalance triggers, EventBridge emits an
`EC2 Instance Rebalance Recommendation` event (separate from the
`EC2 Spot Instance Interruption Warning`). This gives the pipeline
additional lead time (typically 5-15 minutes before the actual
interruption warning).

```json
{
  "detail-type": "EC2 Instance Rebalance Recommendation",
  "source": "aws.ec2",
  "detail": {
    "instance-id": "i-0abc123def456"
  }
}
```

Add a rule for this event to give the graceful-shutdown pipeline even
more time:

```bash
aws events put-rule \
  --name spot-rebalance-recommendation \
  --event-pattern '{
    "detail-type": ["EC2 Instance Rebalance Recommendation"],
    "source": ["aws.ec2"]
  }'
```

## Spot Fleet vs ASG with MixedInstancesPolicy

| Feature | Spot Fleet | ASG with MixedInstancesPolicy |
|---|---|---|
| Spot + On-Demand mix | Yes (via `OnDemandTargetCapacity`) | Yes (via `SpotPercentage` or `InstancesDistribution`) |
| Allocation strategies | All five strategies | All five strategies (via `SpotAllocationStrategy`) |
| Capacity rebalance | No (use ASG for this) | Yes (`CapacityRebalance`) |
| Lifecycle hooks | No | Yes |
| Health checks | EC2 health checks | EC2 or ELB health checks |
| Auto-replace interrupted instances | Yes | Yes |
| Best for | Batch, stateless, high-scale fleets | Production web/API tiers with ELB integration |

**Recommendation:** Use ASG with `MixedInstancesPolicy` for production
workloads that need ELB integration and lifecycle hooks. Use Spot Fleet
for pure compute (batch, CI/CD, data processing) where you do not need
ELB or ASG features.

## InstanceInterruptionBehavior

Set at launch. Cannot be changed for a running instance.

| Behavior | Effect | Use case |
|---|---|---|
| `terminate` (default) | Instance is terminated; EBS volumes are deleted (unless `DeleteOnTermination=false`) | Stateless workloads |
| `stop` | Instance is stopped (EBS-backed only). Can be restarted when capacity returns. EBS volumes persist. | Stateful workloads that can tolerate a cold restart |
| `hibernate` | Instance hibernates — memory state saved to EBS. Requires `--hibernate-options Configured=true` at launch. | Long-running computations that cannot easily checkpoint |

**Important:** `stop` and `hibernate` do NOT guarantee the instance will
be available later. EC2 may terminate it after the stop/hibernate if
capacity does not return. The Spot request remains active and will
attempt to restart the instance when capacity returns — but only if the
request has not expired or been cancelled.

## Spot Block deprecation (2024+)

Spot Block (1-6 hour reserved Spot capacity) is deprecated. Key facts:

- **Existing Spot Block requests** continue to function until they
  expire.
- **New Spot Block requests** are NOT accepted.
- **Alternative:** On-Demand Capacity Reservations for predictable
  capacity, or Savings Plans for cost optimization.

Do NOT plan around Spot Block. The graceful-shutdown pipeline and
diversification are the correct resilience strategies.
