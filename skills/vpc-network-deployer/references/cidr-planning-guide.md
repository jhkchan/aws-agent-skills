# VPC CIDR Planning Reference Guide

Supplementary reference for the VPC Network Deployer skill. Use when
planning CIDR ranges for new VPCs, avoiding overlaps, and sizing subnets
for growth.

## RFC 1918 private address ranges

| Range | CIDR block | Total IPs | Typical scope |
|---|---|---|---|
| 10.0.0.0/8 | 10.0.0.0 – 10.255.255.255 | 16,777,216 | Large enterprises, multi-VPC, on-prem integration, Direct Connect |
| 172.16.0.0/12 | 172.16.0.0 – 172.31.255.255 | 1,048,576 | Mid-size, common default for AWS VPCs, overlaps with default Docker bridge |
| 192.168.0.0/16 | 192.168.0.0 – 192.168.255.255 | 65,536 | Small deployments, high overlap risk with home/office VPN |

**Which to choose:**
- **10.0.0.0/8** — recommended for organizations with on-premises
  networks, multi-account AWS, or plans for >5 VPCs. The huge range
  leaves room for non-overlapping CIDRs across VPCs and peering.
- **172.16.0.0/12** — acceptable for standalone AWS-only environments.
  Avoid `172.17.0.0/16` (default Docker bridge) and
  `172.18.0.0/16` (commonly used by minikube/kind).
- **192.168.0.0/16** — AVOID for VPCs. Highest overlap risk with home
  networks, corporate VPNs, coffee-shop WiFi, and mobile hotspots. Remote
  workers will lose connectivity when split-tunnel VPN conflicts.

## Subnet sizing reference

AWS reserves 5 IPs per subnet (first 4 + last). Usable IPs:

| CIDR | Total | Usable | Typical use |
|---|---|---|---|
| /28 | 16 | 11 | Lambda VPC, small dedicated function |
| /27 | 32 | 27 | Small database, bastion |
| /26 | 64 | 59 | Mid database, dedicated ELB subnet |
| /24 | 256 | 251 | Standard database tier, small app tier |
| /22 | 1,024 | 1,019 | Mid app tier |
| /20 | 4,096 | 4,091 | Production app tier (recommended minimum) |
| /18 | 16,384 | 16,379 | Large app tier, multi-service |
| /16 | 65,536 | 65,531 | Entire VPC (recommended VPC size) |

**Sizing rule:** Always provision the largest CIDR you can afford to
spend. Subnet CIDRs are immutable — a /24 that runs out requires creating
a new subnet and migrating. Over-provisioning costs nothing (AWS does not
charge per unused IP). The only constraint is VPC CIDR exhaustion.

## VPC /16 allocation strategy (3-AZ, 3-tier)

For a `10.0.0.0/16` VPC:

```
10.0.0.0/20    Public  AZ-a    (4,094 usable)
10.0.16.0/20   Public  AZ-b    (4,094 usable)
10.0.32.0/20   Public  AZ-c    (4,094 usable)
10.0.48.0/20   Private AZ-a    (4,094 usable)
10.0.64.0/20   Private AZ-b    (4,094 usable)
10.0.80.0/20   Private AZ-c    (4,094 usable)
10.0.96.0/24   Database AZ-a   (251 usable)
10.0.97.0/24   Database AZ-b   (251 usable)
10.0.98.0/24   Database AZ-c   (251 usable)
10.0.112.0/20  Reserved        (future public expansion)
10.0.128.0/17  Reserved        (future private/database expansion, 32K IPs)
```

This layout leaves ~50% of the /16 unallocated for future tiers
(elasticache, dedicated EKS, mgmt, transit).

## Multi-VPC CIDR strategy (organization level)

For an organization running multiple VPCs (production, staging, dev,
shared-services, data), assign non-overlapping /16 blocks from a /8
supernet:

```
10.0.0.0/16    Production VPC (us-east-1)
10.1.0.0/16    Staging VPC (us-east-1)
10.2.0.0/16    Development VPC (us-east-1)
10.3.0.0/16    Shared Services VPC (us-east-1)
10.4.0.0/16    Data/Analytics VPC (us-east-1)
10.10.0.0/16   Production VPC (eu-west-1)
10.11.0.0/16   Staging VPC (eu-west-1)
...
10.100.0.0/16  On-premises datacenter range 1
10.101.0.0/16  On-premises datacenter range 2
```

**Region prefix convention:** Use the second octet as a region/env
designator. This makes peering routes and firewall rules readable:
`10.0.0.0/16` is immediately recognizable as prod-useast1.

## Overlap-detection checklist

Before `create-vpc`, verify the proposed CIDR does not overlap with:

1. **Existing VPCs in the account:**
   ```
   aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock]' --output table
   ```
2. **VPCs in peered accounts** (check peering connections):
   ```
   aws ec2 describe-vpc-peering-connections --query 'VpcPeeringConnections[*].[RequesterVpcInfo.CidrBlock,AccepterVpcInfo.CidrBlock]'
   ```
3. **Transit Gateway attachments:**
   ```
   aws ec2 describe-transit-gateway-attachments --query 'TransitGatewayAttachments[*].[ResourceId,Association.TransitGatewayRouteTableId]'
   ```
4. **On-premises CIDR ranges** (require network team confirmation).
5. **Reserved ranges for future VPCs** (per the multi-VPC strategy above).

**Overlap detection math:** Two CIDRs overlap if the network address of
one is contained within the other's range. Use Python `ipaddress` module:
```python
import ipaddress
net1 = ipaddress.ip_network("10.0.0.0/16")
net2 = ipaddress.ip_network("10.0.1.0/24")
print(net1.overlaps(net2))  # True — overlap
```

## IPv6 CIDR allocation

AWS assigns a /56 IPv6 CIDR block to the VPC on request. Subnets receive
/64 blocks from the /56:

```
VPC IPv6:     2600:1f18:0001:ab00::/56
Subnet AZ-a:  2600:1f18:0001:ab00::/64
Subnet AZ-b:  2600:1f18:0001:ab01::/64
Subnet AZ-c:  2600:1f18:0001:ab02::/64
```

A /56 supports 256 /64 subnets — sufficient for any VPC topology.

**Key difference:** IPv6 addresses are internet-routable by default.
Private IPv6 subnets need an Egress-Only Internet Gateway for
outbound-only connectivity. There is no IPv6 NAT.
