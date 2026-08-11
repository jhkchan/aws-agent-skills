# Connection Modes and IAM — Cloud9 Environment Deployer

Deep reference on Cloud9 connection modes (SSM no-ingress vs SSH with
key pair), IAM instance profile requirements, managed temporary
credentials, and security best practices. Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## SSM connection mode (CONNECT_SSM)

### How SSM connection works

SSM connection mode uses the AWS Systems Manager (SSM) agent on the
EC2 instance to establish a secure channel via the AWS backbone. The
IDE in the browser connects to the EC2 instance through this channel
— no inbound security group rule, no public SSH key, no bastion host.

```text
User browser → AWS Cloud9 service → SSM Gateway → EC2 instance (SSM agent)
                                              ↑
                                    No port 22 needed
                                    No key pair needed
                                    No inbound rules
```

### Requirements for SSM connection

1. **SSM agent on the instance.** Amazon Linux 2 and Ubuntu Cloud9
   AMIs ship with the SSM agent pre-installed. No manual installation
   needed.

2. **Instance profile with `AmazonSSMManagedInstanceCore`.** The IAM
   role attached to the EC2 instance MUST include the
   `AmazonSSMManagedInstanceCore` managed policy. Without it, the SSM
   agent cannot register with the SSM service.

```bash
# Verify the role has SSM permissions
aws iam list-attached-role-policies \
  --role-name Cloud9InstanceProfile \
  --query 'AttachedPolicies[*].PolicyName' --output table

# Attach if missing
aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

3. **Outbound connectivity to SSM endpoints.** The EC2 instance must
   reach the SSM service endpoints. Options:
   - Public subnet with internet gateway (simplest)
   - Private subnet with NAT gateway
   - Private subnet with VPC endpoints for SSM (most secure — no IGW
     or NAT needed)

### VPC endpoints for fully private SSM connectivity

For environments with no internet gateway and no NAT gateway, use VPC
endpoints for SSM:

```bash
# Create VPC endpoints for SSM (interface endpoints)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.ssm \
  --vpc-endpoint-type Interface \
  --subnet-id subnet-aaa11122 \
  --security-group-id sg-ssm-endpoint

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.ssmmessages \
  --vpc-endpoint-type Interface \
  --subnet-id subnet-aaa11122 \
  --security-group-id sg-ssm-endpoint

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.ec2messages \
  --vpc-endpoint-type Interface \
  --subnet-id subnet-aaa11122 \
  --security-group-id sg-ssm-endpoint
```

This enables fully private Cloud9 environments with no internet
exposure.

## SSH connection mode (CONNECT_SSH)

### How SSH connection works

SSH connection mode uses a traditional SSH tunnel on port 22. The
browser-based IDE connects via SSH to the EC2 instance.

```text
User browser → AWS Cloud9 service → EC2 instance (port 22)
                                    ↑
                          Requires key pair
                          Requires port 22 ingress
                          Requires public subnet (or bastion)
```

### Requirements for SSH connection

1. **Key pair.** An EC2 key pair must exist and be specified at
   environment creation.

```bash
# Verify key pair exists
aws ec2 describe-key-pairs --key-names my-cloud9-key
```

2. **Security group with port 22 ingress.** The security group MUST
   allow inbound TCP port 22 from a trusted CIDR.

```bash
# Create security group with port 22 from corporate network
aws ec2 create-security-group \
  --group-name cloud9-ssh \
  --description "Cloud9 SSH access" \
  --vpc-id vpc-aaa11122

aws ec2 authorize-security-group-ingress \
  --group-name cloud9-ssh \
  --protocol tcp \
  --port 22 \
  --cidr 10.0.0.0/8  # corporate network only
```

3. **Public subnet.** The EC2 instance must be in a public subnet
   with an internet gateway route (or reachable via a bastion host).

### When to use SSH mode

- External SSH client access (e.g., VS Code Remote SSH, terminal SSH).
- Legacy environments that require traditional SSH connectivity.
- Compliance requirements that mandate SSH key auditing.

### When NOT to use SSH mode

- Most modern use cases — SSM mode is more secure and simpler.
- Private subnet deployments without bastion hosts.
- Environments where key pair management is a burden.

## IAM instance profile

### Creating the instance profile for Cloud9

```bash
# Create the IAM role with EC2 trust policy
aws iam create-role \
  --role-name Cloud9InstanceProfile \
  --assume-role-policy-document '{
    "Version":"2012-10-17",
    "Statement":[
      {"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}
    ]
  }'

# Attach SSM permissions (REQUIRED for SSM connection mode)
aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Attach additional permissions for the development workflow
aws iam attach-role-policy \
  --role-name Cloud9InstanceProfile \
  --policy-arn arn:aws:iam::aws:policy/AWSCodeCommitReadOnly

# Create and populate the instance profile
aws iam create-instance-profile \
  --instance-profile-name Cloud9InstanceProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name Cloud9InstanceProfile \
  --role-name Cloud9InstanceProfile
```

### Managed temporary credentials

When a user opens a Cloud9 environment, Cloud9 issues **managed
temporary credentials** scoped to that user's IAM permissions. These
credentials are automatically rotated and used for AWS CLI/SDK calls
within the IDE.

```text
Credential flow:
  User IAM identity → Cloud9 service → managed temporary credentials
  → injected into the EC2 instance environment
  → used by AWS CLI/SDK in the IDE

  The instance profile is the FALLBACK for operations not covered
  by managed temporary credentials (e.g., system-level services).
```

**Key implication:** sharing a Cloud9 environment does NOT share AWS
credentials. Each user's permissions are independent, governed by
their IAM identity.

### Disabling managed temporary credentials

In some cases (e.g., using the instance profile role exclusively),
managed temporary credentials can be disabled:

```bash
# Inside the Cloud9 IDE, disable managed credentials
# Cloud9 → Preferences → AWS Settings → Credentials → Disable
```

This makes the instance profile the sole source of AWS permissions.
Use this when you want all users to share the same permissions
(defined by the instance profile role).

## Security best practices

1. **Use SSM connection mode.** No exposed ports, no key pair
   management.

2. **Restrict SSH CIDR.** If SSH mode is required, never use
   `0.0.0.0/0`. Restrict to the corporate network CIDR.

3. **Least-privilege instance profile.** Only attach the policies
   the IDE needs (SSM, CodeCommit, S3 read). Avoid
   `AdministratorAccess`.

4. **Use VPC endpoints for private environments.** Eliminate
   internet exposure with SSM VPC endpoints.

5. **Monitor with CloudTrail.** Cloud9 API calls (create, delete,
   share) are logged in CloudTrail. Monitor for unauthorized changes.

## Terraform example

```hcl
# IAM role for Cloud9
resource "aws_iam_role" "cloud9" {
  name = "Cloud9InstanceProfile"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# SSM permissions (required for SSM connection)
resource "aws_iam_role_policy_attachment" "cloud9_ssm" {
  role       = aws_iam_role.cloud9.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance profile
resource "aws_iam_instance_profile" "cloud9" {
  name = "Cloud9InstanceProfile"
  role = aws_iam_role.cloud9.name
}

# Cloud9 environment (SSM mode)
resource "aws_cloud9_environment_ec2" "dev" {
  name                        = "dev-team-ide"
  instance_type               = "t3.medium"
  image_id                    = "amazonlinux-2-x86_64"
  connection_type             = "CONNECT_SSM"
  subnet_id                   = aws_subnet.private.id
  automatic_stop_time_minutes = 30

  tags = {
    Environment = "production"
    Team        = "dev"
  }
}
```
