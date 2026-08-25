# Routing and DNS — VPC Peering Deployer

Deep reference on route table configuration for VPC peering (both-sides
requirement, multiple route tables, IPv4/IPv6 independence), DNS
resolution across peered VPCs (AllowDnsResolutionFromPeeredVpc
mechanics, prerequisites), and common routing pitfalls. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Route table fundamentals for peering

### Why BOTH sides need routes

A VPC peering connection is a bidirectional link, but route tables are
evaluated independently per-VPC and per-direction. For traffic to flow
from VPC-A to VPC-B:

```text
VPC-A instance (10.0.1.5) → sends packet to 10.1.2.10
  → VPC-A route table: Destination 10.1.0.0/16 → Target pcx-xxx ✓
  → Packet traverses peering connection
  → VPC-B receives packet on 10.1.2.10
  → VPC-B instance responds: 10.1.2.10 → 10.0.1.5
  → VPC-B route table: Destination 10.0.0.0/16 → Target pcx-xxx ?
    ├── If route exists → response traverses peering back ✓
    └── If route MISSING → response dropped (no route to host) ✗
```

Without the accepter-side route, the initial packet may arrive but the
response is dropped. The requester sees a timeout.

### Multiple route tables per VPC

A VPC typically has multiple route tables — one per subnet (or one for
public subnets, one for private subnets). EACH route table that should
route to the peered VPC must be updated individually.

```bash
# List all route tables in the requester VPC
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=vpc-aaa11122 \
  --query 'RouteTables[*].{RouteTableId:RouteTableId,Name:Tags[?Key==`Name`].Value|[0]}' \
  --region us-east-1 --output table
```

For EACH route table that needs peering access:

```bash
aws ec2 create-route \
  --route-table-id rtb-public-subnet \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id pcx-111222333 \
  --region us-east-1

aws ec2 create-route \
  --route-table-id rtb-private-subnet \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id pcx-111222333 \
  --region us-east-1
```

### Route priority and specificity

VPC route tables use the most specific matching route. If a more
specific route exists (e.g., `10.1.2.0/24` via a NAT gateway), it takes
priority over a broader peering route (`10.1.0.0/16` via peering).

```text
Route table entries:
  10.0.0.0/16 → local          (VPC local traffic)
  10.1.0.0/16 → pcx-xxx        (peering to VPC-B)
  10.1.2.0/24 → nat-xxx        (more specific — overrides peering for 10.1.2.x)
  0.0.0.0/0   → igw-xxx        (internet traffic)
```

**Warning:** if a more specific route exists for part of the peered
CIDR, that subset will NOT use the peering connection. Ensure the
peering route is the most specific for the target CIDR.

### IPv4 vs IPv6 routes

IPv4 and IPv6 routes are independent. If both are needed:

```bash
# IPv4 route
aws ec2 create-route \
  --route-table-id rtb-app111 \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id pcx-111222333

# IPv6 route
aws ec2 create-route \
  --route-table-id rtb-app111 \
  --destination-ipv6-cidr-block 2600:1f18:4113:b200::/56 \
  --vpc-peering-connection-id pcx-111222333
```

Both routes must be added on BOTH sides.

## DNS resolution across peered VPCs

### How AllowDnsResolutionFromPeeredVpc works

By default, the Amazon-provided DNS server (169.254.169.253 at the VPC's
`.2` address) only resolves hostnames within its own VPC. When
`AllowDnsResolutionFromPeeredVpc` is enabled on the peering connection,
the DNS server can resolve hostnames from the peered VPC.

This enables:
- Resolving private hosted zone records across VPCs (with Route53
  association).
- Resolving EC2 private DNS hostnames (e.g.,
  `ip-10-1-2-10.ec2.internal`) across the peering.

### Prerequisites

1. **Both VPCs must have `enableDnsHostnames` true:**

```bash
# Check requester VPC
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 --attribute enableDnsHostnames --region us-east-1

# Check accepter VPC
aws ec2 describe-vpc-attribute --vpc-id vpc-bbb22233 --attribute enableDnsHostnames --region us-east-1

# Enable if needed
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-hostnames --region us-east-1
```

2. **Both VPCs must have `enableDnsSupport` true:**

```bash
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-support --region us-east-1
```

3. **Peering connection must be ACTIVE.**

### Enabling DNS resolution (both sides)

```bash
# Requester side
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-111222333 \
  --requester-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1

# Accepter side
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id pcx-111222333 \
  --accepter-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1
```

**Critical:** BOTH sides must enable the flag. One-sided enablement
does NOT work for bidirectional resolution.

### Verifying DNS resolution

```bash
# From an instance in VPC-A, resolve a hostname in VPC-B
dig ip-10-1-2-10.ec2.internal
# Or with a custom DNS name (if Route53 private hosted zone is associated)
dig database.internal.example.com
```

## Common routing pitfalls

### Pitfall 1: Missing accepter-side route

The #1 cause of peering connectivity issues. The requester creates the
peering and adds its route, but forgets the accepter side.

**Fix:** Verify both route tables have entries:

```bash
# Verify requester route
aws ec2 describe-route-tables \
  --route-table-ids rtb-app111 \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`10.1.0.0/16`]' \
  --region us-east-1

# Verify accepter route
aws ec2 describe-route-tables \
  --route-table-ids rtb-data222 \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`10.0.0.0/16`]' \
  --region us-east-1
```

### Pitfall 2: More specific route overriding peering

If `10.1.2.0/24` has a route via a NAT gateway or VGW, traffic to
`10.1.2.x` uses that route instead of the peering connection.

**Fix:** Ensure the peering route is the most specific for the target.
If needed, add host-specific routes (`10.1.2.10/32`) or remove the
conflicting broader route.

### Pitfall 3: Peering route points to wrong peering connection

If multiple peering connections exist, the route may point to the wrong
`pcx-xxx`.

**Fix:** Verify the peering connection ID in each route:

```bash
aws ec2 describe-route-tables \
  --route-table-ids rtb-app111 \
  --query 'RouteTables[0].Routes[?VpcPeeringConnectionId!=`null`].{Dest:DestinationCidrBlock,PCX:VpcPeeringConnectionId}' \
  --region us-east-1 --output table
```

## Terraform examples

```hcl
# Requester creates the peering connection
resource "aws_vpc_peering_connection" "requester" {
  vpc_id        = aws_vpc.app.id
  peer_vpc_id   = aws_vpc.data.id
  auto_accept   = true  # same-account only

  # For inter-region: peer_region = "us-west-2"
  # For cross-account: peer_owner_id = "999999999999"

  tags = {
    Name = "app-to-data-peering"
  }
}

# Requester route table entry
resource "aws_route" "requester_route" {
  route_table_id            = aws_route_table.app_private.id
  destination_cidr_block    = aws_vpc.data.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.requester.id
}

# Accepter route table entry (REQUIRED — even for same-account)
resource "aws_route" "accepter_route" {
  route_table_id            = aws_route_table.data_private.id
  destination_cidr_block    = aws_vpc.app.cidr_block
  vpc_peering_connection_id = aws_vpc_peering_connection.requester.id
}

# DNS resolution (both sides)
resource "aws_vpc_peering_connection_options" "requester_dns" {
  vpc_peering_connection_id = aws_vpc_peering_connection.requester.id

  requester {
    allow_remote_vpc_dns_resolution = true
  }
}

resource "aws_vpc_peering_connection_options" "accepter_dns" {
  vpc_peering_connection_id = aws_vpc_peering_connection.requester.id

  accepter {
    allow_remote_vpc_dns_resolution = true
  }
}

# Cross-account peering (different provider for accepter)
# Provider in accepter account:
# provider "aws" {
#   alias  = "accepter"
#   region = "us-east-1"
#   # Assume role or use separate credentials
# }

# resource "aws_vpc_peering_connection_accepter" "accepter" {
#   provider                  = aws.accepter
#   vpc_peering_connection_id = aws_vpc_peering_connection.requester.id
#   auto_accept               = true
# }
```
---

## Step 5 — route table update commands (both sides required)

**Requester side route (VPC-A 10.0.0.0/16 → VPC-B 10.1.0.0/16):**

```bash
aws ec2 create-route \
  --route-table-id rtb-requester111 \
  --destination-cidr-block 10.1.0.0/16 \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1
```

**Accepter side route (VPC-B 10.1.0.0/16 → VPC-A 10.0.0.0/16):**

```bash
aws ec2 create-route \
  --route-table-id rtb-accepter222 \
  --destination-cidr-block 10.0.0.0/16 \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1
```

## Step 6 — DNS resolution enablement commands (both sides)

**Enable DNS resolution (requester side):**

```bash
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id "$PCX_ID" \
  --requester-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1
```

**Enable DNS resolution (accepter side):**

```bash
aws ec2 modify-vpc-peering-connection-options \
  --vpc-peering-connection-id "$PCX_ID" \
  --accepter-peering-connection-options AllowDnsResolutionFromPeeredVpc=true \
  --region us-east-1
```

## Step 9 — IPv6 route commands (both sides)

**Add IPv6 routes (both sides):**

```bash
# Requester side
aws ec2 create-route \
  --route-table-id rtb-requester111 \
  --destination-ipv6-cidr-block 2600:1f18:4113:b200::/56 \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1

# Accepter side
aws ec2 create-route \
  --route-table-id rtb-accepter222 \
  --destination-ipv6-cidr-block 2600:1f18:4113:a100::/56 \
  --vpc-peering-connection-id "$PCX_ID" \
  --region us-east-1
```
