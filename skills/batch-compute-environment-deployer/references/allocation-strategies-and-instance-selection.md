# Allocation Strategies & Instance Selection

## Strategy Comparison

| Strategy | Type | Description | Spot Support |
|---|---|---|---|
| BEST_FIT | EC2 | Picks the cheapest instance that fits, does not scale out | No |
| BEST_FIT_PROGRESSIVE | EC2 | Picks additional instance types beyond the cheapest to fulfill capacity | Yes |
| SPOT_CAPACITY_OPTIMIZED | EC2 | Picks spot instances from pools with lowest interruption risk | Yes |

## BEST_FIT_PROGRESSIVE Deep Dive
- Steps up instance types by price when the cheapest is unavailable
- Ideal for heterogeneous pools (m5 + c5 + r5)
- Supports launch template overrides for custom AMIs
- Min vCPUs should be 0 for cost scaling; max caps spend

## SPOT_CAPACITY_OPTIMIZED
- Uses Spot Placement Score internally to select interruption-resistant pools
- Requires spot fleet role: `arn:aws:iam::<acct>:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet`
- Always pair with an On-Demand fallback CE in the same job queue
- Fallback CE order determines priority (order 1 = primary)

## Instance Role Requirements
- EC2 CEs require an instance profile with `AmazonEC2ContainerServiceforEC2Role`
- The instance role is what allows ECS agent registration on Batch-managed instances
- Fargate CEs do NOT need an instance role (execution role instead)
---

## Expert heuristic: BEST_FIT_PROGRESSIVE for heterogeneous pools (moved verbatim from SKILL.md)

A baseline model says "use BEST_FIT." The correct heuristic recognizes
that BEST_FIT causes capacity starvation when the primary type is scarce.

```text
Instance pool: m5.large, m5.xlarge, m5.2xlarge, c5.large, c5.xlarge

BEST_FIT:
  → Packs onto fewest instances (lowest cost)
  → If m5.large unavailable, jobs WAIT (RUNNABLE stuck)
  → Good for: single instance type, predictable capacity

BEST_FIT_PROGRESSIVE:
  → Tries m5.large first; falls back to m5.xlarge, c5.large, etc.
  → Scales across MULTIPLE types simultaneously
  → Good for: heterogeneous pools, production workloads

SPOT_CAPACITY_OPTIMIZED:
  → Selects spot pools with most spare capacity
  → Minimizes interruption risk (not cost)
  → Good for: spot-based environments
```

**Key implication:** BEST_FIT_PROGRESSIVE is almost always the right
choice for EC2 environments with multiple instance types. Use
SPOT_CAPACITY_OPTIMIZED only for spot-based environments.

---

## Expert heuristic: spot capacity optimization fallback (moved verbatim from SKILL.md)

A baseline model uses spot without a fallback. The correct heuristic
pairs Spot + On-Demand compute environments in the same queue.

```text
Job Queue: production-queue (priority: 500)
  ├── CE 1 (order 1): spot-env — SPOT_CAPACITY_OPTIMIZED, max 1000 vCPUs
  └── CE 2 (order 2): ondemand-env — BEST_FIT_PROGRESSIVE, max 200 vCPUs

Behavior:
  → Batch tries spot-env first
  → If spot exhausted, jobs fall through to ondemand-env
  → On-Demand guarantees minimum throughput during spot disruption
```

