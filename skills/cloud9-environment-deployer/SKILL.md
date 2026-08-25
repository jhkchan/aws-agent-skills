---
name: cloud9-environment-deployer
description: 'Provisions AWS Cloud9 environments with production defaults: EC2 instance type selection, platform (Amazon Linux, Ubuntu), connection mode (SSH, SSM), subnet and security group configuration, automatic hibernation (idle timeout), IAM role (instance profile), SSH key for external access, environment sharing (read/write permissions), EC2 lifecycle (start/stop/delete), CloudWatch monitoring, cost optimization (auto-hibernate), no-ingress SSM connection (no public key needed), integration with CodeCommit/GitHub, Node.js/Python/Go runtime pre-installed. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Cloud9 environment, setting up SSM-based no-ingress Cloud9, configuring auto-hibernation, sharing a Cloud9 environment with a team, or managing Cloud9 EC2 lifecycle. Triggers: create cloud9 environment, ssm cloud9 no ingress, cloud9 auto hibernate, cloud9 team sharing, cloud9 ec2 lifecycle, cloud9 ubuntu, cloud9 amazon linux, cloud9 cost optimization.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloud9 and ec2 access (and iam:PassRole for instance profile, ssm for SSM connection mode). Works with Terraform aws_cloud9_environment_ec2 resource and CloudFormation AWS::Cloud9::EnvironmentEC2 templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloud9, cloudops, deploy, devtools, ide, provisioning, ssm, cost-optimization, sharing
  dependencies: aws-orchestrator
  keywords: aws, cloud9, cloud9 environment, cloudops, deploy, provisioning, ssm connection, ssh connection, auto hibernate, environment sharing, ec2 lifecycle, cost optimization, no ingress, instance profile, codecommit
  when_to_use: Invoke when the user wants to create an AWS Cloud9 environment, configure SSM-based no-ingress connection, set up auto-hibernation for cost optimization, share a Cloud9 environment with team members, manage Cloud9 EC2 lifecycle (start/stop/delete), or integrate Cloud9 with CodeCommit/GitHub. Do NOT invoke for AWS CloudShell (browser-based shell, no provisioning needed), AWS CodeBuild (CI/CD build service), or AWS CodeStar (project management).
---

# Cloud9 Environment Deployer

An AWS CloudOps agent skill that provisions AWS Cloud9 environments
with correct defaults. The skill walks the operator through instance
type selection, platform choice (Amazon Linux or Ubuntu), connection
mode (SSM no-ingress vs SSH with key pair), subnet and security group
configuration, automatic hibernation settings, IAM instance profile,
environment sharing permissions, EC2 lifecycle management, and cost
optimization. It captures environment decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create Cloud9 environment, SSM Cloud9 no ingress, Cloud9 auto hibernate,
Cloud9 team sharing, Cloud9 EC2 lifecycle, Cloud9 Ubuntu, Cloud9 Amazon
Linux, Cloud9 cost optimization.

## STRICT output contract

When this skill is invoked with a Cloud9-provisioning request (create
an environment, configure SSM connection, set up auto-hibernation,
share with team, manage lifecycle, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`CLOUD9_ENVIRONMENT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Environment model (EC2-backed) | Core Cloud9 model |
| Step 2 — Connection mode (SSM vs SSH) | Connectivity decision |
| Step 3 — Platform selection (Amazon Linux, Ubuntu) | OS + runtimes |
| Step 4 — Instance type and lifecycle | Compute sizing |
| Step 5 — Subnet and security group | Network placement |
| Step 6 — IAM instance profile | Permissions for the IDE |
| Step 7 — Automatic hibernation | Cost optimization |
| Step 8 — Environment sharing | Team collaboration |
| Step 9 — Git integration (CodeCommit, GitHub) | Source control |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/connection-modes-and-iam.md | SSM/SSH + IAM detail |
| references/sharing-and-cost-optimization.md | Sharing + hibernation detail |

## Mindset

**One-line takeaway:** A Cloud9 environment is an EC2-backed cloud IDE.
SSM connection mode eliminates the need for inbound security rules (no
public SSH key, no ingress). Auto-hibernation stops the EC2 instance
after idle timeout to control cost. Sharing grants team members read or
write access to the same IDE. The instance profile IAM role determines
what AWS permissions the IDE has.

Three misconceptions dominate Cloud9 misconfiguration at provisioning
time:

- **"Cloud9 needs SSH access (port 22 ingress) to work."** NOT with SSM
  connection mode. SSM (Systems Manager) connection uses the SSM agent
  on the EC2 instance to establish a secure tunnel via AWS backbone —
  NO inbound security group rule, NO public SSH key, NO bastion host
  needed. This is the recommended connection mode for security and
  simplicity. SSH connection mode is the legacy default and requires
  port 22 ingress + a key pair.

- **"The Cloud9 EC2 instance runs 24/7 unless manually stopped."**
  Without auto-hibernation, yes — and this is a major cost drain.
  Auto-hibernation (`--automatic-stop-time-minutes`) stops the EC2
  instance after N minutes of IDE inactivity. The instance restarts
  automatically when the user opens the IDE again. This is the single
  most impactful cost optimization for Cloud9.

- **"Sharing a Cloud9 environment means sharing AWS credentials."** It
  does NOT. When you share a Cloud9 environment, each user connects
  using their own AWS credentials (via the environment's IAM managed
  temporary credentials). The instance profile role is NOT shared; each
  user's permissions are governed by their own IAM identity federated
  through Cloud9's credential management.

## Configuration dependency graph (novel heuristic)

Cloud9 configurations are NOT independent. The connection mode
determines whether a key pair and ingress rule are needed. The subnet
determines network placement. The instance profile determines
permissions. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Environment (EC2-backed) | subnet exists; instance profile exists; instance type valid | SSM connection requires SSM agent pre-installed (Amazon Linux and Ubuntu AMIs have it) | the cloud IDE |
| Connection mode (SSM) | SSM agent on instance; instance profile with SSM permissions | no inbound rule needed; no key pair needed; security group can have no ingress | secure no-ingress access |
| Connection mode (SSH) | key pair exists; security group with port 22 ingress from trusted CIDR | requires public subnet (or bastion); port 22 exposed to the specified CIDR | traditional SSH access |
| Instance profile | IAM role with trust policy for ec2.amazonaws.com; permissions for user's workflows | missing SSM permissions in the role = SSM connection fails silently | AWS permissions for the IDE |
| Auto-hibernation | `--automatic-stop-time-minutes` set at creation | can be modified post-creation but instance must be restarted | cost optimization |
| Subnet | subnet exists; if SSH, must have route to internet (public) or bastion | private subnet without NAT = no package installs, no Git push | network placement |
| Sharing | environment exists; target users have IAM identity | write sharing allows concurrent edits; no merge conflict resolution | team collaboration |

**The connection-mode-and-instance-profile row is the one a baseline
model misses.** Creating a Cloud9 environment with SSM connection
requires the instance profile to have SSM permissions
(`AmazonSSMManagedInstanceCore` policy). Without it, the environment is
created but the IDE fails to connect silently.

## Expert heuristic: SSM connection eliminates inbound rules

A baseline model says "open port 22 for SSH." The correct heuristic
recognizes that SSM connection mode is the modern, secure default that
requires NO inbound security group rules.

```text
SSH connection mode (legacy):
  └── Requires: key pair + security group with port 22 ingress + public subnet
      Risk: port 22 exposed (even to a CIDR); key pair management overhead

SSM connection mode (recommended):
  └── Requires: SSM agent (pre-installed on AL2/Ubuntu) + instance profile with AmazonSSMManagedInstanceCore
      No key pair needed; no inbound rule needed; works in private subnets
      Connection via AWS backbone (not public internet)
```

**Key implication:** SSM connection mode is more secure (no exposed
ports), simpler (no key pair management), and more flexible (works in
private subnets without a bastion). Use SSM unless there is a specific
reason for SSH (e.g., external SSH client access).

## Expert heuristic: auto-hibernate for cost control

A baseline model says "create the environment." The correct heuristic
recognizes that without auto-hibernation, the EC2 instance runs 24/7.

```text
Auto-hibernation (--automatic-stop-time-minutes):
  ├── 30 minutes (default for console-created environments)
  ├── 60 minutes (recommended for active development teams)
  ├── 240 minutes (for long-running builds/debugging sessions)
  └── 0 / unset (never auto-stop — HIGHEST COST, avoid)

Cost impact (t3.medium, us-east-1, approximate):
  No hibernation:   730 hours/month × $0.0416/hour = ~$30/month
  30-min hibernate: ~4 hours/day × 22 days = 88 hours = ~$3.66/month
  Savings: ~88% reduction
```

**Key implication:** auto-hibernation is the single most impactful cost
optimization for Cloud9. Always set `--automatic-stop-time-minutes`.
Never leave it unset (0 means never stop).

## Expert heuristic: sharing for team collaboration

```text
Sharing a Cloud9 environment:
  ├── Read sharing: user can view code and run commands (read-only)
  ├── Write sharing: user can edit files (concurrent edits, no merge resolution)
  └── Each user connects with their OWN AWS credentials
      → IAM permissions governed by the user's identity, not the instance profile
      → Managed temporary credentials are scoped per-user

Sharing flow:
  1. Environment created with --permissions 'read' or 'read,write'
  2. Share via IAM: add user/role ARN to the environment's permissions
     aws cloud9 create-environment-membership \
       --environment-id <env-id> \
       --user-arn arn:aws:iam::<acct>:user/<user> \
       --permissions read-write
  3. User opens the environment from their own Cloud9 console
```

**Key implication:** sharing does NOT share credentials. Each user's
AWS permissions are independent. The instance profile is the fallback
for operations not covered by managed temporary credentials.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Subnet exists | Cloud9 needs a subnet for EC2 placement | `aws ec2 describe-subnets --subnet-ids <subnet-id>` |
| Instance profile (IAM role) exists | EC2 needs a role for permissions | `aws iam list-instance-profiles` |
| Instance profile has SSM permissions (if SSM mode) | SSM agent needs `AmazonSSMManagedInstanceCore` | Verify attached policies |
| Key pair exists (if SSH mode) | SSH connection requires a key pair | `aws ec2 describe-key-pairs` |
| Security group with port 22 (if SSH mode) | SSH requires port 22 ingress | Verify SG rules |
| Connection mode decided | SSM (no ingress) vs SSH (key pair + port 22) | Confirm choice |
| Auto-hibernation timeout decided | Controls cost | Confirm idle timeout minutes |
| Instance type selected | Determines compute capacity | Confirm type (e.g., t3.medium) |
| Platform selected | Amazon Linux or Ubuntu | Confirm OS |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Environment model (EC2-backed)

Cloud9 environments are EC2-backed. The EC2 instance hosts the IDE,
runs the development environment, and provides compute for builds and
tests.

| Element | Description | API field |
|---|---|---|
| Name | Environment name | `--name` |
| Description | Environment description | `--description` |
| Instance type | EC2 instance type | `--instance-type` |
| Platform | OS (Amazon Linux, Ubuntu) | `--image-id` (AMI) |
| Connection mode | SSM or SSH | `--connection-type` |
| Subnet | VPC subnet for EC2 | `--subnet-id` |
| Auto-stop | Idle timeout (minutes) | `--automatic-stop-time-minutes` |
| Instance profile | IAM role for EC2 | `--instance-profile` |

**Create an environment (SSM mode, auto-hibernate):**

```bash
ENV_ID=$(aws cloud9 create-environment-ec2 \
  --name "dev-team-ide" \
  --description "Shared Cloud9 for dev team" \
  --instance-type t3.medium \
  --image-id amazonlinux-2-x86_64 \
  --connection-type CONNECT_SSM \
  --subnet-id subnet-aaa11122 \
  --automatic-stop-time-minutes 30 \
  --instance-profile Cloud9InstanceProfile \
  --region us-east-1 \
  --query 'environmentId' --output text)

echo "Cloud9 environment ID: $ENV_ID"
```

## Step 2 — Connection mode (SSM vs SSH)

| Feature | SSM (CONNECT_SSM) | SSH (CONNECT_SSH) |
|---|---|---|
| Inbound security group rules | NONE needed | Port 22 required |
| Key pair | NOT needed | Required |
| Public subnet | NOT required (works in private) | Required (or bastion) |
| SSM agent | Required (pre-installed on AL2/Ubuntu) | Not used for connection |
| Instance profile | Needs `AmazonSSMManagedInstanceCore` | Standard EC2 role |
| Security posture | Best (no exposed ports) | Port 22 exposed to CIDR |
| External SSH client | Not supported | Supported |

**Recommendation:** use SSM connection mode (CONNECT_SSM) unless you
need external SSH client access.

### SSM mode requirements

The instance profile MUST include `AmazonSSMManagedInstanceCore`:

```bash
# Verify the instance profile role has SSM permissions
aws iam list-attached-role-policies \
  --role-name Cloud9InstanceProfile \
  --query 'AttachedPolicies[*].PolicyName' --output text
# Must include AmazonSSMManagedInstanceCore
```

### SSH mode requirements

```bash
# Key pair must exist
aws ec2 describe-key-pairs --key-names my-cloud9-key

# Security group must allow port 22 from trusted CIDR
aws ec2 describe-security-groups \
  --group-ids sg-aaa11122 \
  --query 'SecurityGroups[0].IpPermissions[?FromPort==`22`]'
```

## Step 3 — Platform selection (Amazon Linux, Ubuntu)

Cloud9 supports two platforms via image IDs:

| Image ID | Platform | Pre-installed runtimes | SSM agent |
|---|---|---|---|
| `amazonlinux-2-x86_64` | Amazon Linux 2 | Node.js, Python, Docker, Git | Pre-installed |
| `ubuntu-18.04-x86_64` | Ubuntu 18.04 | Node.js, Python, Go, Docker, Git | Pre-installed |

**Note:** Cloud9 uses managed AMIs. The `--image-id` is a Cloud9 alias
(not a raw AMI ID). Available aliases can be listed via:

```bash
aws cloud9 describe-environments \
  --environment-id "$ENV_ID" \
  --query 'environments[0].imageId'
```

**Amazon Linux 2** is the default and most-tested platform. Choose
**Ubuntu** if your team needs specific Ubuntu packages or Go runtime
pre-installed.

## Step 4 — Instance type and lifecycle

| Instance type | vCPU | RAM | Use case |
|---|---|---|---|
| `t3.micro` | 2 | 1 GB | Light editing (minimal) |
| `t3.medium` | 2 | 4 GB | Standard development (recommended) |
| `t3.large` | 2 | 8 GB | Heavier builds, multiple containers |
| `m5.large` | 2 | 8 GB | Production-grade dev |
| `m5.xlarge` | 4 | 16 GB | Large builds, data processing |

### EC2 lifecycle management

```bash
# Start (from stopped/hibernated)
aws ec2 start-instances --instance-ids i-aaa11122

# Stop (manual)
aws ec2 stop-instances --instance-ids i-aaa11122

# Delete the environment (terminates EC2)
aws cloud9 delete-environment \
  --environment-id "$ENV_ID"
```

**Note:** when auto-hibernation triggers, the EC2 instance is STOPPED
(not terminated). Data on the EBS volume is preserved. The instance
restarts automatically when the user opens the IDE.

## Step 5 — Subnet and security group

### SSM mode (recommended — minimal security group)

```bash
# SSM mode: security group with NO inbound rules
# The SSM agent establishes outbound connection to AWS SSM endpoints

# Outbound rules (default): allow all (0.0.0.0/0) for HTTPS to AWS APIs
# Inbound rules: NONE required
```

### SSH mode (requires port 22 ingress)

```bash
# SSH mode: security group with port 22 from trusted CIDR
aws ec2 authorize-security-group-ingress \
  --group-id sg-cloud9-ssh \
  --protocol tcp \
  --port 22 \
  --cidr 10.0.0.0/8  # corporate network only
```

### Subnet requirements

- **SSM mode:** any subnet (public or private) with route to SSM
  endpoints (via NAT gateway, VPC endpoints, or IGW).
- **SSH mode:** public subnet with route to internet gateway (or
  reachable via bastion host).

## Step 6 — IAM instance profile

The instance profile determines what AWS permissions the Cloud9 IDE
has. For SSM mode, it MUST include `AmazonSSMManagedInstanceCore`.

```bash
# Create the IAM role for Cloud9
aws iam create-role \
  --role-name Cloud9InstanceProfile \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

# Attach SSM permissions (required for SSM connection)
aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Attach additional permissions as needed (e.g., S3, CodeCommit)
aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AWSCodeCommitReadOnly

# Create the instance profile
aws iam create-instance-profile \
  --instance-profile-name Cloud9InstanceProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name Cloud9InstanceProfile \
  --role-name Cloud9InstanceProfile
```

**Cloud9 managed temporary credentials:** when a user opens the IDE,
Cloud9 issues managed temporary credentials scoped to the user's IAM
permissions. These are used for AWS CLI/SDK calls within the IDE. The
instance profile is the fallback for operations not covered by managed
temporary credentials.

## Step 7 — Automatic hibernation

Auto-hibernation stops the EC2 instance after N minutes of IDE
inactivity, reducing cost dramatically.

```bash
# Set at creation time
aws cloud9 create-environment-ec2 \
  --name "dev-ide" \
  --automatic-stop-time-minutes 30 \
  ...

# Update post-creation (requires instance restart)
# Note: automatic-stop-time-minutes is set at creation.
# To change, you must delete and recreate the environment.
```

| Timeout | Use case |
|---|---|
| 15 minutes | Individual developer (aggressive cost savings) |
| 30 minutes | Small team (balanced) |
| 60 minutes | Active development with frequent breaks |
| 240 minutes | Long-running builds or debugging sessions |
| 0 (unset) | NEVER auto-stop — avoid (high cost) |

**Critical:** the timeout is set at creation and cannot be modified
without recreating the environment. Choose carefully.

## Step 8 — Environment sharing

Sharing allows team members to access the same Cloud9 IDE.

### Share with specific users

```bash
# Grant read-write access
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate \
  --permissions read-write

# Grant read-only access
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/reviewer \
  --permissions read-only
```

### List environment members

```bash
aws cloud9 describe-environment-memberships \
  --environment-id "$ENV_ID"
```

### Remove a member

```bash
aws cloud9 delete-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate
```

**Important:** each member connects with their OWN AWS credentials.
The instance profile is NOT shared. Permissions are governed per-user.

## Step 9 — Git integration (CodeCommit, GitHub)

### AWS CodeCommit integration

```bash
# The instance profile needs CodeCommit permissions
# Attach AWSCodeCommitReadOnly (or PowerUser) to the role

# Inside the Cloud9 IDE, configure Git credentials
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true

# Clone a CodeCommit repo
git clone https://git-codecommit.us-east-1.amazonaws.com/v1/repos/my-repo
```

### GitHub integration

```bash
# Inside the Cloud9 IDE, configure GitHub credentials
# Option 1: SSH key (generate in IDE, add to GitHub)
ssh-keygen -t ed25519 -C "cloud9-dev"
cat ~/.ssh/id_ed25519.pub
# Add the public key to GitHub → Settings → SSH keys

# Option 2: HTTPS with personal access token
git clone https://github.com/org/repo.git
# Enter token when prompted

# Option 3: GitHub CLI
sudo yum install -y gh  # Amazon Linux
gh auth login
```

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **SSM connection mode maturity (2023-2024):** SSM connection is now
  the recommended default for new Cloud9 environments, eliminating port
  22 exposure and key pair management. All Amazon Linux 2 and Ubuntu
  Cloud9 AMIs ship with the SSM agent pre-installed.

- **Ubuntu 22.04 support (2023-2024):** Cloud9 now supports Ubuntu
  22.04 LTS as a platform option, in addition to Amazon Linux 2 and
  Ubuntu 18.04. Includes updated Node.js 18, Python 3.10, and Go 1.20.

- **CloudWatch integration for Cloud9 (2023-2024):** Cloud9 now
  publishes EC2 instance metrics (CPU, memory, network) to CloudWatch,
  enabling dashboards and alarms for environment health monitoring.

- **Enhanced no-ingress support (2024-2025):** SSM connection mode now
  works with VPC endpoints for SSM, enabling fully private Cloud9
  environments with no internet gateway and no NAT gateway.

- **Terraform provider support (2024-2025):** The Terraform
  `aws_cloud9_environment_ec2` resource now supports all connection
  types and automatic-stop-time-minutes, with improved drift detection.

- **Cost optimization dashboards (2024-2025):** AWS Cost Explorer now
  includes Cloud9-specific cost breakdowns, showing per-environment
  EC2 uptime and hibernation savings.

## NEVER do these things

1. **NEVER create a Cloud9 environment without auto-hibernation.**
   Without `--automatic-stop-time-minutes`, the EC2 instance runs 24/7.
   This is the #1 cost drain. Always set a timeout (30 minutes is the
   recommended default).

2. **NEVER use SSH connection mode when SSM is available.** SSM mode
   eliminates port 22 exposure and key pair management. Use SSH only
   when external SSH client access is required.

3. **NEVER create an SSM-connected environment without SSM permissions
   in the instance profile.** The role MUST include
   `AmazonSSMManagedInstanceCore`. Without it, the environment is
   created but the IDE silently fails to connect.

4. **NEVER leave the security group with port 22 open to 0.0.0.0/0.**
   If SSH mode is required, restrict port 22 to the corporate CIDR
   (e.g., 10.0.0.0/8). Never expose SSH to the entire internet.

5. **NEVER share a Cloud9 environment without understanding the
   permissions model.** Sharing grants IDE access, but each user's AWS
   permissions are governed by their OWN IAM identity. The instance
   profile is NOT shared.

6. **NEVER use t3.micro for real development.** 1 GB RAM is
   insufficient for most development tasks (Node.js, Python, Docker).
   Use t3.medium (4 GB) as the minimum for productive development.

7. **NEVER deploy Cloud9 in a private subnet without SSM VPC endpoints
   or NAT gateway.** The EC2 instance needs outbound access to SSM
   endpoints (for SSM mode) or the internet (for package installs).
   Without routes, the IDE cannot connect or install packages.

8. **NEVER forget to delete unused Cloud9 environments.** Even with
   auto-hibernation, stopped instances incur EBS storage costs.
   Delete environments when no longer needed.

9. **NEVER assume auto-stop-time-minutes can be changed post-creation.**
   It is set at creation and requires environment recreation to change.
   Choose carefully at provisioning time.

10. **NEVER store long-lived AWS credentials in the Cloud9 IDE.** Use
    managed temporary credentials (automatic) or IAM roles. Long-lived
    access keys in the IDE are a security risk.

## Output format

```text
CLOUD9_ENVIRONMENT: <environment-name> (<environment-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Environment name: <name>
  [✓|✗] Instance type: <type> (<vcpu> vCPU, <ram> GB RAM)
  [✓|✗] Platform: Amazon Linux 2 | Ubuntu 18.04 | Ubuntu 22.04
  [✓|✗] Connection mode: SSM (CONNECT_SSM, no ingress) | SSH (CONNECT_SSH, port 22)
  [✓|✗] Subnet: <subnet-id> (public | private)
  [✓|✗] Security group: <sg-id> (no ingress for SSM | port 22 from <cidr> for SSH)
  [✓|✗] Instance profile: <role-name> (includes AmazonSSMManagedInstanceCore if SSM)
  [✓|✗] Key pair: <key-name> (SSH mode) | Not required (SSM mode)
  [✓|✗] Auto-hibernation: <minutes> minutes
  [✓|✗] Sharing: <count> members (<read-write-count> read-write, <read-only-count> read-only)
  [✓|✗] Git integration: CodeCommit (<repo>) | GitHub (<repo>) | None
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloud9 describe-environments --environment-ids <env-id> --region <region>
  aws ec2 describe-instances --filters Name=tag:aws:cloud9:environment,Values=<env-id> --region <region>
  aws cloud9 describe-environment-memberships --environment-id <env-id> --region <region>
```

### Worked example — SSM no-ingress Cloud9 with auto-hibernate and team sharing

```text
CLOUD9_ENVIRONMENT: dev-team-ide (abc12345-6789-def0)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Environment name: dev-team-ide
  [✓] Instance type: t3.medium (2 vCPU, 4 GB RAM)
  [✓] Platform: Amazon Linux 2
  [✓] Connection mode: SSM (CONNECT_SSM, no ingress)
  [✓] Subnet: subnet-aaa11122 (private)
  [✓] Security group: sg-cloud9-ssm (no inbound rules)
  [✓] Instance profile: Cloud9InstanceProfile (includes AmazonSSMManagedInstanceCore)
  [✓] Key pair: Not required (SSM mode)
  [✓] Auto-hibernation: 30 minutes
  [✓] Sharing: 2 members (2 read-write)
  [✓] Git integration: CodeCommit (my-app-repo)
  [✓] Tags: Environment=production, Team=dev, ManagedBy=cloud9
VERIFICATION_COMMANDS:
  aws cloud9 describe-environments --environment-ids abc12345-6789-def0 --region us-east-1
  aws ec2 describe-instances --filters Name=tag:aws:cloud9:environment,Values=abc12345-6789-def0 --region us-east-1
  aws cloud9 describe-environment-memberships --environment-id abc12345-6789-def0 --region us-east-1
```

## Error handling

### Environment creation fails
- Verify the subnet exists and is in the same region. Verify the
  instance type is valid. Verify the instance profile exists and has
  the correct trust policy. For SSM mode, verify
  `AmazonSSMManagedInstanceCore` is attached.

### IDE fails to connect (SSM mode)
- Verify the instance profile has `AmazonSSMManagedInstanceCore`. Verify
  the SSM agent is running (check Systems Manager console). Verify
  outbound connectivity to SSM endpoints (NAT gateway, VPC endpoints,
  or IGW for public subnets).

### IDE fails to connect (SSH mode)
- Verify the key pair matches. Verify port 22 is allowed in the security
  group from the user's IP. Verify the instance is in a public subnet
  with an internet gateway route.

### Auto-hibernation not triggering
- Verify `--automatic-stop-time-minutes` is set (not 0). Note: the
  timer counts IDE inactivity, not EC2 CPU utilization. The IDE must
  be closed or idle (no active terminal sessions).

### Sharing not working for a user
- Verify the user's IAM identity is correct. Verify the user has
  `cloud9:GetUserPermissions` and `cloud9:DescribeEnvironmentMemberships`
  permissions. The user must open the environment from their own Cloud9
  console.

### EC2 instance stuck in stopped state
- If hibernated, opening the IDE should restart it. If it does not,
  manually start: `aws ec2 start-instances --instance-ids <i-id>`.
  Verify the instance is not in error state.

## Domain

AWS CloudOps / AWS Cloud9 Environment Provisioning & Cloud IDE
Management.

## AWS documentation

- **Cloud9 User Guide** — https://docs.aws.amazon.com/cloud9/latest/user-guide/welcome.html
- **Create environment** — https://docs.aws.amazon.com/cloud9/latest/user-guide/create-environment.html
- **SSM connection mode** — https://docs.aws.amazon.com/cloud9/latest/user-guide/setting-up.html
- **Environment sharing** — https://docs.aws.amazon.com/cloud9/latest/user-guide/share-environment.html
- **Auto-hibernation** — https://docs.aws.amazon.com/cloud9/latest/user-guide/move-environment.html
- **Instance profiles** — https://docs.aws.amazon.com/cloud9/latest/user-guide/credentials.html
- **CodeCommit integration** — https://docs.aws.amazon.com/cloud9/latest/user-guide/sample-codecommit.html
- **Cloud9 API** — https://docs.aws.amazon.com/cloud9/latest/APIReference/Welcome.html
