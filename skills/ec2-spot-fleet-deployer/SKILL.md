---
name: ec2-spot-fleet-deployer
description: 'Provisions EC2 Spot Fleets with production defaults: launch template configuration, Spot Fleet request (target capacity, allocation strategy: lowestPrice/capacityOptimized/diversified/ priceCapacityOptimized), instance pools, fleet type (request/maintain), replacement strategies, capacity rebalance, Spot placement score, capacity reservations. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Spot Fleet request, choosing an allocation strategy, configuring instance diversification, enabling capacity rebalance, or integrating Spot Fleets with capacity reservations. Triggers: create spot fleet, EC2 Spot Fleet request, spot instance pool, allocation strategy, capacity rebalance, spot placement score, priceCapacityOptimized, lowestPrice spot, capacityOptimized spot, diversified spot fleet, maintain spot fleet.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ec2, iam, and service-roles access. Works with Terraform aws_spot_fleet_request resources and CloudFormation AWS::EC2::SpotFleet templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ec2, spot-fleet, cloudops, deploy, compute, provisioning, allocation-strategy, capacity-rebalance, launch-template, spot-instances
  dependencies: aws-orchestrator
  keywords: aws, ec2, spot fleet, spot instances, cloudops, deploy, provisioning, allocation strategy, lowestPrice, capacityOptimized, diversified, priceCapacityOptimized, instance pools, target capacity, capacity rebalance, spot placement score, capacity reservations, launch template, fleet type, maintain
  when_to_use: Invoke when the user wants to create an EC2 Spot Fleet request (maintain or one-time request), select an allocation strategy (lowestPrice, capacityOptimized, diversified, priceCapacityOptimized), configure instance pool diversification, enable capacity rebalance and replacement, use Spot placement score for capacity awareness, or integrate Spot Fleets with capacity reservations. Do NOT invoke for single Spot Instance requests (use RunInstances with InstanceMarketOptions), for On-Demand Capacity Reservations standalone (use capacity-reservation operators), for EC2 Auto Scaling Groups with mixed instances (use autoscaling-policy-deployer), or for auditing existing Spot Fleet configurations (use autoscaling-group-auditor).
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
Full mindset and the three provisioning misconceptions moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)
Full dependency table and cross-dependency gotchas moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: allocation strategy selection
Workload-profile decision framework and key implications moved to
[references/allocation-strategies.md](references/allocation-strategies.md).

## Expert heuristic: capacity rebalance and replacement
Rebalance-vs-default-replacement comparison, lifecycle, and enabling JSON moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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

Query command and sample output moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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
Recent AWS feature notes (2023-2026) moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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
Fleet failure modes and their fixes moved to
[references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset misconceptions, configuration dependency graph, capacity rebalance deep dive, recent AWS features (moved from this file)
- [references/allocation-strategies.md](references/allocation-strategies.md) — allocation-strategy workload-profile heuristic (moved from this file) plus the strategy comparison matrix and decision framework
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — full copy-pasteable provisioning CLI sequence
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Spot placement score query and sample output (moved from this file)
- [references/error-handling.md](references/error-handling.md) — fleet stuck/partially filled, rebalance not working, MaxSpotInstanceCountExceeded, immutable allocation strategy (moved from this file)

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
