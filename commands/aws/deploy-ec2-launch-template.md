---
description: Provision an EC2 Launch Template with production-grade defaults (IMDSv2 required, gp3 block devices, Graviton architecture validation, tag specifications, capacity reservation targeting, network interfaces). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create launch template"
  - "deploy launch template"
  - "ec2 launch template"
  - "launch template version"
  - "imdsv2 required"
  - "imdsv2 launch template"
  - "graviton launch template"
  - "arm64 launch template"
  - "block device mapping"
  - "ebs gp3 launch template"
  - "instance store launch template"
  - "network interface launch template"
  - "capacity reservation targeting"
  - "tag specifications launch template"
  - "iam instance profile launch template"
  - "user data launch template"
routes_to: ec2-launch-template-deployer
---

# /aws:deploy-ec2-launch-template

Activate the `ec2-launch-template-deployer` skill and provision an
EC2 Launch Template with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. AMI and architecture validation (x86_64 / arm64 Graviton)
2. Instance type selection
3. Key pair, security groups, IAM instance profile
4. User data (base64-encoded bootstrap)
5. Block device mapping (EBS gp3, instance store)
6. Network interfaces (subnet, public IP, IPv6, SG)
7. IMDSv2 enforcement (HttpTokens=required)
8. Tag specifications (instance, volume, network-interface)
9. Capacity reservation targeting (open / targeted / none)
10. CPU options and license specifications
11. Recent features

## When to use

- You need to create a new launch template.
- You want to enforce IMDSv2 (HttpTokens=required).
- You are targeting Graviton (arm64) instance types.
- You need block device mapping with gp3 volumes.
- You want to target a capacity reservation.
- You are configuring network interfaces with public IP / IPv6.
- You want tag specifications on instance + volume + ENI.

## When NOT to use

- **EC2 Instance Connect Endpoint** — use `vpc-network-deployer`.
- **Spot Fleet requests** — use `ec2-spot-fleet-deployer`.
- **Auto Scaling Group configuration** — use
  `autoscaling-policy-deployer`.
- **Auditing existing launch templates** — use
  `ec2-security-group-auditor` / `compute-optimizer-findings-auditor`.

## How to invoke

### Slash command

```
/aws:deploy-ec2-launch-template
```

Then provide: AMI ID, instance type, key pair, security groups, IAM
instance profile, subnet, block devices, IMDSv2 setting, tags.

### Natural language

Any of these routes to the same skill:

- "create a launch template with imdsv2 required"
- "deploy a graviton launch template"
- "create a launch template targeting a capacity reservation"
- "configure gp3 block devices in my launch template"
- "add tag specifications to my launch template"

### CLI routing

```bash
node cli/bin/cli.js route "create launch template"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create or version a launch template. The output checklist feeds into
verification pipelines and downstream skills (EC2 launch, ASG,
Spot Fleet all consume launch templates).

## Example

```
You: /aws:deploy-ec2-launch-template

     Create a Graviton launch template in us-east-1 with
     IMDSv2 required, gp3 volumes, tag specs on instance +
     volume + ENI. AMI ami-0abcdef1234567890 (arm64). Instance
     type m7g.large. Account 123456789012.

Skill:
  LAUNCH_TEMPLATE: lt-0abc123def456 (version 1)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] AMI: ami-0abcdef1234567890 (architecture: arm64)
    [✓] Instance type: m7g.large (architecture: arm64)
    [✓] Architecture match: arm64 == arm64
    [✓] IMDSv2: HttpTokens=required, hop limit 2
    [✓] Block devices: root 30 gp3, secondary 100 gp3
    [✓] Tag specifications: instance, volume, network-interface
  VERIFICATION_COMMANDS:
    aws ec2 describe-launch-template-versions --launch-template-id lt-0abc123def456
    aws ec2 describe-launch-templates --launch-template-ids lt-0abc123def456
```

## References

- Skill definition: `skills/ec2-launch-template-deployer/SKILL.md`
- Block device / network deep dive: `skills/ec2-launch-template-deployer/references/block-device-and-network.md`
- Provisioning CLI commands: `skills/ec2-launch-template-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/ec2-launch-template-deployer/evals/evals.json`
