# EC2 Spot Fleet Deployer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Mindset (moved from SKILL.md)

**One-line takeaway:** A Spot Fleet is a collection of Spot
Instances (and optionally On-Demand) launched from a diversified
set of instance types and Availability Zones, managed as a group
to maintain a target capacity. The allocation strategy determines
how the fleet selects pools; the fleet type determines whether AWS
maintains the capacity or fills it once.

Three misconceptions dominate Spot Fleet misdesign at provisioning
time:

- **"Just pick lowestPrice and the cheapest instances will
  appear."** They will — until capacity is reclaimed and the fleet
  collapses to a single pool. `lowestPrice` selects the lowest-
  priced pool per AZ with no diversification. If that pool is
  interrupted, the entire fleet is interrupted simultaneously.
  `priceCapacityOptimized` (the 2022 default recommendation) is
  almost always the better choice: it balances price with capacity
  availability.

- **"Spot Fleet and Auto Scaling Group are the same thing."** They
  are not. A Spot Fleet is a capacity procurement mechanism — it
  requests and replaces Spot Instances but has no scaling policies.
  An Auto Scaling Group can request Spot Instances AND scale based
  on load. Use Spot Fleet for fixed-capacity cost optimization; use
  ASG with mixed instances for elastic workloads.

- **"I only need one instance type in my fleet."** The entire point
  of a Spot Fleet is diversification. A single instance type has no
  fallback pools. If that type is reclaimed, the fleet cannot
  replace it from another pool. Always specify at least 2-3 instance
  types across multiple AZs.

## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

Spot Fleet configurations are NOT independent. Many settings are
immutable after the request is created; others silently degrade
interruption resilience. Use this graph to sequence provisioning
and debug "why is my fleet not filling?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Fleet type | IAM service role (AWSServiceRoleForEC2SpotFleet) | `maintain` continuously replaces; `request` is one-time (cannot be modified) | fleet lifecycle behavior |
| Launch template | AMI exists in the region + valid instance type | launch template is versioned; changing AMI requires a new version | standardized instance config |
| Allocation strategy | none — SpotFleetRequestConfig parameter | **CANNOT be changed after request creation** — must cancel and re-create | pool selection logic |
| Instance types (Overrides) | valid instance type + AZ combination | adding/removing types requires modifying the Spot Fleet request | diversification |
| Target capacity | positive integer (units or vCPUs or instances) | mutable for `maintain` fleets; `request` fleets fill once and stop | fleet size |
| Excess capacity termination | `TargetCapacitySpecification` set | defaults to `noTermination` (safe) or `termination` (aggressive) | capacity drift handling |
| InstanceInterruptionBehavior | valid value: stop/terminate/hibernate | **CANNOT be changed per-instance after launch** — set at request level | interruption response |
| Capacity rebalance | `maintain` fleet type + Rebalance enabled | only works with `maintain` fleets; `request` fleets ignore it | proactive rebalancing |
| Spot placement score | must be queried before fleet creation | advisory only — does not guarantee capacity | capacity-aware pool selection |
| Capacity reservations | existing ODCR in the account | must match instance type + AZ; consumed before Spot | guaranteed capacity |

**The immutable rows are the ones a baseline model misses.**
Allocation strategy and fleet type are set at request creation and
CANNOT be changed without canceling and re-creating the fleet. The
procedure below forces an explicit decision on each before the
`request-spot-fleet` call.

**Cross-dependency gotchas:**
- A `request` (one-time) fleet type CANNOT be modified after
  creation. Target capacity changes, instance type additions, and
  capacity rebalance all require a `maintain` fleet.
- Capacity rebalance requires `maintain` fleet type. Enabling it on
  a `request` fleet is silently ignored.
- Spot placement score is advisory — it scores pools but does not
  reserve capacity. The fleet may still be interrupted in a
  high-scoring pool.
- Capacity reservations (ODCR) are consumed first, but only if
  they match instance type + AZ + platform exactly.

## Expert heuristic: capacity rebalance and replacement (moved from SKILL.md)

Capacity rebalance is NOT the same as the default interruption
replacement. A baseline model conflates the two; this heuristic
separates them.

| Mechanism | When it triggers | What it does | Fleet type |
|---|---|---|---|
| Default replacement (no rebalance) | 2-minute interruption warning | Fleet requests a NEW instance from another pool, then the interrupted instance terminates | `maintain` only |
| Capacity rebalance (Rebalance) | AWS signals at-risk pool (before warning) | Fleet proactively launches a replacement BEFORE the interruption, giving more migration time | `maintain` only |
| `request` fleet | n/a | No replacement at all — fleet fills once and stops | `request` only |

**Capacity rebalance lifecycle:**
```text
AWS detects rising interruption risk in a pool
  → Rebalance Recommendation signal emitted (via EventBridge + metadata)
  → If rebalance is ENABLED:
    → Fleet launches a NEW replacement instance from a safer pool
    → Replacement becomes healthy → old instance terminates
    → Workload drains from old to new
  → If rebalance is DISABLED:
    → Wait for 2-minute interruption warning → then launch replacement
```

**Key implication:** Capacity rebalance buys time. Without it, you
get 2 minutes from the warning. With it, the rebalance signal can
come before the interruption notice — critical for stateful
workloads, ML training checkpoints, and long-running batch jobs.

**Enabling capacity rebalance (set at SpotFleetRequestConfig level):**
```json
{
  "Type": "maintain",
  "AllocationStrategy": "priceCapacityOptimized",
  "InstanceInterruptionBehavior": "terminate",
  "SpotMaintenanceStrategies": {
    "CapacityRebalance": { "ReplacementStrategy": "launch" }
  }
}
```

## Step 10 — Recent features (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **`priceCapacityOptimized` as default (Nov 2022, refined 2023-
  2024):** AWS's recommended allocation strategy. Balances price
  with capacity availability. Replaces `lowestPrice` as the default
  recommendation for most workloads.

- **Spot placement score API (2023-2024):** Pre-flight capacity
  check before fleet creation. Scores pools 1-10. Single-AZ or
  multi-AZ modes. Enables data-driven pool selection.

- **Attribute-based instance selection (2023-2024):** Use
  `InstanceRequirements` (vCPU, memory, accelerator count) instead
  of specific instance types. AWS picks any matching type,
  maximizing pool count and reducing interruption risk.

- **Capacity rebalance with `launch` strategy (2023-2024):**
  Fleet launches a replacement BEFORE terminating the old instance.
  Reduces capacity gaps during rebalancing.

- **Spot Fleet with On-Demand Capacity Reservations (2023-2024):**
  ODCR consumed first when matching instance type + AZ. Enables
  hybrid guaranteed-capacity + cost-optimization fleets.

- **Spot Fleet support for `hibernate` interruption behavior (2023-
  2024):** Instances can hibernate on interruption, preserving RAM
  state. Useful for long-running stateful workloads.
