# VPC and Networking — MWAA Environment Deployer

Deep reference on VPC subnet requirements for MWAA (2 private subnets
in different AZs, security group rules, S3 access path via NAT Gateway
or VPC endpoint), webserver access modes (PUBLIC_ONLY vs PRIVATE_ONLY),
DNS resolution requirements, and common networking pitfalls. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## VPC topology for MWAA

MWAA requires a specific VPC topology:

```text
Required VPC topology:
  VPC (enableDnsSupport=true, enableDnsHostnames=true)
  ├── Private subnet A (us-east-1a)
  │     Route table:
  │       10.0.0.0/16 → local
  │       0.0.0.0/0 → nat-gw-xxx (NAT Gateway in public subnet)
  │     (or: S3 prefix list → vpce-xxx for S3 VPC endpoint)
  │     → MWAA workers, scheduler, webserver
  │
  ├── Private subnet B (us-east-1b)
  │     Route table:
  │       10.0.0.0/16 → local
  │       0.0.0.0/0 → nat-gw-xxx
  │     → MWAA workers (HA across AZs)
  │
  ├── Public subnet A (us-east-1a) [if using NAT Gateway]
  │     Route table:
  │       10.0.0.0/16 → local
  │       0.0.0.0/0 → igw-xxx (Internet Gateway)
  │     → NAT Gateway
  │
  └── Security Group (sg-mwaa)
        Inbound:
          TCP 443 from self (webserver)
          TCP 5432 from self (metadata DB inter-component)
          TCP 3306 from self (Celery broker)
          ALL from self (inter-component communication)
        Outbound:
          TCP 443 to 0.0.0.0/0 (S3, CloudWatch, MWAA APIs)
```

### Why 2 subnets in different AZs?

MWAA distributes its workers across AZs for high availability. If one
AZ fails, workers in the other AZ continue processing tasks. With only
1 subnet (or 2 in the same AZ), the create-environment API call fails
with:

```text
ResourceNotFoundException: The specified subnets must be in at least
two different Availability Zones.
```

### Verifying subnet configuration

```bash
# Check that the 2 subnets are in different AZs
aws ec2 describe-subnets \
  --subnet-ids subnet-aaa subnet-bbb \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock}' \
  --region us-east-1 --output table

# Verify VPC DNS settings
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 --attribute enableDnsSupport
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 --attribute enableDnsHostnames

# Enable if needed
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-support
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-hostnames
```

## S3 access path

MWAA workers need to pull DAGs, requirements.txt, and plugins from S3.
Two options:

### Option A: NAT Gateway

The private subnets route 0.0.0.0/0 through a NAT Gateway in the
public subnet. This allows workers to reach S3 (and the internet).

```bash
# Verify NAT Gateway exists in the VPC
aws ec2 describe-nat-gateways \
  --filter Name=vpc-id,Values=vpc-aaa11122 \
  --query 'NatGateways[*].{NatGatewayId:NatGatewayId,State:State}' \
  --region us-east-1

# Verify route table in private subnet routes to NAT Gateway
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=subnet-aaa \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`]' \
  --region us-east-1
```

### Option B: S3 VPC endpoint (Gateway type)

An S3 VPC endpoint provides S3 access without a NAT Gateway. This is
cheaper (no hourly NAT Gateway charge) and more secure (no internet
egress).

```bash
# Create S3 VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-aaa11122 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-private-a rtb-private-b \
  --region us-east-1

# Verify S3 VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=vpc-aaa11122 Name=service-name,Values=com.amazonaws.us-east-1.s3 \
  --region us-east-1
```

**Without either option, MWAA workers cannot pull DAGs.** The
environment starts but DAGs never execute. This is a silent failure —
check DagProcessingLogs for "S3 connection timeout" or similar errors.

## Security group rules

### Minimum required rules

```text
Security Group: sg-mwaa

Inbound rules:
  TCP 443  Source: sg-mwaa (self)
    → webserver communication
  TCP 5432 Source: sg-mwaa (self)
    → metadata database inter-component
  TCP 3306 Source: sg-mwaa (self)
    → Celery broker inter-component
  ALL      Source: sg-mwaa (self)
    → general inter-component communication

Outbound rules:
  TCP 443  Destination: 0.0.0.0/0
    → S3, CloudWatch, MWAA APIs
  TCP 5432 Destination: 0.0.0.0/0 (if using external RDS)
```

The simplest approach is to allow ALL inbound from self (same security
group). MWAA components (scheduler, workers, webserver) communicate
internally using various ports.

```bash
# Create security group
SG_ID=$(aws ec2 create-security-group \
  --group-name mwaa-sg \
  --description "Security group for MWAA environment" \
  --vpc-id vpc-aaa11122 \
  --query 'GroupId' --output text)

# Allow all inbound from self
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol all \
  --source-security-group-id "$SG_ID"

# Allow outbound 443
aws ec2 authorize-security-group-egress \
  --group-id "$SG_ID" \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=0.0.0.0/0}]"
```

## Webserver access modes

### PUBLIC_ONLY

The webserver URL is publicly reachable over the internet. Access is
controlled by AWS IAM — the caller must have `airflow:CreateWebLoginToken`
permission.

```bash
aws mwaa create-environment \
  --webserver-access-mode PUBLIC_ONLY \
  ...
```

- Simplest setup. No VPN/DX needed.
- Webserver URL: `https://<unique-id>.<region>.airflow.amazonaws.com`
- Suitable for: dev/test, internal team tools, non-compliance-sensitive.

### PRIVATE_ONLY

The webserver URL resolves to a private IP within the VPC. Requires VPN,
Direct Connect, or a bastion host to access.

```bash
aws mwaa create-environment \
  --webserver-access-mode PRIVATE_ONLY \
  ...
```

- No public endpoint. Webserver is only reachable from within the VPC.
- Required for: HIPAA, FedRAMP, compliance-sensitive environments.
- The security group must allow inbound 443 from the VPN/DX subnet or
  bastion host security group.

## Common networking pitfalls

1. **Only 1 subnet provided.** MWAA requires 2 in different AZs. The
   create-environment call fails immediately.

2. **No S3 access path.** Without NAT Gateway or S3 VPC endpoint,
   workers cannot pull DAGs. Silent failure — check DagProcessingLogs.

3. **DNS resolution disabled.** MWAA needs `enableDnsSupport` and
   `enableDnsHostnames` on the VPC. Without DNS, internal service
   resolution fails.

4. **Security group too restrictive.** MWAA components communicate on
   multiple ports. If the security group only allows 443, inter-component
   communication breaks. Use "ALL from self" as the simplest rule.

5. **S3 bucket in different region.** MWAA reads DAGs from S3 in-region.
   Cross-region S3 access causes latency and intermittent failures.

## Terraform VPC example

```hcl
# VPC with 2 private subnets and S3 VPC endpoint for MWAA

resource "aws_vpc" "mwaa_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.mwaa_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.mwaa_vpc.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"
}

resource "aws_security_group" "mwaa" {
  vpc_id = aws_vpc.mwaa_vpc.id

  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# S3 VPC endpoint
resource "aws_vpc_endpoint" "s3" {
  vpc_id          = aws_vpc.mwaa_vpc.id
  service_name    = "com.amazonaws.us-east-1.s3"
  route_table_ids = [aws_route_table.private.id]
}
```
## Expert heuristic: VPC subnet requirements (2 private + security group)

A baseline model says "select any 2 subnets." The correct heuristic
verifies that the subnets are private, in different AZs, and have S3
access.

```text
VPC readiness check for MWAA:
  ├── 2 private subnets in DIFFERENT AZs?
  │     ├── YES → proceed
  │     └── NO (1 subnet, or 2 in same AZ) → BLOCK (PREREQUISITES_MISSING)
  │
  ├── Route to S3 (for DAG access)?
  │     ├── NAT Gateway in public subnet → route table has 0.0.0.0/0 → nat-gw
  │     ├── S3 VPC endpoint (Gateway type) → route table has S3 prefix list
  │     └── NEITHER → BLOCK (workers cannot pull DAGs)
  │
  ├── Security group with correct rules?
  │     ├── Inbound 443 (webserver — for PRIVATE_ONLY access from within VPC)
  │     ├── Inbound 5432 (metadata DB — managed by AWS, SG-internal)
  │     ├── Outbound 443 (S3, CloudWatch, MWAA APIs)
  │     └── All from self (inter-component communication)
  │
  └── VPC has DNS resolution + DNS hostnames enabled?
        ├── YES → proceed (MWAA needs DNS for internal resolution)
        └── NO → BLOCK (enableDnsSupport + enableDnsHostnames)
```

**Key implication:** the 2-subnet-different-AZ requirement is non-
negotiable. MWAA distributes workers across AZs for HA. If only 1 AZ is
available, the environment cannot be created.

## Step 2 — VPC verification commands (subnets/AZ, S3 endpoint, NAT)

```text
Required VPC topology:
  VPC
  ├── 2 private subnets (different AZs)
  │     subnet-private-a (us-east-1a) → MWAA workers, scheduler
  │     subnet-private-b (us-east-1b) → MWAA workers (HA)
  ├── 1 public subnet (for NAT Gateway)
  │     subnet-public-a → NAT Gateway → 0.0.0.0/0 route
  ├── S3 VPC endpoint (Gateway type) OR NAT Gateway route
  │     Without this, workers cannot pull DAGs from S3
  └── Security group
        Inbound: 443 (self), 5432 (self)
        Outbound: 443 (S3, CloudWatch, MWAA APIs)
```

**Verify subnet AZs:**

```bash
aws ec2 describe-subnets \
  --subnet-ids subnet-aaa subnet-bbb \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone,Type:MapPublicIpOnLaunch}' \
  --region us-east-1
# Ensure the two subnets are in different AZs and are private
```

**Verify S3 access (NAT Gateway or VPC endpoint):**

```bash
# Check for S3 VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=vpc-aaa11122 Name=service-name,Values=com.amazonaws.us-east-1.s3 \
  --region us-east-1

# Or check for NAT Gateway
aws ec2 describe-nat-gateways \
  --filter Name=vpc-id,Values=vpc-aaa11122 \
  --region us-east-1
```

