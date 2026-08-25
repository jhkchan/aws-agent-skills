# Cross-Account Peering and Security Groups — VPC Peering Deployer

Deep reference on cross-account VPC peering (acceptance automation, IAM
role assumption, EventBridge auto-accept), security group cross-VPC
references (same-account+region constraint, CIDR-based alternatives),
and security best practices. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays scannable.

## Cross-account peering acceptance

### The acceptance step

In cross-account peering, the accepter account must explicitly accept
the peering connection. The requester cannot force acceptance. The
connection remains in `pending-acceptance` status until the accepter
acts.

### Option 1: Manual acceptance

The accepter operator logs into their account (console or CLI) and
accepts:

```bash
# In the accepter account (using accepter credentials)
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id pcx-111222333 \
  --region us-east-1
```

### Option 2: Automated acceptance via STS role assumption

The requester assumes a role in the accepter account that has
`ec2:AcceptVpcPeeringConnection` permission:

```bash
# Requester assumes a role in the accepter account
CREDS=$(aws sts assume-role \
  --role-arn arn:aws:iam::999999999999:role/VpcPeeringAcceptor \
  --role-session-name "peering-accept" \
  --query 'Credentials' --output json)

# Extract temporary credentials
AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')

# Accept the peering using the assumed role's credentials
AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
aws ec2 accept-vpc-peering-connection \
  --vpc-peering-connection-id pcx-111222333 \
  --region us-east-1
```

**Accepter account IAM role trust policy** (allows requester to assume):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Accepter account IAM role permissions** (allows accepting peering):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AcceptVpcPeeringConnection",
        "ec2:DescribeVpcPeeringConnections"
      ],
      "Resource": "*"
    }
  ]
}
```

### Option 3: EventBridge auto-accept (Lambda)

The accepter account can set up an EventBridge rule that triggers a
Lambda function to auto-accept incoming peering requests. This is the
most automated approach but requires Lambda and EventBridge setup in
the accepter account.

**EventBridge rule pattern** (matches peering request events):

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["EC2 VPC Peering Connection Request"],
  "detail": {
    "state": ["pending-acceptance"]
  }
}
```

**Lambda function** (accepts the peering):

```python
import boto3

ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    pcx_id = event['detail']['vpc-peering-connection-id']
    response = ec2.accept_vpc_peering_connection(
        VpcPeeringConnectionId=pcx_id
    )
    print(f"Accepted peering: {pcx_id}")
    return {'statusCode': 200}
```

**Security consideration:** auto-accept accepts ALL peering requests.
Add filtering in the Lambda function to only accept requests from
known account IDs.

## Security group cross-VPC references

### Same-account, same-region: SG cross-references allowed

When both VPCs are in the SAME account and SAME region, security group
rules can reference a security group from the peered VPC by its ID.

```bash
# Reference accepter VPC's SG by ID in a requester SG rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-requester-app \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=sg-accepter-data,PeeringStatus=active,VpcPeeringConnectionId=pcx-111222333}]" \
  --region us-east-1
```

**Advantages of SG cross-references:**
- More precise than CIDR rules (follows the SG, not the IP range).
- Automatically adapts if instances are added/removed from the
  referenced SG.
- No need to manage IP ranges.

### Cross-account or inter-region: CIDR-based rules ONLY

For cross-account or inter-region peering, SG cross-references do NOT
work. Use CIDR-based security group rules instead.

```bash
# Cross-account or inter-region: use CIDR-based rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-requester-app \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=10.1.0.0/16,Description='Accepter VPC CIDR'}]" \
  --region us-east-1
```

**Limitation of CIDR-based rules:**
- Less precise (entire CIDR, not individual SGs).
- Must be updated if the peered VPC's CIDR changes (rare but possible).
- Does not auto-adapt to instance changes.

### Reference VPC CIDR in SG rules

For a cleaner approach, reference the VPC CIDR as a prefix list or
managed prefix list:

```bash
# Create a managed prefix list for the accepter VPC CIDR
aws ec2 create-managed-prefix-list \
  --prefix-list-name "accepter-vpc-cidr" \
  --address-family IPv4 \
  --max-entries 1 \
  --entries "Cidr=10.1.0.0/16,Description=Accepter VPC" \
  --region us-east-1

# Reference the prefix list in a SG rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-requester-app \
  --ip-permissions \
    "IpProtocol=tcp,FromPort=443,ToPort=443,PrefixListIds=[{PrefixListId=pl-xxx}]" \
  --region us-east-1
```

## CIDR overlap checking

Before creating a peering connection, verify the VPC CIDRs do not
overlap. Overlapping CIDRs cause ambiguous routing.

```bash
# Compare VPC CIDRs
REQUESTER_CIDR=$(aws ec2 describe-vpcs --vpc-ids vpc-aaa11122 \
  --query 'Vpcs[0].CidrBlock' --output text --region us-east-1)
ACCEPTER_CIDR=$(aws ec2 describe-vpcs --vpc-ids vpc-bbb22233 \
  --query 'Vpcs[0].CidrBlock' --output text --region us-east-1)

echo "Requester CIDR: $REQUESTER_CIDR"
echo "Accepter CIDR: $ACCEPTER_CIDR"

# Check for overlap (10.0.0.0/16 and 10.0.1.0/24 overlap; 10.0.0.0/16 and 10.1.0.0/16 do not)
```

Also check subnet CIDRs — subnets within the VPCs must not overlap
either, even if the VPC CIDRs are different (a subnet in VPC-A could
overlap with a subnet in VPC-B if the VPC CIDRs partially overlap).

## Terraform cross-account example

```hcl
# Provider in requester account
provider "aws" {
  alias  = "requester"
  region = "us-east-1"
}

# Provider in accepter account (different credentials/profile)
provider "aws" {
  alias  = "accepter"
  region = "us-east-1"
  # Use a different profile or assume-role
}

# Requester creates the peering connection
resource "aws_vpc_peering_connection" "peer" {
  provider      = aws.requester
  vpc_id        = data.aws_vpc.requester.id
  peer_vpc_id   = data.aws_vpc.accepter.id
  peer_owner_id = var.accepter_account_id
  peer_region   = var.accepter_region  # omit for same-region

  tags = {
    Name = "cross-account-peering"
  }
}

# Accepter accepts (using accepter provider)
resource "aws_vpc_peering_connection_accepter" "accepter" {
  provider                  = aws.accepter
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
  auto_accept               = true

  tags = {
    Name = "cross-account-peering-accepter"
  }
}

# Requester route
resource "aws_route" "requester_route" {
  provider                  = aws.requester
  route_table_id            = data.aws_route_table.requester_rt.id
  destination_cidr_block    = data.aws_vpc.accepter.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

# Accepter route (using accepter provider)
resource "aws_route" "accepter_route" {
  provider                  = aws.accepter
  route_table_id            = data.aws_route_table.accepter_rt.id
  destination_cidr_block    = data.aws_vpc.requester.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.peer.id
}

# CIDR-based SG rules (cross-account cannot use SG references)
resource "aws_security_group_rule" "requester_ingress" {
  provider          = aws.requester
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [data.aws_vpc.accepter.cidr_block]
  security_group_id = data.aws_security_group.requester_sg.id
}
```

## Common cross-account pitfalls

1. **Forgetting the acceptance step.** The requester creates the
   peering but the accepter never accepts. Connection stays in
   `pending-acceptance` indefinitely. Set up auto-accept or monitor for
   pending requests.

2. **Using SG cross-references across accounts.** Cross-account
   peering does NOT support SG cross-references. Use CIDR-based rules
   or managed prefix lists.

3. **Route table on accepter side not updated.** Even with automated
   acceptance, the accepter's route tables must be updated. This often
   requires the accepter provider in Terraform or role assumption in
   CLI.

4. **Inter-region peering data transfer costs.** Inter-region peering
   incurs cross-region data transfer charges. Monitor costs and
   consider whether Transit Gateway with inter-region attachments is
   more cost-effective for high-volume cross-region traffic.

5. **Not checking CIDR overlap across accounts.** Each account manages
   its own VPC CIDRs. Two accounts may independently allocate
   overlapping CIDRs. Always verify before creating cross-account
   peering.
---

## Step 7 — SG cross-reference vs CIDR-based rule commands

**Same-account, same-region SG cross-reference:**

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-requester111 \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=sg-accepter222,VpcPeeringConnectionId=$PCX_ID}]" \
  --region us-east-1
```

**Cross-account or inter-region (CIDR-based rule):**

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-requester111 \
  --ip-permissions "IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=10.1.0.0/16}]" \
  --region us-east-1
```
