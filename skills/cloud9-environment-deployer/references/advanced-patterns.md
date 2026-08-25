# Advanced Patterns — Cloud9 Environment Deployer

Load-on-demand deep dives moved verbatim from SKILL.md.

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
