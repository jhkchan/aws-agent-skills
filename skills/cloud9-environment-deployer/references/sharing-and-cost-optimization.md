# Sharing and Cost Optimization — Cloud9 Environment Deployer

Deep reference on environment sharing (read/write permissions, per-
user credentials, membership management), auto-hibernation (idle
timeout configuration, cost impact, modification constraints), EC2
lifecycle management (start/stop/delete), and cost optimization
strategies. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Environment sharing

### Sharing model

When you share a Cloud9 environment, each member connects using their
OWN AWS credentials. The instance profile is NOT shared. Each user's
permissions are governed by their IAM identity through managed
temporary credentials.

```text
Environment owner creates the environment → shares with members
  → Each member opens the environment from their Cloud9 console
  → Cloud9 issues managed temporary credentials scoped to the member's IAM identity
  → Member can edit code (write) or view code (read)
  → No credential sharing, no permission leakage
```

### Permission levels

| Permission | What the member can do |
|---|---|
| `read-only` | View files, view terminal output. Cannot edit or run commands. |
| `read-write` | Edit files, run terminal commands, install packages. Full IDE access. |

### Sharing via AWS CLI

```bash
# Grant read-write access to a user
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate1 \
  --permissions read-write

# Grant read-only access to a reviewer
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/reviewer1 \
  --permissions read-only

# List all members
aws cloud9 describe-environment-memberships \
  --environment-id "$ENV_ID"

# Remove a member
aws cloud9 delete-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate1
```

### Sharing via IAM group

For team-based sharing, create an IAM group and share with the group
ARN:

```bash
# Share with an IAM group
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:group/DevTeam \
  --permissions read-write
```

All users in the `DevTeam` group get access.

### Concurrent editing

Multiple members with read-write access can edit the same environment
simultaneously. Cloud9 does NOT provide merge conflict resolution —
changes are saved to the same filesystem. Coordinate with team members
to avoid overwriting each other's changes.

**Best practice:** use Git within the IDE for collaborative editing.
Commit changes frequently and pull before editing to avoid conflicts.

## Auto-hibernation

### How auto-hibernation works

Auto-hibernation stops the EC2 instance after N minutes of IDE
inactivity. The EBS volume is preserved. When a user opens the IDE
again, the instance restarts automatically (takes 1-3 minutes).

```text
IDE inactivity timer:
  ├── User closes the browser tab → timer starts
  ├── No terminal activity, no file saves → timer counts
  ├── Timer reaches threshold → EC2 instance STOPPED
  ├── User opens IDE → instance STARTS automatically
  └── User resumes work (data intact on EBS)
```

### Setting auto-hibernation

```bash
# Set at creation time (REQUIRED — cannot be changed post-creation)
aws cloud9 create-environment-ec2 \
  --name "dev-ide" \
  --automatic-stop-time-minutes 30 \
  ...
```

### Cost impact of auto-hibernation

```text
Instance: t3.medium ($0.0416/hour, us-east-1)

No hibernation (always running):
  730 hours/month × $0.0416 = $30.37/month

30-min hibernation (assume 4 hrs/day active, 22 workdays):
  88 hours/month × $0.0416 = $3.66/month
  Savings: 88%

15-min hibernation (assume 2 hrs/day active, 22 workdays):
  44 hours/month × $0.0416 = $1.83/month
  Savings: 94%

60-min hibernation (assume 6 hrs/day active, 22 workdays):
  132 hours/month × $0.0416 = $5.49/month
  Savings: 82%
```

**Note:** even with hibernation, EBS storage costs continue (~$0.10/
GB/month for gp2). A 30 GB EBS volume costs ~$3/month regardless of
instance state.

### Recommended hibernation timeouts

| Scenario | Timeout | Rationale |
|---|---|---|
| Individual developer | 15-30 minutes | Frequent breaks, aggressive savings |
| Small team (2-3 people) | 30-60 minutes | Multiple timezones, staggered activity |
| Workshop/training | 240 minutes | Long sessions with breaks |
| Long-running builds | 240 minutes | Avoid stopping during CI/CD |
| Never set to 0 | — | 0 means never stop (highest cost) |

### Modifying auto-hibernation

Auto-hibernation is set at creation and CANNOT be modified post-
creation without recreating the environment. To change the timeout:

```bash
# Option 1: Delete and recreate (loses in-place data unless EBS snapshot taken)
aws cloud9 delete-environment --environment-id "$OLD_ENV_ID"

aws cloud9 create-environment-ec2 \
  --name "dev-ide" \
  --automatic-stop-time-minutes 60 \
  ...

# Option 2: Stop the EC2 instance manually outside of hibernation hours
aws ec2 stop-instances --instance-ids i-aaa11122
# Restart when needed
aws ec2 start-instances --instance-ids i-aaa11122
```

## EC2 lifecycle management

### Start (from hibernated/stopped)

```bash
# Find the EC2 instance backing the Cloud9 environment
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:aws:cloud9:environment,Values=$ENV_ID" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text)

# Start the instance
aws ec2 start-instances --instance-ids "$INSTANCE_ID"
```

### Stop (manual)

```bash
aws ec2 stop-instances --instance-ids "$INSTANCE_ID"
```

### Delete the environment (terminates EC2)

```bash
aws cloud9 delete-environment --environment-id "$ENV_ID"
```

**Critical:** deleting the environment terminates the EC2 instance
AND deletes the EBS volume. All data is lost. Take a snapshot first
if data needs to be preserved.

```bash
# Take an EBS snapshot before deletion
aws ec2 create-snapshot \
  --volume-id "$VOLUME_ID" \
  --description "Cloud9 backup before deletion"
```

## Cost optimization strategies

### Strategy 1: Right-size the instance

Use the smallest instance type that supports the workload:

| Workload | Instance type | Monthly cost (no hibernate) |
|---|---|---|
| Light editing, scripting | t3.micro (1 GB) | ~$7.60 |
| Standard development | t3.medium (4 GB) | ~$30.37 |
| Heavy builds, containers | t3.large (8 GB) | ~$60.74 |
| Data processing | m5.xlarge (16 GB) | ~$121.48 |

### Strategy 2: Auto-hibernate aggressively

Set 15-minute hibernation for individual developers. This reduces
runtime by 80-94%.

### Strategy 3: Delete unused environments

Even stopped environments incur EBS costs. Delete environments that
are no longer needed. Use tags to track ownership and lifecycle:

```bash
# Tag environments with owner and lifecycle
aws cloud9 tag-resource \
  --resource-arn arn:aws:cloud9:us-east-1:123456789012:environment:$ENV_ID \
  --tags Owner=jacky,Lifecycle=temporary,Expires=2026-09-01
```

### Strategy 4: Share environments

Instead of creating one environment per developer, share a single
environment for pair programming or code reviews. This reduces the
number of EC2 instances.

### Strategy 5: Monitor with Cost Explorer

```bash
# Query Cloud9 costs via Cost Explorer (use theawsfog CLI or console)
# Filter by service: Cloud9 and EC2 (Cloud9 instances are tagged)
```

## Terraform example with sharing and hibernation

```hcl
# Cloud9 environment
resource "aws_cloud9_environment_ec2" "team_ide" {
  name                        = "team-shared-ide"
  instance_type               = "t3.medium"
  image_id                    = "amazonlinux-2-x86_64"
  connection_type             = "CONNECT_SSM"
  subnet_id                   = aws_subnet.private.id
  automatic_stop_time_minutes = 60

  tags = {
    Environment = "production"
    Team        = "dev"
  }
}

# Share with team members (read-write)
resource "aws_cloud9_environment_membership" "dev1" {
  environment_id = aws_cloud9_environment_ec2.team_ide.id
  user_arn       = "arn:aws:iam::123456789012:user/teammate1"
  permissions    = "read-write"
}

resource "aws_cloud9_environment_membership" "dev2" {
  environment_id = aws_cloud9_environment_ec2.team_ide.id
  user_arn       = "arn:aws:iam::123456789012:user/teammate2"
  permissions    = "read-write"
}

# Share with reviewer (read-only)
resource "aws_cloud9_environment_membership" "reviewer" {
  environment_id = aws_cloud9_environment_ec2.team_ide.id
  user_arn       = "arn:aws:iam::123456789012:user/reviewer1"
  permissions    = "read-only"
}
```
