# Endpoints and Networking — S3 Outposts Deployer

Deep reference on S3 Outposts endpoint creation, VPC and subnet
requirements, security group configuration, and the networking bridge
between VPC and Outpost S3. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays scannable.

## S3 Outposts endpoint architecture

### Why the endpoint is mandatory

S3 on Outposts has NO public API endpoint. All S3 API traffic to an
Outpost bucket must go through a VPC endpoint created on the Outpost.
This endpoint creates a networking bridge between the VPC and the
Outpost's S3 service.

```text
Cloud S3 access:
  Client → public S3 API (s3.amazonaws.com) → AWS cloud → bucket
  Client → VPC gateway endpoint → AWS cloud → bucket

S3 Outposts access:
  Client → VPC endpoint (on Outpost subnet) → Outpost S3 → bucket
              ↑ MANDATORY — no public endpoint exists
```

### Endpoint creation

```bash
aws s3outposts create-endpoint \
  --outpost-id op-0abc123def456 \
  --subnet-id subnet-abc123 \
  --security-group-id sg-abc123 \
  --query 'EndpointArn' --output text
```

**Requirements:**
- The subnet MUST be on the Outpost (Outpost subnet)
- The security group controls which clients can reach the S3 service
- The endpoint is tied to the specific Outpost

### Subnet requirements

The subnet must be an Outpost subnet — a subnet whose parent VPC is
associated with the Outpost. Regular cloud subnets cannot host an S3
Outposts endpoint.

```bash
# Find Outpost subnets
aws ec2 describe-subnets \
  --filters Name=outpost-arn,Values=arn:aws:outposts:us-east-1:123456789012:outpost/op-0abc123def456 \
  --query 'Subnets[*].{SubnetId:SubnetId,CIDR:CidrBlock}' \
  --output table
```

### Security group configuration

The endpoint's security group MUST allow inbound HTTPS (port 443) from
the clients that need to access the Outpost S3.

```bash
# Create security group for endpoint
SG_ID=$(aws ec2 create-security-group \
  --group-name "s3-outposts-endpoint-sg" \
  --description "SG for S3 Outposts endpoint" \
  --vpc-id vpc-abc123 \
  --query 'GroupId' --output text)

# Allow HTTPS from the VPC CIDR
aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/16
```

### Verifying endpoint connectivity

```bash
# Check endpoint status
aws s3outposts list-endpoints \
  --query 'Endpoints[?OutpostId==`op-0abc123def456`]'

# From an EC2 instance on the Outpost, test S3 access
aws s3 ls s3://my-outpost-bucket
# If this works, the endpoint is correctly configured
```

## Accessing Outpost S3 from cloud EC2

Cloud EC2 instances (not on the Outpost) can access Outpost S3 IF
there is network connectivity between the cloud VPC and the Outpost
network. This typically requires:

1. The Outpost's local network route back to the VPC
2. DX or VPN connectivity between cloud VPC and Outpost

However, the PRIMARY access path is from EC2 instances ON the Outpost
itself, which have direct network access to the endpoint.

## Endpoint lifecycle

| State | Meaning |
|---|---|
| Creating | Endpoint is being provisioned |
| Available | Endpoint is active and serving traffic |
| Deleting | Endpoint is being removed |

An endpoint in `Creating` state cannot serve traffic. Wait for
`Available` before testing bucket access.

## Common networking pitfalls

### Pitfall 1: Subnet not on Outpost

```text
ERROR: The subnet subnet-xyz is not associated with the Outpost.
FIX: Use describe-subnets with the outpost-arn filter to find
     Outpost subnets.
```

### Pitfall 2: Security group blocks HTTPS

The endpoint SG must allow port 443 from the client CIDR. If the SG
only allows SSH (22), S3 API calls fail.

### Pitfall 3: Wrong VPC

The endpoint must be in the same VPC as the Outpost subnet. Creating
an endpoint in a different VPC fails.

### Pitfall 4: DNS resolution

Outpost S3 uses a different DNS namespace than cloud S3. The endpoint
provides DNS resolution for Outpost S3 hostnames. Ensure DNS settings
in the VPC allow resolution of the Outpost S3 endpoint hostname.

## Terraform examples

```hcl
# S3 Outposts endpoint
resource "aws_s3outposts_endpoint" "main" {
  outpost_id         = "op-0abc123def456"
  subnet_id          = aws_subnet.outpost_subnet.id
  security_group_id  = aws_security_group.endpoint.id
}

# Security group for the endpoint
resource "aws_security_group" "endpoint" {
  name        = "s3-outposts-endpoint-sg"
  description = "SG for S3 Outposts endpoint"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }
}
```

## Step 2: endpoint creation and verification (moved from SKILL.md)

**Create the endpoint:**

```bash
ENDPOINT_ID=$(aws s3outposts create-endpoint \
  --outpost-id op-0abc123def456 \
  --subnet-id subnet-abc123def \
  --security-group-id sg-abc123def \
  --query 'EndpointArn' --output text)

echo "Endpoint ARN: $ENDPOINT_ID"
```

**Verify the endpoint:**

```bash
aws s3outposts list-endpoints \
  --query 'Endpoints[?EndpointArn==`'"$ENDPOINT_ID"'`]'
```

The endpoint must be in the `Available` state before bucket access
works. The endpoint is tied to a specific subnet and security group
on the Outpost.

**Security group requirements:** the security group must allow inbound
HTTPS (port 443) from the clients that need to access the Outpost S3.

