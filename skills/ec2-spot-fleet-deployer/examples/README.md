# End-to-End Example: EC2 Spot Fleet Deployment

A walkthrough showing how to use the `ec2-spot-fleet-deployer`
skill from invocation through verification. Mirrors the structured-
>eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a maintain Spot Fleet for batch processing.
The fleet needs:

- Fleet type: maintain (continuous capacity with replacement)
- Allocation strategy: priceCapacityOptimized (recommended)
- Instance types: m5.large, m5a.large, c5.large (3 types)
- AZs: us-east-1a, us-east-1b, us-east-1c (3 AZs = 9 pools)
- Target capacity: 20 vcpu
- Capacity rebalance: enabled (launch replacement strategy)
- InstanceInterruptionBehavior: terminate
- Launch template: lt-0abc123 (version 1)

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ec2-spot-fleet
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a maintain Spot Fleet in us-east-1 with
      priceCapacityOptimized. Target capacity 20 vcpu.
      Instance types: m5.large, m5a.large, c5.large across
      us-east-1a, us-east-1b, us-east-1c. Enable capacity
      rebalance. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a spot fleet"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SPOT_FLEET: sfr-1234567890abcdef0 (allocation strategy: priceCapacityOptimized)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Fleet type: maintain
  [✓] Allocation strategy: priceCapacityOptimized
  [✓] Launch template: lt-0abc123 (version 1)
  [✓] Instance types: m5.large, m5a.large, c5.large (in 3 AZs = 9 pools)
  [✓] Target capacity: 20 vcpu (spot: 20, on-demand: 0)
  [✓] InstanceInterruptionBehavior: terminate
  [✓] Capacity rebalance: enabled (launch strategy)
  [✓] Spot placement score: not checked
  [✓] Capacity reservations (ODCR): not used
  [✓] IAM service role: AWSServiceRoleForEC2SpotFleet
  [✓] Tags: Environment=production, Service=batch-processing
VERIFICATION_COMMANDS:
  aws ec2 describe-spot-fleet-requests --spot-fleet-request-ids sfr-1234567890abcdef0
  aws ec2 describe-spot-fleet-instances --spot-fleet-request-id sfr-1234567890abcdef0
  aws ec2 describe-spot-fleet-request-history --spot-fleet-request-id sfr-1234567890abcdef0
```

---

## Step 3 — Provisioning commands

```bash
# Step 0: Verify IAM service role
aws iam get-role --role-name AWSServiceRoleForEC2SpotFleet

# Step 1: Create the Spot Fleet request
FLEET_ID=$(aws ec2 request-spot-fleet \
  --spot-fleet-request-config '{
    "Type": "maintain",
    "AllocationStrategy": "priceCapacityOptimized",
    "IamFleetRole": "arn:aws:iam::123456789012:role/aws-service-role/spotfleet.amazonaws.com/AWSServiceRoleForEC2SpotFleet",
    "TargetCapacitySpecification": {
      "TotalTargetCapacity": 20,
      "DefaultTargetCapacityType": "spot",
      "TargetCapacityUnitType": "vcpu"
    },
    "LaunchTemplateConfigs": [{
      "LaunchTemplateSpecification": { "LaunchTemplateId": "lt-0abc123", "Version": "1" },
      "Overrides": [
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1a" },
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1b" },
        { "InstanceType": "m5.large",  "AvailabilityZone": "us-east-1c" },
        { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1a" },
        { "InstanceType": "m5a.large", "AvailabilityZone": "us-east-1b" },
        { "InstanceType": "c5.large",  "AvailabilityZone": "us-east-1c" }
      ]
    }],
    "InstanceInterruptionBehavior": "terminate",
    "SpotMaintenanceStrategies": {
      "CapacityRebalance": { "ReplacementStrategy": "launch" }
    }
  }' \
  --query 'SpotFleetRequestId' --output text)

echo "Fleet ID: $FLEET_ID"

# Step 2: Monitor fleet status
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID"

# Step 3: List running instances
aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id "$FLEET_ID"
```

---

## Step 4 — Post-deployment verification

```bash
# Fleet state (should be active)
aws ec2 describe-spot-fleet-requests \
  --spot-fleet-request-ids "$FLEET_ID" \
  --query 'SpotFleetRequestConfigs[0].SpotFleetRequestState'

# Fulfilled capacity
aws ec2 describe-spot-fleet-instances \
  --spot-fleet-request-id "$FLEET_ID" \
  --output table

# Check for errors
aws ec2 describe-spot-fleet-request-history \
  --spot-fleet-request-id "$FLEET_ID" \
  --query 'HistoryRecords[?EventType==`error`]'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Allocation strategy | `lowestPrice` (default) | `priceCapacityOptimized` | lowestPrice concentrates in one pool; priceCapacityOptimized balances price + capacity |
| Instance diversification | 1 type, 1 AZ | 3 types, 3 AZs (9 pools) | Single-type/single-AZ fleets collapse on interruption |
| Capacity rebalance | Not configured | Enabled with launch | Proactive rebalancing gives more migration lead time |
| Fleet type | Unspecified | `maintain` (explicit) | `request` fills once and stops — no replacement |
| IAM role check | Skipped | Verified before request | Missing role causes silent permission failure |
| Capacity unit | `instances` (default) | `vcpu` (for mixed types) | Mixed types with `instances` gives inconsistent capacity |
| Spot placement score | Skipped | Checked for large fleets | Pre-validate capacity availability before launching |

---

## Related artifacts

- **Skill definition:** `skills/ec2-spot-fleet-deployer/SKILL.md`
- **Allocation strategies guide:** `skills/ec2-spot-fleet-deployer/references/allocation-strategies.md`
- **Provisioning CLI commands:** `skills/ec2-spot-fleet-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-ec2-spot-fleet.md`
- **Eval suite:** `skills/ec2-spot-fleet-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ec2-spot-fleet-deployer/eval/test-cases.yaml`
