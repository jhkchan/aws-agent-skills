---
name: ec2-launch-template-deployer
description: 'Provisions EC2 Launch Templates with production defaults: AMI and architecture validation (x86_64 / arm64 Graviton), instance type, key pair, security groups, IAM instance profile, user data (base64), block device mapping (EBS gp3 volume type/size/IOPS, instance store), network interfaces (subnet, public IP, primary IPv6), IMDSv2 (HttpTokens=required, hop limit), tag specs (instance, volume, ENI), capacity-reservation targeting (CapacityReservationSpecification: open|targeted|none), CPU options, license specs. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating or versioning a launch template, requiring IMDSv2, targeting Graviton types, configuring block devices, or binding a Capacity Reservation. Triggers: create launch template, EC2 launch template version, IMDSv2 required, Graviton launch template, block device mapping, capacity reservation targeting.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with ec2 (create-launch-template, create-launch-template-version, describe-launch-templates, describe-launch-template-versions), iam (describe-instance-profiles), and ec2 describe-capacity-reservations. Works with Terraform aws_launch_template and CloudFormation AWS::EC2::LaunchTemplate.
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
  tags: aws, ec2, launch-template, imdsv2, graviton, cloudops, deploy, compute
  dependencies: aws-orchestrator
  keywords: aws, ec2, launch template, imdsv2, graviton, arm64, block device, ebs, gp3, instance store, network interface, capacity reservation, tag specifications, user data, iam instance profile, cloudops, deploy
  when_to_use: 'Invoke when the user wants to create or version an EC2 Launch Template: defining AMI + instance type + key pair + security groups + IAM instance profile + user data, configuring block device mappings (EBS gp3 / instance store), network interfaces (subnet, public IP, IPv6), enforcing IMDSv2 (HttpTokens=required), targeting Graviton (arm64) instance types, attaching tag specifications, or targeting a Capacity Reservation (open | targeted | none). Do NOT invoke for EC2 Instance Connect Endpoint creation (use vpc-network-deployer), for Spot Fleet requests (use ec2-spot-fleet-deployer), for EC2 Auto Scaling group configuration (use autoscaling-policy-deployer), or for auditing existing launch templates (use ec2-security-group-auditor / compute-optimizer-findings-auditor).'
---

# EC2 Launch Template Deployer

An AWS CloudOps agent skill that provisions EC2 Launch Templates
with correct security and performance defaults. The skill walks the
operator through AMI and architecture validation, instance type
selection (including Graviton arm64), block device mapping (EBS gp3
and instance store), network interface configuration, IMDSv2
enforcement, tag specifications, capacity-reservation targeting, and
CPU options. It captures each configuration decision, explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## Activation keywords

create launch template, EC2 launch template version, IMDSv2
required, Graviton launch template, arm64 launch template, block
device mapping, EBS gp3, instance store, network interface, capacity
reservation targeting, tag specifications, IAM instance profile,
user data, HttpTokens required, hop limit, primary IPv6.

## STRICT output contract

When this skill is invoked with a launch-template provisioning
request (AMI, instance type, network, block devices, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `LAUNCH_TEMPLATE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — AMI and architecture validation | x86_64 vs arm64 Graviton |
| Step 2 — Instance type selection | Sizing, Graviton, burstable |
| Step 3 — Key pair, security groups, IAM profile | Identity and access |
| Step 4 — User data | Bootstrap script (base64) |
| Step 5 — Block device mapping | EBS gp3 / instance store |
| Step 6 — Network interfaces | Subnet, public IP, IPv6, SG |
| Step 7 — IMDSv2 enforcement | HttpTokens=required |
| Step 8 — Tag specifications | Instance, volume, ENI tags |
| Step 9 — Capacity reservation targeting | open / targeted / none |
| Step 10 — CPU options and license specs | Cores, threads, licenses |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/block-device-and-network.md | Block device / ENI deep dive |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Configuration dependency graph (novel heuristic)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: IMDSv2 enforcement

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: Graviton (arm64) instance type selection

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Expert heuristic: block device mapping — gp3 vs gp2

Moved verbatim to [references/block-device-and-network.md](references/block-device-and-network.md) - load on demand (see References below).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with EC2 access | Cannot provision without it | `aws sts get-caller-identity` |
| Region selected | AMIs, instance types, and AZs are region-scoped | `aws configure get region` |
| AMI exists in the region | Cross-region AMI IDs are invalid | `aws ec2 describe-images --image-ids <ami-id>` |
| AMI architecture matches instance type | x86_64 AMI on Graviton (arm64) fails at boot | `describe-images` Architecture field |
| Instance type available in the AZ | Not all types are in all AZs | `aws ec2 describe-instance-type-offerings --location-type availability-zone --filters Name=instance-type,Values=<type>` |
| Key pair exists in the region (if specified) | Key pairs are region-scoped | `aws ec2 describe-key-pairs --key-names <name>` |
| Security groups in the target VPC | SGs from another VPC silently accepted, fail at launch | `aws ec2 describe-security-groups --group-ids <sg-id>` then check VpcId |
| IAM instance profile exists with a role | Profile without attached role → no credentials | `aws iam describe-instance-profiles --instance-profile-name <name>` |
| Subnet exists in the target VPC | Cross-VPC subnet + SG combo fails at launch | `aws ec2 describe-subnets --subnet-ids <subnet-id>` |
| Capacity reservation exists (if targeting) | `targeted` with non-existent ID fails at launch | `aws ec2 describe-capacity-reservations --capacity-reservation-ids <id>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — AMI and architecture validation

The AMI determines the OS, baseline software, and architecture
(x86_64 or arm64). Validate before creating the template.

**Verify AMI exists and check architecture:**
```bash
aws ec2 describe-images --image-ids ami-0abcdef1234567890 \
  --query 'Images[0].[Architecture,Name,RootDeviceType]' --output text
# Returns: arm64    al2023-ami-2023.0.20240820-kernel-6.1-arm64    ebs
```

**Architecture compatibility matrix:**

| AMI Architecture | Compatible Instance Families |
|---|---|
| `x86_64` | c5, c6i, c7i, m5, m6i, m7i, r5, r6i, r7i, t3, t3a, x2ied |
| `arm64` | c6g, c7g, m6g, m7g, r6g, r7g, t4g (Graviton) |
| `x86_64_mac` | mac1.metal, mac2.metal (macOS — dedicated host required) |

**Common mistake:** specifying an x86_64 AMI with a Graviton instance
type (e.g., `c7g.large`). The template creates successfully but the
instance fails to boot with no obvious error. Always verify
architecture match.

## Step 2 — Instance type selection

The instance type determines vCPUs, memory, network performance, and
storage. Graviton (arm64) families offer 20-40% price-performance
gains over x86_64 if the application supports arm64.

**Family selection by workload:**

| Workload | x86_64 | arm64 (Graviton) |
|---|---|---|
| General purpose (web, microservices) | m7i, m6i | m7g (cheaper) |
| Compute-optimized (batch, HPC) | c7i, c6i | c7g |
| Memory-optimized (databases) | r7i, r6i | r7g |
| Burstable (dev, low-traffic) | t3 | t4g (cheapest) |

**Verify instance type is available in the AZ:**
```bash
aws ec2 describe-instance-type-offerings \
  --location-type availability-zone \
  --filters Name=instance-type,Values=m7g.large \
  --query 'InstanceTypeOfferings[*].Location' --output text
```

**Common mistake:** specifying a Graviton instance type with an x86_64
AMI. Always verify architecture compatibility in Step 1.

## Step 3 — Key pair, security groups, IAM instance profile

These define how the instance is accessed, what network rules apply,
and what IAM permissions the application has.

```json
{
  "KeyName": "my-key-pair",
  "SecurityGroupIds": ["sg-0abc123", "sg-0def456"],
  "IamInstanceProfile": {
    "Arn": "arn:aws:iam::123456789012:instance-profile/web-server-role"
  }
}
```

**Key rules:**
- The key pair must exist in the same region as the instance.
- All security groups must be in the same VPC as the subnet (Step 6).
- The IAM instance profile must have a role attached (profile name
  without a role produces instances with no credentials).
- Use `SecurityGroupIds` (not `SecurityGroups`) for VPC instances.

**Verify IAM instance profile has a role:**
```bash
aws iam describe-instance-profiles \
  --instance-profile-name web-server-role \
  --query 'InstanceProfiles[0].Roles[0].RoleName' --output text
```

## Step 4 — User data (bootstrap script)

User data is a base64-encoded script that runs at first boot (root on
Linux, local admin on Windows). The primary bootstrap mechanism.

```bash
# CLI base64-encodes with file://
aws ec2 create-launch-template \
  --launch-template-data '{"UserData": "'"$(base64 user-data.sh | tr -d '\n')"'"}'
```

**Key rules:**
- 16 KB limit (base64). For larger scripts, download from S3 in the
  user data itself.
- Runs only on first boot by default. Use `cloud-init` `per-boot` for
  scripts that run on every start.
- User data is visible in IMDS and the console — **never put secrets
  in user data.** Fetch from Secrets Manager or Parameter Store.

**Common mistake:** putting passwords or API keys in user data —
readable by anyone with `ec2:DescribeInstanceAttribute` or console
access. This is an immediate credential leak.

## Step 5 — Block device mapping

Block device mapping defines EBS and instance store volumes.

```json
{
  "BlockDeviceMappings": [
    {
      "DeviceName": "/dev/xvda",
      "Ebs": {
        "VolumeSize": 30,
        "VolumeType": "gp3",
        "Iops": 3000,
        "Throughput": 125,
        "DeleteOnTermination": true,
        "Encrypted": true
      }
    },
    {
      "DeviceName": "/dev/xvdb",
      "Ebs": {
        "VolumeSize": 100,
        "VolumeType": "gp3",
        "Iops": 6000,
        "Throughput": 250,
        "DeleteOnTermination": true,
        "Encrypted": true
      }
    }
  ]
}
```

See the "Expert heuristic: block device mapping" section for the gp3
vs gp2 decision framework and the `DeleteOnTermination` /
instance-store gotchas. Production defaults: `gp3`,
`DeleteOnTermination=true`, `Encrypted=true` on all volumes.

## Step 6 — Network interfaces

Network interfaces (ENIs) define subnet, public IP, security groups,
and IPv6.

```json
{
  "NetworkInterfaces": [
    {
      "DeviceIndex": 0,
      "SubnetId": "subnet-0abc123def456",
      "Groups": ["sg-0abc123", "sg-0def456"],
      "AssociatePublicIpAddress": true,
      "Ipv6AddressCount": 1
    }
  ]
}
```

**Key rules:**
- `AssociatePublicIpAddress` is only honored on `DeviceIndex=0`.
- Use `Groups` inside `NetworkInterfaces`, not the top-level
  `SecurityGroupIds`. If both are set, `Groups` wins and the
  top-level is silently ignored.
- The subnet's VPC must match all SGs' VPC. A mismatch fails at
  launch, not at template creation.
- `Ipv6AddressCount` requires the subnet to have an IPv6 CIDR block.

**Common mistake:** specifying `SecurityGroupIds` at the top level
AND `Groups` inside `NetworkInterfaces` — the top-level is silently
overridden. Use one; prefer `NetworkInterfaces.Groups` for VPC.

## Step 7 — IMDSv2 enforcement

See the "Expert heuristic: IMDSv2 enforcement" section above for the
full lifecycle. Summary configuration:

```json
{
  "MetadataOptions": {
    "HttpEndpoint": "enabled",
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 2,
    "InstanceMetadataTags": "enabled"
  }
}
```

**Field semantics:**
- `HttpEndpoint: enabled` — IMDS endpoint is reachable.
- `HttpTokens: required` — **This is the IMDSv2 enforcement field.**
  v1 GET requests are rejected. Without this, IMDSv1 is available
  and vulnerable to SSRF.
- `HttpPutResponseHopLimit: 2` — number of network hops allowed for
  the token PUT. Default 1; set to 2 or 3 for containers (ECS, EKS,
  Docker).
- `InstanceMetadataTags: enabled` — allows tags to be retrieved via
  IMDS (optional but useful for instance self-discovery).

**Common mistake:** setting only `HttpEndpoint=enabled` and assuming
IMDSv2 is enforced. It is not — `HttpTokens=required` is the field
that rejects v1 requests.

## Step 8 — Tag specifications

Tag specifications apply tags to resources created from the template.
Each resource type must be listed separately: `instance`, `volume`,
`network-interface`, and `spot-instances-request`.

```json
{
  "TagSpecifications": [
    {
      "ResourceType": "instance",
      "Tags": [
        { "Key": "Name", "Value": "web-server" },
        { "Key": "Environment", "Value": "production" }
      ]
    },
    {
      "ResourceType": "volume",
      "Tags": [
        { "Key": "Name", "Value": "web-server-root" }
      ]
    }
  ]
}
```

**Key rule:** `spot-instances-request` tags apply ONLY to the Spot
request object, NOT the resulting instance. To tag a Spot instance,
also include `instance` in the same `TagSpecifications` list. This
is the #1 tagging surprise for Spot workloads.

## Step 9 — Capacity reservation targeting

Capacity Reservation targeting controls whether instances launched
from this template consume an existing On-Demand Capacity Reservation
(ODCR).

```json
{
  "CapacityReservationSpecification": {
    "CapacityReservationTarget": {
      "CapacityReservationIds": ["cr-0abc123def456"]
    }
  }
}
```

**Three targeting modes:**

| Mode | Config | Behavior |
|---|---|---|
| `open` | `CapacityReservationPreference: "open"` | Instance consumes any matching `open` ODCR automatically |
| `targeted` | `CapacityReservationTarget: { CapacityReservationIds: [...] }` | Instance consumes the specific ODCR by ID |
| `none` (implicit) | No specification | Instance does not consume any ODCR; billed as On-Demand |

**Key rules:**
- The ODCR's `InstanceType`, `AvailabilityZone`, and `InstancePlatform`
  must match the template's instance configuration exactly.
- A `targeted` ODCR with no matching pool (wrong AZ, wrong type,
  expired reservation) silently falls back to On-Demand billing.
  There is no error signal — verify with `describe-capacity-reservations`.

**Verify the reservation is active and matches:**
```bash
aws ec2 describe-capacity-reservations \
  --capacity-reservation-ids cr-0abc123def456 \
  --query 'CapacityReservations[0].[State,InstanceType,AvailabilityZone,InstancePlatform]' --output text
```

## Step 10 — CPU options and license specifications

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Step 11 — Recent features

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## NEVER do these things

1. **NEVER create a launch template without `HttpTokens=required`
   (IMDSv2).** A template without this leaves the instance vulnerable
   to SSRF-driven IMDSv1 credential theft. The default is `optional`;
   always set `HttpTokens=required` and `HttpEndpoint=enabled`
   together. This is the single most common Security Hub EC2 finding.

2. **NEVER pair an x86_64 AMI with a Graviton (arm64) instance
   type.** The template creates successfully but the instance fails
   to boot (pending → shutting-down). Always verify
   `Image.Architecture` matches the instance family (arm64 for
   c6g/c7g/m6g/m7g/r6g/r7g/t4g; x86_64 for everything else).

3. **NEVER mix security groups from a different VPC than the
   subnet.** A security group from VPC-A with a subnet from VPC-B is
   silently accepted in the template but fails at instance launch
   with `InvalidParameterCombination`. Verify all SGs share the
   subnet's VpcId.

4. **NEVER leave `DeleteOnTermination=false` on non-root EBS volumes
   for stateless workloads.** Orphaned volumes accumulate cost
   silently (a 100 GB gp3 volume is ~$8/month — thousands across a
   fleet). Set `DeleteOnTermination=true` on all volumes attached to
   ephemeral/stateless instances.

5. **NEVER put secrets in user data.** User data is readable via
   `ec2:DescribeInstanceAttribute`, the console, and IMDS. Fetch
   secrets at runtime from Secrets Manager or Parameter Store.
   Baseline templates with `password=...` in user data are an
   immediate credential leak.

## Output format

```text
LAUNCH_TEMPLATE: <lt-id> (version <n>, name: <name>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] AMI: <ami-id> (architecture: <x86_64|arm64>, OS: <name>)
  [✓|✗] Instance type: <type> (architecture: <x86_64|arm64>, vCPUs: <n>)
  [✓|✗] Architecture match: AMI <arch> == instance <arch>
  [✓|✗] Key pair: <name>
  [✓|✗] Security groups: <sg-1>, <sg-2> (VPC: <vpc-id>)
  [✓|✗] IAM instance profile: <name> (role: <role-name>)
  [✓|✗] User data: <size> bytes (base64) | none
  [✓|✗] Block devices: root <size> <type> (DeleteOnTerm: true), <n> additional volumes
  [✓|✗] Network interface: subnet <subnet-id>, public IP <true|false>, IPv6 <count|none>
  [✓|✗] IMDSv2: HttpTokens=required, hop limit <n>
  [✓|✗] Tag specifications: instance, volume, network-interface (<n> tags each)
  [✓|✗] Capacity reservation: <open|targeted: <id>|none>
  [✓|✗] CPU options: <core-count> cores x <threads-per-core> threads | default
VERIFICATION_COMMANDS:
  aws ec2 describe-launch-template-versions --launch-template-id <lt-id>
  aws ec2 describe-launch-templates --launch-template-ids <lt-id>
```

### Worked example — Graviton web server with IMDSv2, gp3, and tags

```text
LAUNCH_TEMPLATE: lt-0abc123def456 (version 1, name: graviton-web-server)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] AMI: ami-0abcdef1234567890 (architecture: arm64, OS: al2023-ami-2023.0.20240820-kernel-6.1-arm64)
  [✓] Instance type: m7g.large (architecture: arm64, vCPUs: 2)
  [✓] Architecture match: AMI arm64 == instance arm64
  [✓] Key pair: prod-graviton-key
  [✓] Security groups: sg-0abc123, sg-0def456 (VPC: vpc-0abc123def)
  [✓] IAM instance profile: web-server-role (role: web-server-role)
  [✓] User data: 2048 bytes (base64)
  [✓] Block devices: root 30 gp3 (DeleteOnTerm: true), 1 additional volume (100 gp3)
  [✓] Network interface: subnet subnet-0abc123def, public IP true, IPv6 1
  [✓] IMDSv2: HttpTokens=required, hop limit 2
  [✓] Tag specifications: instance (3 tags), volume (2 tags), network-interface (1 tag)
  [✓] Capacity reservation: none
  [✓] CPU options: default
VERIFICATION_COMMANDS:
  aws ec2 describe-launch-template-versions --launch-template-id lt-0abc123def456 --versions 1
  aws ec2 describe-launch-templates --launch-template-ids lt-0abc123def456
```

## Error handling

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset, configuration dependency graph, IMDSv2/Graviton/block-device expert heuristics, Step 10 CPU options and license specs, and 2023-2026 recent features, moved verbatim from SKILL.md
- [references/error-handling.md](references/error-handling.md) — boot-failure, InvalidParameterCombination, IMDSv2, capacity-reservation, and orphaned-volume error handling, moved verbatim from SKILL.md
- [references/block-device-and-network.md](references/block-device-and-network.md) — extended with the gp3 vs gp2 decision framework moved verbatim from SKILL.md
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — unchanged copy-pasteable CLI sequence (see Quick navigation)

## Domain

AWS CloudOps / EC2 Launch Template Provisioning & Compute
Configuration Standardization.

## AWS documentation

- **Launch Templates** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-templates.html
- **IMDSv2** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html
- **Block device mapping** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html
- **EBS volume types** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html
- **Graviton** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html
- **Capacity Reservations** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-capacity-reservations.html
- **CPU options** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-optimize-cpu.html
