---
name: ec2-spot-fleet-deployer
description: >-
  Provisions EC2 Spot Fleets with production defaults: launch template
  configuration, Spot Fleet request (target capacity, allocation
  strategy: lowestPrice/capacityOptimized/diversified/
  priceCapacityOptimized), instance pools, fleet type
  (request/maintain), replacement strategies, capacity rebalance,
  Spot placement score, capacity reservations. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating a Spot Fleet request, choosing an allocation strategy,
  configuring instance diversification, enabling capacity rebalance,
  or integrating Spot Fleets with capacity reservations. Triggers:
  create spot fleet, EC2 Spot Fleet request, spot instance pool,
  allocation strategy, capacity rebalance, spot placement score,
  priceCapacityOptimized, lowestPrice spot, capacityOptimized spot,
  diversified spot fleet, maintain spot fleet.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with ec2, iam,
  and service-roles access. Works with Terraform
  aws_spot_fleet_request resources and CloudFormation
  AWS::EC2::SpotFleet templates.
keywords:
  - aws
  - ec2
  - spot fleet
  - spot instances
  - cloudops
  - deploy
  - provisioning
  - allocation strategy
  - lowestPrice
  - capacityOptimized
  - diversified
  - priceCapacityOptimized
  - instance pools
  - target capacity
  - capacity rebalance
  - spot placement score
  - capacity reservations
  - launch template
  - fleet type
  - maintain
tags:
  - aws
  - ec2
  - spot-fleet
  - cloudops
  - deploy
  - compute
  - provisioning
  - allocation-strategy
  - capacity-rebalance
  - launch-template
  - spot-instances
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - ec2
    - spot-fleet
    - cloudops
    - deploy
    - compute
    - provisioning
    - allocation-strategy
    - capacity-rebalance
    - launch-template
    - spot-instances
  dependencies:
    - aws-orchestrator
  keywords:
    - create spot fleet
    - ec2 spot fleet request
    - spot allocation strategy
    - capacity rebalance spot
    - spot placement score
    - priceCapacityOptimized
    - lowestPrice spot
    - capacityOptimized spot
    - diversified spot fleet
    - maintain spot fleet
  when_to_use: >-
    Invoke when the user wants to create an EC2 Spot Fleet request
    (maintain or one-time request), select an allocation strategy
    (lowestPrice, capacityOptimized, diversified,
    priceCapacityOptimized), configure instance pool
    diversification, enable capacity rebalance and replacement,
    use Spot placement score for capacity awareness, or integrate
    Spot Fleets with capacity reservations. Do NOT invoke for
    single Spot Instance requests (use RunInstances with
    InstanceMarketOptions), for On-Demand Capacity Reservations
    standalone (use capacity-reservation operators), for EC2
    Auto Scaling Groups with mixed instances (use
    autoscaling-policy-deployer), or for auditing existing Spot
    Fleet configurations (use autoscaling-group-auditor).
---

# EC2 Spot Fleet Deployer

An AWS CloudOps agent skill that provisions EC2 Spot Fleets with
correct defaults. The skill walks the operator through fleet type
selection, launch template configuration, allocation strategy
choice, instance pool diversification, target capacity, replacement
strategies, capacity rebalance, and Spot placement score. It
captures capacity and cost decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Spot Fleet, EC2 Spot Fleet request, spot allocation
strategy, capacity rebalance spot, Spot placement score,
priceCapacityOptimized, lowestPrice spot, capacityOptimized spot,
diversified Spot Fleet, maintain Spot Fleet, Spot instance pool,
target capacity, Spot Fleet launch template.

## STRICT output contract

When this skill is invoked with a Spot-Fleet-provisioning request
(fleet type, allocation strategy, instance types, target capacity,
or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `SPOT_FLEET:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Fleet type (maintain vs request) | Fleet lifecycle decision |
| Step 2 — Launch template configuration | AMI, instance type, network |
| Step 3 — Allocation strategy | Cost vs capacity trade-off |
| Step 4 — Instance pools and diversification | Interruption resilience |
| Step 5 — Target capacity (units vs vCPUs) | Sizing |
| Step 6 — Replacement strategies | Interruption handling |
| Step 7 — Capacity rebalance | Proactive rebalancing |
| Step 8 — Spot placement score | Capacity-aware launch |
| Step 9 — Capacity reservations integration | Guaranteed capacity |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/allocation-strategies.md | Strategy deep dive |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

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

## Configuration dependency graph (novel heuristic)

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

## Expert heuristic: allocation strategy selection

The allocation strategy determines how the Spot Fleet selects which
Spot Instance pools to draw from. A baseline model lists the four
options without explaining when each fails; this heuristic provides
a decision framework.

```text
Workload profile → allocation strategy

Stateless, fault-tolerant, cost-optimized
  → priceCapacityOptimized (RECOMMENDED DEFAULT)
    Balances price with capacity availability. AWS's recommended
    default since Nov 2022. Avoids concentrating the fleet in a
    single cheap pool that gets reclaimed all at once.

Stateless, MUST be cheapest, can tolerate interruptions
  → lowestPrice
    Picks the lowest-priced pool per AZ. No diversification. High
    risk of simultaneous fleet-wide interruption. Only use with
    many instance types (10+) across all AZs.

Stateless, capacity availability > price sensitivity
  → capacityOptimized
    Picks pools with the most available capacity, reducing
    interruption risk. Good for long-running workloads where
    interruption cost > Spot savings.

Stateful or requires specific instance families
  → diversified
    Distributes across all pools equally. Lowest interruption risk
    but no cost optimization.
```

**Key implication:** `lowestPrice` was the pre-2022 default and is
rarely the best choice. `priceCapacityOptimized` avoids the trap of
concentrating the fleet in a single cheap pool. `capacityOptimized`
suits workloads where interruption cost is high (batch jobs, CI/CD,
ML training). `diversified` is the fallback for maximum spread.

## Expert heuristic: capacity rebalance and replacement

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with EC2 Spot Fleet access | Cannot provision without it | `aws sts get-caller-identity` |
| Region selected | Instance types and AZ availability vary by region | `aws configure get region` |
| IAM service role for Spot Fleet | Spot Fleet needs `AWSServiceRoleForEC2SpotFleet` to launch instances | `aws iam get-role --role-name AWSServiceRoleForEC2SpotFleet` |
| Launch template exists (or create one) | Fleet needs a standardized instance configuration | `aws ec2 describe-launch-templates` |
| AMI valid in the region | AMIs are region-scoped; cross-region AMI IDs are invalid | `aws ec2 describe-images --image-ids <ami-id>` |
| Instance types available in the region | Not all instance types are available in all regions/AZs | `aws ec2 describe-instance-types --instance-types <type>` |
| At least 2-3 instance types specified | Single-type fleets have no diversification fallback | List in the Overrides |
| At least 2 AZs specified | Single-AZ fleets lose all capacity on AZ failure | List AZs in Overrides |
| Target capacity identified | Determines fleet size; `maintain` fleets auto-adjust | Positive integer |
| Spot placement score (optional) | Pre-check capacity availability before creating fleet | `aws ec2 get-spot-placement-scores` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Fleet type (maintain vs request)

The first decision is whether the fleet should continuously maintain
its target capacity or fill it once and stop.

**Decision tree:**
```text
Does the workload need continuous capacity (long-running, stateless)?
├── YES → Fleet type: maintain
│         AWS continuously monitors and replaces interrupted instances.
│         Target capacity can be modified (scale up/down).
│         Capacity rebalance can be enabled.
│         Use for: web servers, batch processing, CI/CD workers
└── NO  → Is this a one-time burst (job queue, HPC, data processing)?
    ├── YES → Fleet type: request
    │         Fleet fills once and stops. No replacement.
    │         Target capacity CANNOT be modified after creation.
    │         Capacity rebalance is silently ignored.
    │         Use for: one-time HPC jobs, data migration, burst compute
    └── NO  → Fleet type: maintain (the safe default)
```

**Feature comparison:**

| Feature | maintain | request |
|---|---|---|
| Replacement on interruption | Yes (automatic) | No |
| Target capacity modification | Yes (live) | No (immutable) |
| Capacity rebalance | Supported | Not supported (ignored) |
| Excess capacity termination | Configurable | N/A |
| Expiry | Until cancelled | Fills once, then done |
| Best for | Long-running workloads | One-time burst jobs |

**Common mistake:** using `request` for a web tier and expecting
AWS to replace interrupted instances. It will not — the fleet fills
once and stops. Use `maintain`.

## Step 2 — Launch template configuration

A launch template defines the instance configuration: AMI, instance
type, key pair, security groups, IAM instance profile, user data,
and storage. The Spot Fleet references the launch template and
overrides instance type and AZ via the Overrides array.

**Create a launch template:**
```bash
aws ec2 create-launch-template \
  --launch-template-name spot-fleet-web-server \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m5.large",
    "KeyName": "my-key-pair",
    "SecurityGroupIds": ["sg-0abc123"],
    "IamInstanceProfile": { "Arn": "arn:aws:iam::123456789012:instance-profile/spot-fleet-role" },
    "UserData": "'$(base64 user-data.sh)'",
    "BlockDeviceMappings": [{
      "DeviceName": "/dev/xvda",
      "Ebs": { "VolumeSize": 30, "VolumeType": "gp3", "DeleteOnTermination": true }
    }],
    "TagSpecifications": [{
      "ResourceType": "instance",
      "Tags": [
        { "Key": "Name", "Value": "spot-fleet-web" },
        { "Key": "Environment", "Value": "production" }
      ]
    }]
  }'
```

**Key rules:**
- The instance type in the launch template is the DEFAULT; the
  Spot Fleet Overrides override it per pool.
- The AMI must be valid in the fleet's region.
- EBS volumes should be `DeleteOnTermination: true` for Spot
  (otherwise orphaned volumes accumulate cost).
- Tag the instances at launch (launch-template tags are more
  reliable than Spot Fleet-level tags).

## Step 3 — Allocation strategy

See the "Expert heuristic: allocation strategy selection" section
above for the decision framework. Summary:

| Strategy | Picks pools based on | Diversification | Interruption risk | Cost |
|---|---|---|---|---|
| `priceCapacityOptimized` | Price + capacity availability (RECOMMENDED) | Implicit (multi-pool) | Low-Medium | Low |
| `capacityOptimized` | Capacity availability (max free capacity) | Implicit (multi-pool) | Lowest | Medium |
| `lowestPrice` | Lowest price per AZ | None (concentrates) | Highest | Lowest |
| `diversized` | Even spread across all pools | Explicit (equal) | Low | Medium |

**Setting the allocation strategy:**
```json
{
  "AllocationStrategy": "priceCapacityOptimized",
  "TargetCapacitySpecification": {
    "TotalTargetCapacity": 10,
    "DefaultTargetCapacityType": "spot"
  }
}
```

**Common mistake:** using `lowestPrice` with a single instance type.
The fleet concentrates in one pool and is interrupted all at once.
Always use `priceCapacityOptimized` or `capacityOptimized` unless you
have a specific cost-optimization requirement with many (10+) instance
types.

## Step 4 — Instance pools and diversification

Instance pools are unique combinations of instance type + AZ. The
Spot Fleet draws from these pools based on the allocation strategy.
More pools = better diversification = lower interruption risk.

**Overrides specify the pools (9 pools = 3 types x 3 AZs):**
```json
"LaunchTemplateConfigs": [{
  "LaunchTemplateSpecification": { "LaunchTemplateId": "lt-0abc123", "Version": "1" },
  "Overrides": [
    { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1a" },
    { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1b" },
    { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1c" },
    { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1a" },
    { "InstanceType": "c5.large",  "AvailabilityZone": "us-east-1b" },
    { "InstanceType": "c5.large",  "AvailabilityZone": "us-east-1c" }
  ]
}]
```

**Diversification best practices:**
- Specify at least 2-3 instance types (e.g., m5, m5a, c5).
- Specify at least 3 AZs (all AZs in the region).
- This gives 9+ pools, dramatically reducing interruption risk.
- Use instance type families with similar vCPU/memory ratios so
  your workload scales predictably.
- Consider using `InstanceRequirements` (attribute-based) instead of
  specific types for flexible selection.

**Attribute-based instance selection (InstanceRequirements):**
```json
"Overrides": [
  {
    "InstanceRequirements": {
      "VCpuCount": { "Min": 2, "Max": 4 },
      "MemoryMiB": { "Min": 8192 },
      "AcceleratorCount": { "Max": 0 },
      "BurstablePerformance": "excluded"
    },
    "AvailabilityZone": "us-east-1a"
  }
]
```

This lets AWS pick any instance type matching the requirements,
maximizing pool count.

## Step 5 — Target capacity (units vs vCPUs vs instances)

Target capacity can be measured in three ways:

| Unit type | How it works | When to use |
|---|---|---|
| `units` | Weighted: each override has a `WeightedCapacity` value | Mixed-size fleets (some instances count as 2 units, others as 1) |
| `vcpu` | Each instance counts as its vCPU count | vCPU-based capacity planning |
| `instances` (default) | Each instance counts as 1 | Simple equal-weight fleets |

```json
"TargetCapacitySpecification": {
  "TotalTargetCapacity": 20,
  "DefaultTargetCapacityType": "spot",
  "TargetCapacityUnitType": "vcpu"
}
```

**Common mistake:** using `instances` with mixed instance types
where some are 2x the size of others. The fleet thinks it needs 20
instances, but if it picks large instances, you have way more
capacity than intended. Use `vcpu` or `units` for mixed fleets.

## Step 6 — Replacement strategies (InstanceInterruptionBehavior)

When a Spot Instance is interrupted, the fleet's behavior depends
on `InstanceInterruptionBehavior`:

| Behavior | What happens to the interrupted instance | When to use |
|---|---|---|
| `terminate` (default) | Instance is terminated (EBS volumes deleted if DeleteOnTermination) | Stateless workloads |
| `stop` | Instance is stopped (can be restarted later) | Stateful workloads that can resume |
| `hibernate` | Instance is hibernated (RAM saved to disk) | Long-running jobs with checkpointing |

```json
{
  "InstanceInterruptionBehavior": "terminate",
  "SpotMaintenanceStrategies": {
    "CapacityRebalance": {
      "ReplacementStrategy": "launch"
    }
  }
}
```

**Key rule:** `InstanceInterruptionBehavior` is set at the Spot
Fleet request level and applies to ALL instances in the fleet. It
cannot be overridden per-instance after launch.

## Step 7 — Capacity rebalance

See the "Expert heuristic: capacity rebalance and replacement"
section above for the full lifecycle. Summary configuration:

```json
"SpotMaintenanceStrategies": {
  "CapacityRebalance": {
    "ReplacementStrategy": "launch"
  }
}
```

**Replacement strategies:**
- `launch` (default): Fleet launches a new replacement instance
  BEFORE terminating the old one. This is the recommended strategy.
- `terminate`: Fleet terminates the old instance immediately and
  then launches a replacement. Higher risk of capacity gap.

**Requirements:**
- Fleet type MUST be `maintain`.
- Fleet MUST have `InstanceInterruptionBehavior` set to `terminate`
  or `stop`.
- The replacement instance is launched from the same launch
  template + overrides.

**Common mistake:** enabling capacity rebalance on a `request` fleet.
It is silently ignored. Only `maintain` fleets support rebalancing.

## Step 8 — Spot placement score

Spot placement score is a pre-flight capacity check. Before creating
a fleet, query the score to see which instance type + AZ
combinations have the best capacity availability.

**Query Spot placement scores:**
```bash
aws ec2 get-spot-placement-scores \
  --instance-types m5.large m5a.large c5.large \
  --target-capacity 10 \
  --target-capacity-type vcpu \
  --region us-east-1 \
  --single-availability-zone true
```

**Output:**
```json
{
  "SpotPlacementScores": [
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az1", "Score": 10 },
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az2", "Score": 7 },
    { "Region": "us-east-1", "AvailabilityZoneId": "use1-az3", "Score": 3 }
  ]
}
```

**Score interpretation:**
- Score 1-3: Low availability. High interruption risk. Avoid.
- Score 4-7: Medium availability. Acceptable for fault-tolerant.
- Score 8-10: High availability. Low interruption risk. Prefer.

**Key implication:** Spot placement score is ADVISORY ONLY. It does
not reserve capacity. The fleet may still be interrupted in a
high-scoring pool if overall Spot demand spikes.

**When to use:** Before creating large fleets (>100 instances),
when choosing between instance types, or before scaling up.

## Step 9 — Capacity reservations integration

On-Demand Capacity Reservations (ODCR) can be used alongside Spot
Fleets. When the fleet launches in an AZ+instance-type combination
that has an open ODCR, the ODCR is consumed first (guaranteed
capacity, On-Demand billing), then Spot fills the rest.

**Configuration for ODCR preference:**
```json
{
  "LaunchTemplateConfigs": [{
    "LaunchTemplateSpecification": { "LaunchTemplateId": "lt-0abc123", "Version": "1" },
    "Overrides": [{
      "InstanceType": "m5.large",
      "AvailabilityZone": "us-east-1a"
    }]
  }],
  "TargetCapacitySpecification": {
    "TotalTargetCapacity": 10,
    "OnDemandTargetCapacity": 3,
    "DefaultTargetCapacityType": "spot"
  },
  "OnDemandOptions": {
    "CapacityReservationOptions": {
      "UsageStrategy": "use-capacity-reservations-first"
    }
  }
}
```

**Key rules:**
- ODCR must match instance type + AZ + platform exactly.
- `OnDemandTargetCapacity` specifies how many units to run as
  On-Demand (consumed from ODCR if available).
- The rest of the fleet runs as Spot.
- This gives a hybrid: guaranteed capacity for critical instances +
  cost savings for the rest.

## Step 10 — Recent features

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

## NEVER do these things

1. **NEVER use `lowestPrice` with a single instance type.** The
   fleet concentrates in one pool. When that pool is reclaimed, the
   entire fleet is interrupted simultaneously with no fallback. Use
   `priceCapacityOptimized` with at least 3 instance types.

2. **NEVER use `request` fleet type for long-running workloads.**
   A `request` fleet fills once and stops. It does NOT replace
   interrupted instances. Use `maintain` for any workload that
   needs continuous capacity.

3. **NEVER specify only one instance type or one AZ.** Single-type
   or single-AZ fleets have no diversification. Always specify 2-3+
   instance types across 3+ AZs for interruption resilience.

4. **NEVER enable capacity rebalance on a `request` fleet.** It is
   silently ignored. Capacity rebalance only works with `maintain`
   fleet type. Verify fleet type before configuring rebalance.

5. **NEVER treat Spot placement score as a capacity guarantee.** It
   is advisory only. A score of 10 does not reserve capacity. Use
   it to avoid low-scoring pools, not as a reservation.

## Output format

```text
SPOT_FLEET: <fleet-id> (allocation strategy: <strategy>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Fleet type: maintain | request
  [✓|✗] Allocation strategy: priceCapacityOptimized | capacityOptimized | lowestPrice | diversified
  [✓|✗] Launch template: <lt-id> (version <n>)
  [✓|✗] Instance types: <type-1>, <type-2>, <type-3> (in <n> AZs = <pool-count> pools)
  [✓|✗] Target capacity: <n> <unit-type> (spot: <n>, on-demand: <n>)
  [✓|✗] InstanceInterruptionBehavior: terminate | stop | hibernate
  [✓|✗] Capacity rebalance: enabled (launch strategy) | disabled
  [✓|✗] Spot placement score: checked (top pool score: <score>) | not checked
  [✓|✗] Capacity reservations (ODCR): used-first (<n> On-Demand units) | not used
  [✓|✗] IAM service role: AWSServiceRoleForEC2SpotFleet
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ec2 describe-spot-fleet-requests --spot-fleet-request-ids <fleet-id>
  aws ec2 describe-spot-fleet-instances --spot-fleet-request-id <fleet-id>
  aws ec2 describe-spot-fleet-request-history --spot-fleet-request-id <fleet-id>
```

### Worked example — maintain fleet with priceCapacityOptimized and rebalance

```text
SPOT_FLEET: sfr-1234567890abcdef0 (allocation strategy: priceCapacityOptimized)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Fleet type: maintain
  [✓] Allocation strategy: priceCapacityOptimized
  [✓] Launch template: lt-0abc123def456 (version 1)
  [✓] Instance types: m5.large, m5a.large, c5.large (in 3 AZs = 9 pools)
  [✓] Target capacity: 20 vcpu (spot: 20, on-demand: 0)
  [✓] InstanceInterruptionBehavior: terminate
  [✓] Capacity rebalance: enabled (launch strategy)
  [✓] Spot placement score: checked (top pool score: 10)
  [✓] Capacity reservations (ODCR): not used
  [✓] IAM service role: AWSServiceRoleForEC2SpotFleet
  [✓] Tags: Environment=production, Service=batch-processing
VERIFICATION_COMMANDS:
  aws ec2 describe-spot-fleet-requests --spot-fleet-request-ids sfr-1234567890abcdef0
  aws ec2 describe-spot-fleet-instances --spot-fleet-request-id sfr-1234567890abcdef0
  aws ec2 describe-spot-fleet-request-history --spot-fleet-request-id sfr-1234567890abcdef0
```

## Error handling

### Fleet stuck in `submitted`/`active` with 0 instances
- No capacity in the specified pools. Check Spot placement score;
  diversify by adding instance types/AZs. Switch to
  `capacityOptimized` if using `lowestPrice`. Verify the IAM service
  role (`AWSServiceRoleForEC2SpotFleet`) exists.

### Fleet partially filled (e.g., 10 of 20 target)
- Add more instance types (m5a, c5, r5 families) and AZs. Consider
  switching to `priceCapacityOptimized` if using `lowestPrice`.

### Capacity rebalance not working
- Verify fleet type is `maintain` (not `request`). Verify
  `ReplacementStrategy` is `launch`. Check EventBridge for rebalance
  recommendation events.

### `MaxSpotInstanceCountExceeded`
- Account hit the Spot vCPU limit. Request a quota increase via
  Service Quotas. Use vCPU-based quotas (now default).

### Allocation strategy cannot be changed
- Immutable after creation. Cancel the fleet
  (`cancel-spot-fleet-requests`) and create a new one.

## Domain

AWS CloudOps / EC2 Spot Fleet Provisioning & Cost-Optimized Compute
Capacity Management.

## AWS documentation

- **Spot Fleet User Guide** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-fleet.html
- **Allocation strategies** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-fleet-allocation-strategy.html
- **Capacity rebalance** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-rebalance.html
- **Spot placement score** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-placement-score.html
- **Spot Fleet request options** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-request-options.html
- **Instance interruption behavior** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-interruptions.html
- **On-Demand Capacity Reservations** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-reservations.html
- **Attribute-based instance selection** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-instance-request-types.html#attribute-based-instance-type-selection
