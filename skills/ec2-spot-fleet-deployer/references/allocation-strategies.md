# Allocation Strategies Deep Dive — EC2 Spot Fleet Deployer

Detailed comparison of the four allocation strategies, their
interruption risk profiles, cost trade-offs, and workload fit.
Loaded on-demand when the operator needs to reason about which
strategy to select.

## Strategy comparison matrix

| Strategy | Selection logic | Diversification | Interruption risk | Relative cost | AWS recommendation |
|---|---|---|---|---|---|
| `priceCapacityOptimized` | Pools with best price-to-capacity ratio | Implicit (multi-pool) | Low-Medium | Low | **Default (Nov 2022+)** |
| `capacityOptimized` | Pools with most free capacity | Implicit (multi-pool) | Lowest | Medium | For long-running workloads |
| `lowestPrice` | Lowest-priced pool per AZ | None (concentrates in cheapest) | Highest | Lowest | Legacy default; avoid |
| `diversified` | Even spread across all pools | Explicit (equal weight) | Low | Medium | For maximum spread |

## priceCapacityOptimized (recommended)

**How it works:** AWS scores each pool based on both price and
available capacity. It selects pools that are both affordable AND
unlikely to be reclaimed. This avoids the trap of concentrating
in a single cheap pool that gets interrupted all at once.

**Best for:** Most workloads — web servers, batch processing,
microservices, CI/CD workers. The default recommendation since
November 2022.

**When NOT to use:** When you need absolute lowest cost regardless
of interruption risk (use `lowestPrice` with 10+ types), or when
you need maximum capacity availability regardless of cost (use
`capacityOptimized`).

**Example configuration:**
```json
{
  "Type": "maintain",
  "AllocationStrategy": "priceCapacityOptimized",
  "TargetCapacitySpecification": {
    "TotalTargetCapacity": 20,
    "DefaultTargetCapacityType": "spot"
  }
}
```

## capacityOptimized

**How it works:** AWS selects pools with the most available Spot
capacity. This minimizes interruption risk by choosing pools where
AWS has the most unused capacity. May cost slightly more than
`lowestPrice` but significantly reduces interruptions.

**Best for:** Long-running workloads where interruption cost is
high — ML training, data processing pipelines, stateful batch jobs,
CI/CD with long build times.

**When NOT to use:** When absolute lowest cost is the priority and
the workload can tolerate frequent interruptions.

**Interruption rate comparison (typical):**
- `capacityOptimized`: ~2-4% interruption rate (capacity-aware)
- `priceCapacityOptimized`: ~3-5% interruption rate (price + capacity)
- `lowestPrice`: ~5-15% interruption rate (concentrated in cheap pools)

## lowestPrice

**How it works:** AWS selects the lowest-priced Spot pool per AZ.
If the `InstancePoolsToUseCount` parameter is set (>1), it
distributes across the N cheapest pools. Without it, the entire
fleet concentrates in the single cheapest pool.

**Best for:** Cost-obsessed workloads with many (10+) instance
types and all AZs. Only viable with heavy diversification.

**Critical risk:** With `InstancePoolsToUseCount` unset (default
1), the fleet concentrates in one pool. When that pool is
reclaimed, the entire fleet is interrupted simultaneously. This
is the #1 cause of fleet-wide outages.

**When to use (rarely):** Only when you have 10+ instance types,
all AZs, and `InstancePoolsToUseCount` set to at least 3-4.

## diversified

**How it works:** AWS distributes the fleet evenly across ALL
specified pools. Each pool gets an equal share of the target
capacity. Maximum geographic and instance-type spread.

**Best for:** Workloads that need maximum spread — multi-region
deployments, compliance-driven geographic distribution, or
workloads with specific instance family requirements.

**Trade-off:** No cost optimization. You may end up paying more
than `priceCapacityOptimized` because you accept higher-priced
pools for the sake of even distribution.

## Decision framework

```text
1. Is the workload stateless and fault-tolerant?
   YES → priceCapacityOptimized (stop here — this is the default)
   NO  → continue

2. Is interruption cost > Spot savings?
   YES → capacityOptimized
   NO  → continue

3. Do you need geographic spread or specific families?
   YES → diversified
   NO  → continue

4. Is absolute lowest cost required with 10+ instance types?
   YES → lowestPrice (with InstancePoolsToUseCount >= 4)
   NO  → priceCapacityOptimized
```

## InstancePoolsToUseCount (for lowestPrice/diversified)

When using `lowestPrice`, `InstancePoolsToUseCount` controls how
many of the cheapest pools the fleet draws from:

```json
{
  "AllocationStrategy": "lowestPrice",
  "InstancePoolsToUseCount": 4
}
```

- Default (unset): 1 pool — dangerous, no diversification.
- 2-3: Better, but still concentrated.
- 4+: Recommended minimum for `lowestPrice`.
- Only valid for `lowestPrice`. `priceCapacityOptimized` and
  `capacityOptimized` ignore this parameter.

## Historical context

- Pre-Nov 2022: `lowestPrice` was the only low-cost option. Fleets
  frequently collapsed when the cheapest pool was reclaimed.
- Nov 2022: `priceCapacityOptimized` introduced. AWS recommended
  it as the new default for most workloads.
- 2023-2024: `capacityOptimized` refined with better capacity
  prediction models.
- Current (2026): `priceCapacityOptimized` remains the recommended
  default; `lowestPrice` is considered legacy.
