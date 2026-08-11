# End-to-End Example: EC2 Launch Template Deployment

A walkthrough showing how to use the `ec2-launch-template-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Graviton-based web server launch template.
The template needs:

- AMI: ami-0abcdef1234567890 (arm64, AL2023)
- Instance type: m7g.large (Graviton)
- IMDSv2 required (HttpTokens=required), hop limit 2 (containers)
- Block devices: root 30 GB gp3, secondary 100 GB gp3 6000 IOPS
- Network: public IP, IPv6, security groups in VPC
- Tag specs: instance, volume, network-interface

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-ec2-launch-template
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Graviton launch template in us-east-1 with IMDSv2
      required, gp3 volumes, tag specs on instance + volume + ENI.
      AMI ami-0abcdef1234567890 (arm64). Instance type m7g.large.
      Account 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create launch template"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LAUNCH_TEMPLATE: lt-0abc123def456 (version 1, name: graviton-web-server)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] AMI: ami-0abcdef1234567890 (architecture: arm64)
  [✓] Instance type: m7g.large (architecture: arm64)
  [✓] Architecture match: arm64 == arm64
  [✓] Key pair: prod-graviton-key
  [✓] Security groups: sg-0abc123, sg-0def456 (VPC: vpc-0abc123def)
  [✓] IAM instance profile: web-server-role
  [✓] Block devices: root 30 gp3, secondary 100 gp3 6000 IOPS
  [✓] Network interface: subnet-0abc123def456, public IP true, IPv6 1
  [✓] IMDSv2: HttpTokens=required, hop limit 2
  [✓] Tag specifications: instance, volume, network-interface
  [✓] Capacity reservation: none
VERIFICATION_COMMANDS:
  aws ec2 describe-launch-template-versions --launch-template-id lt-0abc123def456 --versions 1
  aws ec2 describe-launch-templates --launch-template-ids lt-0abc123def456
```

---

## Step 3 — Provisioning commands

```bash
# Step 0: Verify AMI architecture
AMI_ARCH=$(aws ec2 describe-images --image-ids ami-0abcdef1234567890 \
  --query 'Images[0].Architecture' --output text)
echo "AMI Architecture: $AMI_ARCH"  # Must be arm64 for Graviton

# Step 1: Create the launch template
LT_ID=$(aws ec2 create-launch-template \
  --launch-template-name graviton-web-server \
  --launch-template-data '{
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "m7g.large",
    "KeyName": "prod-graviton-key",
    "IamInstanceProfile": { "Arn": "arn:aws:iam::123456789012:instance-profile/web-server-role" },
    "BlockDeviceMappings": [
      { "DeviceName": "/dev/xvda", "Ebs": { "VolumeSize": 30, "VolumeType": "gp3", "Iops": 3000, "DeleteOnTermination": true, "Encrypted": true } },
      { "DeviceName": "/dev/xvdb", "Ebs": { "VolumeSize": 100, "VolumeType": "gp3", "Iops": 6000, "DeleteOnTermination": true, "Encrypted": true } }
    ],
    "NetworkInterfaces": [{
      "DeviceIndex": 0,
      "SubnetId": "subnet-0abc123def456",
      "Groups": ["sg-0abc123", "sg-0def456"],
      "AssociatePublicIpAddress": true,
      "Ipv6AddressCount": 1
    }],
    "MetadataOptions": {
      "HttpEndpoint": "enabled",
      "HttpTokens": "required",
      "HttpPutResponseHopLimit": 2,
      "InstanceMetadataTags": "enabled"
    },
    "TagSpecifications": [
      { "ResourceType": "instance", "Tags": [
        { "Key": "Name", "Value": "graviton-web-server" },
        { "Key": "Environment", "Value": "production" }
      ]},
      { "ResourceType": "volume", "Tags": [
        { "Key": "Name", "Value": "graviton-web-root" }
      ]}
    ]
  }' \
  --query 'LaunchTemplate.LaunchTemplateId' --output text)

echo "Launch Template ID: $LT_ID"

# Step 2: Launch an instance from the template
INSTANCE_ID=$(aws ec2 run-instances \
  --launch-template "LaunchTemplateId=$LT_ID,Version=1" \
  --count 1 \
  --query 'Instances[0].InstanceId' --output text)
```

---

## Step 4 — Post-deployment verification

```bash
# Verify template version data (IMDSv2, block devices, tags)
aws ec2 describe-launch-template-versions \
  --launch-template-id "$LT_ID" --versions 1 \
  --query 'LaunchTemplateVersions[0].LaunchTemplateData.MetadataOptions'

# Verify the launched instance has IMDSv2 enforced
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].MetadataOptions' --output table

# Verify block devices on the instance
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings' --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| IMDSv2 | Not set (HttpTokens=optional default) | HttpTokens=required | Without this, IMDSv1 is available and vulnerable to SSRF |
| Architecture validation | Not checked | arm64 AMI verified against m7g.large | x86_64 AMI on Graviton fails at boot with no console clue |
| Volume type | gp2 (AMI default) | gp3 (20% cheaper, tunable IOPS) | gp2 is legacy; gp3 is the production default since 2020 |
| DeleteOnTermination | false on non-root (default) | true on all volumes | Orphaned volumes accumulate cost silently |
| Network interface | SecurityGroupIds at top-level | Groups inside NetworkInterfaces | Top-level silently overridden when NetworkInterfaces present |
| Tag specs | instance only | instance + volume + network-interface | Volume and ENI tags needed for cost allocation |
| Hop limit | 1 (default) | 2 (for containers) | Containerized workloads need higher hop limit for IMDSv2 |

---

## Related artifacts

- **Skill definition:** `skills/ec2-launch-template-deployer/SKILL.md`
- **Block device / network deep dive:** `skills/ec2-launch-template-deployer/references/block-device-and-network.md`
- **Provisioning CLI commands:** `skills/ec2-launch-template-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-ec2-launch-template.md`
- **Eval suite:** `skills/ec2-launch-template-deployer/evals/evals.json`
- **Legacy test cases:** `skills/ec2-launch-template-deployer/eval/test-cases.yaml`
