# Endpoint Policy and Security Groups — VPC Endpoint Policy Troubleshooter

Deep reference on endpoint policy evaluation (separate IAM layer,
default vs custom, dual-layer evaluation order), security group
configuration for interface endpoint ENIs (inbound from client subnet
on service port), and endpoint policy JSON validation. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
diagnostic procedure stays scannable.

## Endpoint policy fundamentals

### The dual-layer evaluation model

The endpoint policy is a SEPARATE IAM layer from the caller's IAM
policy. Both are evaluated independently. Both must allow the action
for the request to succeed.

```text
Request evaluation order:

  Step 1 — IAM policy (caller identity)
    Does the caller's IAM policy (attached to user/role) allow the action?
    ├── NO → IAM denies (403, before the endpoint is involved)
    └── YES → continue to Step 2

  Step 2 — Endpoint policy (attached to VPC endpoint)
    Does the endpoint policy allow the action for this principal?
    ├── NO → Endpoint policy denies (403, from the endpoint)
    └── YES → request reaches the AWS service

  BOTH must allow. Either can deny.
```

This dual-layer model is the #1 cause of endpoint "access denied"
mysteries. The caller's IAM policy is checked first, but even if IAM
allows, the endpoint policy can still deny. Operators who do not know
about the endpoint policy layer spend hours checking IAM and bucket
policies without finding the issue.

### Default endpoint policy (full access)

If no custom policy is specified at endpoint creation, the default
policy allows full access:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

With the default policy, the endpoint policy is NOT the blocker. Any
access denied error would come from the caller's IAM policy.

### Custom endpoint policy examples

**Restrict to specific actions:**

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
```

**Restrict to specific buckets:**

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::allowed-bucket-1/*",
        "arn:aws:s3:::allowed-bucket-2/*"
      ]
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::restricted-bucket/*"
    }
  ]
}
```

### Retrieve and inspect the endpoint policy

```bash
# Get the endpoint policy (URL-encoded JSON)
POLICY=$(aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PolicyDocument' \
  --output text --region us-east-1)

# Decode and pretty-print
echo "$POLICY" | python3 -c "
import sys, json, urllib.parse
policy = json.loads(urllib.parse.unquote(sys.stdin.read()))
print(json.dumps(policy, indent=2))
"

# Check if the policy is empty (default)
if [ -z "$POLICY" ] || [ "$POLICY" == "null" ]; then
  echo "Default policy (full access) — endpoint policy is NOT the blocker"
fi
```

### Modify the endpoint policy

```bash
# Apply a new policy from a JSON file
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --policy-document file://new-policy.json \
  --region us-east-1

# Reset to default (full access)
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --no-policy-document \
  --region us-east-1
```

## Endpoint policy JSON validation

Common JSON syntax errors that cause policy update failures:

```bash
# Validate JSON before applying
python3 -m json.tool new-policy.json

# Common errors:
# 1. Trailing comma
#    {"Action": ["s3:GetObject",]}  ← remove the comma after the last element
#
# 2. Missing closing bracket
#    {"Statement": [{"Effect": "Allow"}  ← missing ] and }
#
# 3. Invalid principal format
#    {"Principal": {"AWS": "123456789012"}}  ← must be ARN: arn:aws:iam::123456789012:root
#    {"Principal": "*"}  ← valid (all principals)
#
# 4. Unquoted value
#    {"Effect": Allow}  ← must be {"Effect": "Allow"}
#
# 5. Missing Statement wrapper
#    {"Effect": "Allow", ...}  ← must be {"Statement": [{"Effect": "Allow", ...}]}
```

## Security group configuration for interface endpoints

### Why the endpoint's SG matters

An interface endpoint creates ENIs (elastic network interfaces) in the
specified subnets. Each ENI has a private IP address and a security
group. The client sends traffic to the ENI's private IP on the service
port (typically TCP 443 for most AWS PrivateLink services).

If the endpoint's security group does NOT allow inbound traffic from
the client subnet on the service port, the connection times out (SYN
dropped, no response). This is the #1 cause of interface endpoint
connection timeouts.

```text
Traffic flow:
  Client (10.0.2.5) → sends TCP SYN to ENI IP (10.0.1.10) port 443
    → ENI's security group sg-vpce123 evaluates inbound rules
    ├── Rule allows 10.0.2.0/24 on 443 → SYN-ACK returned → connection works
    └── No matching rule → SYN dropped → connection TIMEOUT
```

### Retrieve the endpoint's security group

```bash
# Get endpoint ENI IDs
ENI_IDS=$(aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].NetworkInterfaceIds' \
  --output text --region us-east-1)

# Get SG IDs from the ENIs
for ENI in $ENI_IDS; do
  echo "=== ENI: $ENI ==="
  aws ec2 describe-network-interfaces \
    --network-interface-ids "$ENI" \
    --query 'NetworkInterfaces[0].{PrivateIp:PrivateIpAddress,SGs:Groups[*].GroupId}' \
    --output table --region us-east-1
done

# Get inbound rules for the endpoint's SG
SG_ID=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_IDS \
  --query 'NetworkInterfaces[0].Groups[0].GroupId' \
  --output text --region us-east-1)

aws ec2 describe-security-groups \
  --group-ids "$SG_ID" \
  --query 'SecurityGroups[0].IpPermissions[*].{Protocol:IpProtocol,From:FromPort,To:ToPort,Sources:IpRanges[*].CidrIp}' \
  --output table --region us-east-1
```

### Add an inbound rule for the client subnet

```bash
# Allow inbound from client subnet on the service port (443 for most services)
aws ec2 authorize-security-group-ingress \
  --group-id sg-vpce123 \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.2.0/24 \
  --region us-east-1
```

### Common service ports

| Service | Port | Notes |
|---|---|---|
| Most AWS services (SSM, EC2, STS, Secrets Manager, etc.) | 443 | Standard HTTPS |
| API Gateway private endpoints | 443 | |
| Custom PrivateLink services | Varies | Check the NLB listener port |
| Kinesis Streams | 443 | |

For custom PrivateLink services, the service port is determined by the
NLB listener configuration in the provider account. Check the NLB
listener to confirm the port.

## Cross-account endpoint access policies

For cross-account PrivateLink, the service provider's endpoint service
resource policy must allow the consumer account. This is a THIRD
policy layer (in addition to the consumer's IAM policy and the
consumer's endpoint policy).

```text
Cross-account access control (three layers):
  1. Consumer IAM policy (caller identity in consumer account)
  2. Consumer endpoint policy (attached to consumer's VPC endpoint)
  3. Provider endpoint service resource policy (attached to the endpoint service)

  ALL THREE must allow the action for cross-account access to work.
```

**Provider: check and add allowed principals:**

```bash
# Check who is allowed
aws ec2 describe-vpc-endpoint-service-permissions \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --query 'AllowedPrincipals[*].Principal' \
  --output table --region us-east-1

# Add the consumer account
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --add-allowed-principals arn:aws:iam::123456789012:root \
  --region us-east-1
```

## Terraform examples

```hcl
# Interface endpoint with security group and custom policy
resource "aws_security_group" "endpoint_sg" {
  name        = "vpce-endpoint-sg"
  description = "Allow inbound from client subnets on 443"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.1.0/24", "10.0.2.0/24"]
  }
}

resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.us-east-1.ssm"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.endpoint_sg.id]
  subnet_ids          = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  policy = jsonencode({
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource  = "*"
      }
    ]
  })
}

# Gateway endpoint with route table association
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.us-east-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_1.id, aws_route_table.private_2.id]

  policy = jsonencode({
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:PutObject"]
        Resource  = ["arn:aws:s3:::my-bucket/*"]
      }
    ]
  })
}
```
