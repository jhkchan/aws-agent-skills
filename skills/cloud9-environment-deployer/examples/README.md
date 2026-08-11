# End-to-End Example: Cloud9 Environment Deployment

A walkthrough showing how to use the `cloud9-environment-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Cloud9 environment with SSM connection (no
ingress), Amazon Linux 2, auto-hibernation, and team sharing. The
environment needs:

- Name: dev-team-ide
- Instance type: t3.medium
- Platform: Amazon Linux 2
- Connection mode: SSM (CONNECT_SSM, no ingress)
- Subnet: subnet-aaa11122
- Instance profile: Cloud9InstanceProfile (with AmazonSSMManagedInstanceCore)
- Auto-hibernation: 30 minutes
- Sharing: 2 read-write members (teammate1, teammate2)
- Git integration: CodeCommit

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cloud9-environment
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Cloud9 environment named dev-team-ide. t3.medium,
      Amazon Linux 2, SSM connection mode. Subnet subnet-aaa11122.
      Instance profile Cloud9InstanceProfile. Auto-hibernate 30
      minutes. Share with teammate1 and teammate2 read-write."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a cloud9 environment"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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
  [✓] Tags: Environment=production, Team=dev
VERIFICATION_COMMANDS:
  aws cloud9 describe-environments --environment-ids abc12345-6789-def0 --region us-east-1
  aws ec2 describe-instances --filters Name=tag:aws:cloud9:environment,Values=abc12345-6789-def0 --region us-east-1
  aws cloud9 describe-environment-memberships --environment-id abc12345-6789-def0 --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the IAM role (if not existing)
aws iam create-role \
  --role-name Cloud9InstanceProfile \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]
  }'

aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

aws iam create-instance-profile --instance-profile-name Cloud9InstanceProfile
aws iam add-role-to-instance-profile \
  --instance-profile-name Cloud9InstanceProfile \
  --role-name Cloud9InstanceProfile

# Step 2: Create the Cloud9 environment (SSM mode, auto-hibernate)
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

# Step 3: Share with team members
aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate1 \
  --permissions read-write

aws cloud9 create-environment-membership \
  --environment-id "$ENV_ID" \
  --user-arn arn:aws:iam::123456789012:user/teammate2 \
  --permissions read-write

# Step 4: Configure CodeCommit Git credentials (inside the IDE)
# Cloud9 → Preferences → AWS Settings → Credentials → Managed
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the environment
aws cloud9 describe-environments \
  --environment-ids "$ENV_ID" \
  --region us-east-1

# Verify the backing EC2 instance
aws ec2 describe-instances \
  --filters "Name=tag:aws:cloud9:environment,Values=$ENV_ID" \
  --query 'Reservations[0].Instances[0].{State:State.Name,Type:InstanceType,Subnet:SubnetId}' \
  --region us-east-1

# Verify sharing
aws cloud9 describe-environment-memberships \
  --environment-id "$ENV_ID" \
  --region us-east-1

# Verify the instance profile has SSM permissions
aws iam list-attached-role-policies \
  --role-name Cloud9InstanceProfile \
  --query 'AttachedPolicies[*].PolicyName' --output table
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Connection mode | Defaults to SSH (port 22) | SSM (no ingress) | SSM eliminates exposed ports and key pair management |
| Instance profile | Missing AmazonSSMManagedInstanceCore | Verified SSM permissions included | SSM connection silently fails without SSM policy |
| Auto-hibernation | Not set (0 = never stop) | 30-minute timeout | Without hibernation, EC2 runs 24/7 (~$30/month wasted) |
| Security group | Port 22 open to 0.0.0.0/0 | No inbound rules (SSM mode) | SSM needs no inbound; SSH should restrict CIDR |
| Sharing | Not configured | Explicit membership management | Sharing grants IDE access with per-user credentials |
| Subnet placement | Private subnet without SSM endpoints | SSM mode with verified connectivity | Private subnets need SSM VPC endpoints or NAT for SSM |

---

## Related artifacts

- **Skill definition:** `skills/cloud9-environment-deployer/SKILL.md`
- **Connection modes and IAM guide:** `skills/cloud9-environment-deployer/references/connection-modes-and-iam.md`
- **Sharing and cost optimization guide:** `skills/cloud9-environment-deployer/references/sharing-and-cost-optimization.md`
- **Slash command:** `commands/aws/deploy-cloud9-environment.md`
- **Eval suite:** `skills/cloud9-environment-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cloud9-environment-deployer/eval/test-cases.yaml`
