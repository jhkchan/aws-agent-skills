---
description: Provision an EC2 Spot Fleet with production-grade defaults (allocation strategy, fleet type, instance diversification, capacity rebalance, Spot placement score, capacity reservations). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create spot fleet"
  - "deploy spot fleet"
  - "ec2 spot fleet"
  - "spot fleet request"
  - "spot allocation strategy"
  - "capacity rebalance spot"
  - "spot placement score"
  - "priceCapacityOptimized"
  - "lowestPrice spot"
  - "capacityOptimized spot"
  - "diversified spot fleet"
  - "maintain spot fleet"
  - "spot instance pool"
  - "target capacity spot"
  - "spot fleet launch template"
routes_to: ec2-spot-fleet-deployer
---

# /aws:deploy-ec2-spot-fleet

Activate the `ec2-spot-fleet-deployer` skill and provision an EC2
Spot Fleet with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Fleet type (maintain vs request)
2. Launch template configuration
3. Allocation strategy (priceCapacityOptimized, capacityOptimized, lowestPrice, diversified)
4. Instance pools and diversification
5. Target capacity (units vs vCPUs vs instances)
6. Replacement strategies (InstanceInterruptionBehavior)
7. Capacity rebalance
8. Spot placement score
9. Capacity reservations integration
10. Recent features

## When to use

- You need to create a Spot Fleet request (maintain or one-time).
- You are selecting an allocation strategy.
- You need instance diversification across types and AZs.
- You want to enable capacity rebalance.
- You need Spot placement score pre-checks.
- You want to integrate On-Demand Capacity Reservations.

## When NOT to use

- **Single Spot Instance requests** — use RunInstances with
  InstanceMarketOptions.
- **EC2 Auto Scaling Groups with mixed instances** — use
  `autoscaling-policy-deployer`.
- **On-Demand Capacity Reservations standalone** — use capacity-
  reservation operators.
- **Auditing existing Spot Fleets** — use `autoscaling-group-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-ec2-spot-fleet
```

Then provide: fleet type, allocation strategy, instance types,
AZs, target capacity, launch template ID, capacity rebalance
(yes/no), IAM role status, tags.

### Natural language

Any of these routes to the same skill:

- "create a maintain spot fleet with priceCapacityOptimized"
- "request a one-time spot fleet for HPC burst"
- "enable capacity rebalance on my spot fleet"
- "check spot placement score before creating fleet"
- "integrate capacity reservations with my spot fleet"

### CLI routing

```bash
node cli/bin/cli.js route "create a spot fleet"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create Spot Fleet requests. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-ec2-spot-fleet

     Create a maintain Spot Fleet in us-east-1 with
     priceCapacityOptimized. Target capacity 20 vcpu.
     Instance types: m5.large, m5a.large, c5.large across
     us-east-1a, us-east-1b, us-east-1c. Enable capacity
     rebalance. Launch template lt-0abc123. Account: 123456789012.

Skill:
  SPOT_FLEET: sfr-1234567890abcdef0
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Fleet type: maintain
    [✓] Allocation strategy: priceCapacityOptimized
    [✓] Instance types: m5.large, m5a.large, c5.large (9 pools)
    [✓] Target capacity: 20 vcpu
    [✓] Capacity rebalance: enabled (launch strategy)
    [✓] IAM service role: AWSServiceRoleForEC2SpotFleet
  VERIFICATION_COMMANDS:
    aws ec2 describe-spot-fleet-requests --spot-fleet-request-ids <fleet-id>
    aws ec2 describe-spot-fleet-instances --spot-fleet-request-id <fleet-id>
```

## References

- Skill definition: `skills/ec2-spot-fleet-deployer/SKILL.md`
- Allocation strategies: `skills/ec2-spot-fleet-deployer/references/allocation-strategies.md`
- Provisioning CLI commands: `skills/ec2-spot-fleet-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/ec2-spot-fleet-deployer/evals/evals.json`
