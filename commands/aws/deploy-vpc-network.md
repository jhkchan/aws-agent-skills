---
description: Provision a production-grade VPC with secure multi-AZ network infrastructure (CIDR planning, subnet tiers, NAT topology, route tables, security groups, NACLs, flow logs, VPC endpoints, DNS, IPv6).
nl_triggers:
  - "create a new VPC"
  - "provision VPC network"
  - "plan CIDR ranges for VPC"
  - "design multi-AZ subnets"
  - "NAT gateway HA topology"
  - "VPC endpoint configuration"
  - "VPC flow logs setup"
  - "security group and NACL design"
  - "VPC route table design"
  - "IPv6 dual-stack VPC"
  - "Transit Gateway vs VPC peering"
  - "production VPC deployment"
  - "three-tier VPC architecture"
  - "private subnet NAT gateway"
routes_to: vpc-network-deployer
---

# /aws:deploy-vpc-network

Activate the `vpc-network-deployer` skill and produce a deployment plan
for a production-grade VPC with secure, well-architected network
infrastructure.

## What it does

Reads a deployment specification (region, AZ count, CIDR range, tier
requirements, NAT strategy, endpoint requirements, flow-log destination)
and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates region, CIDR, AZ count, NAT
   strategy, tier list. Blocks deployment (PREREQUISITES_MISSING) on
   missing required fields or CIDR overlap.
2. CIDR planning — RFC 1918 range selection, /16 minimum for production,
   no overlap with existing VPCs/on-prem, growth headroom per tier per AZ.
3. Subnet tier design — public, private, database tiers across N AZs
   (N ≥ 2, recommend 3). Database tier has local-only route table.
4. Internet Gateway + Egress-Only Gateway (IPv6) — bidirectional public
   egress for public subnets, outbound-only IPv6 for private subnets.
5. NAT Gateway topology — HA (1 per AZ, ~$96/month) vs cost-optimized
   (1, ~$32/month). Each private subnet routes to its AZ-local NAT.
6. Route table design — public→IGW, private→NAT (AZ-local), database→
   local-only. One route table per private AZ for HA topology.
7. Security Groups — least-privilege, reference by SG name/ID not CIDR,
   separate SG per tier.
8. NACLs — stateless defense-in-depth, ephemeral port rule for return
   traffic.
9. VPC Flow Logs — all-traffic, S3 or CloudWatch, 1-year retention.
10. VPC Endpoints — Gateway (S3, DynamoDB — free) + Interface for
    private-service connectivity (~$7/AZ/month per endpoint).
11. DNS — enableDnsHostnames + enableDnsSupport, AmazonProvidedDNS.
12. IPv6 dual-stack — /56 from AWS, Egress-Only Gateway for private egress.
13. Multi-VPC — Transit Gateway for 3+ VPCs, peering for 1:1.

Emits a deterministic deployment plan per VPC:

```text
VPC_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Region / CIDR / AZs / Tiers / NAT / Endpoints / Flow Logs / DNS
CHECKLIST:
  [x] CIDR range is RFC 1918 and does not overlap
  [x] Subnet tiers span N AZs with growth headroom
  [x] Public subnets route 0.0.0.0/0 → IGW
  [x] Private subnets route 0.0.0.0/0 → AZ-local NAT Gateway
  [x] Database subnets have NO internet route (local-only)
  ...
FINDINGS:
  - [INFO] Cost-savings from Gateway Endpoints
  - [WARN] Cost-optimized NAT — AZ failure cuts private egress
DEPLOY_COMMANDS:
  <ordered list of aws ec2 create-* commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a production VPC in us-east-1 with 3 AZs"
- "design CIDR ranges for a multi-tier VPC"
- "NAT gateway HA topology for my VPC"
- "set up VPC endpoints for private connectivity"
- "configure VPC flow logs for security forensics"
- "IPv6 dual-stack VPC"

A bare region + CIDR + "deploy VPC" also routes here via the orchestrator.

## Inputs

- **Required:** region (AWS region), cidr_block (RFC 1918, /16 minimum
  for production), az_count (2 minimum, 3 recommended), nat_strategy
  (HA or cost-optimized), tier_list (public, private, database — at
  least private required).
- **Optional:** endpoint_list, flow_log_destination, ipv6 (dual-stack),
  multi_vpc_topology (peering vs Transit Gateway).

## Outputs

- One VERDICT block per VPC (READY_TO_DEPLOY or PREREQUISITES_MISSING).
- ARCHITECTURE summary with tier/AZ/endpoint layout.
- CHECKLIST with all 11 network-architecture dimensions validated.
- FINDINGS with cost estimates and HA-risk warnings.
- DEPLOY_COMMANDS with ordered `aws ec2 create-*` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for VPC networking).
- `/aws:audit-ec2-security-groups` for post-deployment SG auditing.
- `/aws:audit-vpc-lattice-auth` for service-network auth policies layered
  on top of the VPC.
