---
name: vpc-network-deployer
description: >-
  Provisions production-grade VPCs with secure, well-architected network
  infrastructure: RFC 1918 CIDR planning with growth headroom, multi-AZ
  public/private/database subnet tiers, NAT Gateway HA placement (1-per-AZ
  vs single for cost), Internet Gateway vs Egress-Only Gateway (IPv6),
  least-privilege route table design (public→IGW, private→NAT, database→
  local-only), Security Groups that reference by name not CIDR, stateless
  NACLs for defense-in-depth, VPC Flow Logs with long retention, Gateway
  (S3/DynamoDB — free) vs Interface VPC Endpoints (private DNS, per-AZ
  cost), DHCP option sets and Route 53 Resolver DNS resolution, VPC peering
  vs Transit Gateway for multi-VPC, and IPv6 dual-stack considerations.
  Emits a deterministic deployment plan with a READY_TO_DEPLOY checklist
  and network architecture validation. Use when provisioning a new VPC,
  designing multi-tier subnet layouts, planning CIDR ranges to avoid
  overlaps, configuring NAT Gateway topology, setting up VPC endpoints
  for private connectivity, or hardening VPC network posture before
  production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline architecture planning. Live
  deployment uses aws ec2 create-vpc, create-subnet, create-route-table,
  create-nat-gateway, create-security-group, create-flow-logs,
  create-vpc-endpoint, and describe-* verification commands (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - VPC
  - CIDR planning
  - RFC 1918
  - subnet design
  - multi-AZ
  - public subnet
  - private subnet
  - database subnet
  - NAT Gateway
  - Internet Gateway
  - Egress-Only Gateway
  - route table
  - Security Group
  - NACL
  - VPC Flow Logs
  - VPC Endpoint
  - Gateway Endpoint
  - Interface Endpoint
  - PrivateLink
  - DHCP options
  - Route 53 Resolver
  - VPC peering
  - Transit Gateway
  - IPv6 dual-stack
  - network architecture
tags: [vpc, networking, deploy, subnets, nat-gateway, route-tables, security-groups, nacl, flow-logs, vpc-endpoints, ipv6, transit-gateway]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new VPC for production, designing a multi-tier subnet
    layout (public/private/database), planning CIDR ranges to avoid overlaps
    with existing networks, selecting NAT Gateway topology for HA vs cost,
    configuring VPC endpoints for private S3/DynamoDB connectivity, setting
    up VPC Flow Logs for security forensics, designing route tables for
    least-privilege traffic flow, hardening VPC security groups and NACLs,
    or planning IPv6 dual-stack support.
  activation_triggers:
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
  invocation_schema: >-
    Input shape (one of): (a) a deployment specification including region,
    AZ count, CIDR range, tier requirements (public/private/database), NAT
    strategy (HA vs cost), endpoint requirements, and flow-log destination;
    (b) a partial spec for interactive refinement (e.g., "3-AZ VPC in
    us-east-1 with /16 CIDR, private-only"); (c) an existing VPC ID for
    architecture review against the well-architected checklist. Output
    shape: { VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[],
    DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING,
    ERROR }.
---

# VPC Network Deployer

## Mindset

**One-line takeaway:** a production VPC is not "a /16 with subnets" — it is
a **routing graph** where every route-table entry, every security-group
rule, and every NACL rule is an explicit security decision. The CIDR block
is the least interesting part; the **subnet tiering, NAT topology, and
endpoint strategy** determine blast radius, cost, and failover behavior.

Three facts make VPC provisioning different from "draw a network diagram":

- **Subnet CIDR blocks are immutable.** A subnet's CIDR cannot be resized
  after creation. A /24 subnet that runs out of IPs cannot be expanded —
  you must create a new subnet and migrate workloads. CIDR planning must
  account for growth at provisioning time, not later.
- **"Public subnet" is a route-table property, not a subnet property.**
  A subnet becomes "public" when its route table has a `0.0.0.0/0` route
  to an Internet Gateway. The subnet itself has no "public" attribute.
  Misunderstanding this leads to accidentally exposing private workloads.
- **NAT Gateway is the single largest VPC cost driver.** A single NAT
  Gateway costs ~$32/month + $0.045/GB processed. A 3-AZ HA topology (one
  per AZ) triples the base cost. Choosing HA vs cost-optimized is a
  deliberate trade-off, not a default.

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| CIDR block | RFC 1918, no overlap with existing VPCs/on-prem, /16 minimum for production | Step 1 |
| Subnet tiers | Public, private, and database tiers across N AZs (N ≥ 2, recommend 3) | Step 2 |
| Internet Gateway | Attached for public subnet egress | Step 3 |
| NAT Gateway | 1 per AZ (HA) or 1 in AZ-a (cost-optimized) | Step 4 |
| Route tables | Public→IGW, private→NAT (AZ-local), database→local-only | Step 5 |
| Security Groups | Least-privilege, reference by SG name/ID, not CIDR | Step 6 |
| NACLs | Stateless defense-in-depth for known IP ranges | Step 7 |
| VPC Flow Logs | All-traffic, S3 or CloudWatch, 1-year retention | Step 8 |
| VPC Endpoints | Gateway (S3, DynamoDB — free) + Interface for private services | Step 9 |
| DNS | enableDnsHostnames + enableDnsSupport true, DHCP option set | Step 10 |
| IPv6 | Dual-stack optional; Egress-Only Gateway for IPv6 egress | Step 11 |
| Multi-VPC | Transit Gateway for >2 VPCs; peering for 1:1 | Step 12 |

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure VPC.

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify the caller can run `ec2:CreateVpc`, `ec2:CreateSubnet`,
   `ec2:CreateRouteTable`, `ec2:CreateNatGateway`, `ec2:CreateSecurityGroup`,
   `ec2:CreateFlowLogs`, and `ec2:CreateVpcEndpoint`. Surface IAM gaps
   BEFORE emitting deployment commands.
2. Check for CIDR overlap with existing VPCs:
   `aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock]' --output table`
3. Check for CIDR overlap with on-premises ranges (requires network
   team input — flag as a PREREQUISITES_MISSING if not provided).
4. Verify an Elastic IP is available for the NAT Gateway (default EIP
   quota is 5 per region).
5. Verify the target region has ≥3 AZs available:
   `aws ec2 describe-availability-zones --region <region> --query 'AvailabilityZones[?State==`available`].ZoneName'`

| Attribute | Value | Effect on plan |
|---|---|---|
| Region | Valid AWS region | Determines available AZs and service endpoints |
| AZ count | 2 | Minimum for HA. Acceptable but not ideal — single AZ failure takes 50% of capacity. |
| AZ count | 3 | **Recommended.** Survives a single AZ failure with 67% capacity. Standard for production. |
| CIDR block | /16 to /28 | /16 (65,536 IPs) recommended for production. /20 is the practical minimum for a 3-tier, 3-AZ layout. |
| NAT strategy | HA (1 per AZ) | ~$96/month base + data processing. Survives AZ failure. |
| NAT strategy | Cost-optimized (1) | ~$32/month base + data processing. Single AZ failure cuts egress. |
| Endpoint budget | None | All traffic routes through NAT — higher cost, lower security |
| IPv6 | Dual-stack | Requires /56 IPv6 CIDR assigned by AWS. Egress-Only Gateway for private IPv6 egress. |

**If the deployment spec is incomplete** (missing region, CIDR range, or
AZ count), output:

```text
VPC_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting VPC
would be non-functional or insecure.
REQUIRED:
  - region (AWS region for the VPC)
  - cidr_block (RFC 1918 range, /16 minimum for production)
  - az_count (2 minimum, 3 recommended)
  - nat_strategy (HA or cost-optimized)
  - tier_list (public, private, database — at least private required)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious VPC behaviors that change the plan

These behaviors are easy to misjudge without operational VPC experience.
Each changes the architecture if ignored:

- **Subnet CIDR blocks are immutable.** Once created, a subnet's CIDR
  cannot be expanded or shrunk. If a /24 runs out of IPs, the only fix is
  creating a new subnet and migrating workloads. Always over-provision
  subnet CIDRs at /20 or larger for app tiers, /24 or larger for database
  tiers.

- **"Public subnet" is a route-table property.** A subnet has no inherent
  "public" flag. A subnet is public if its associated route table has a
  `0.0.0.0/0 → igw-xxx` route. A misconfigured route table can silently
  expose a private workload to the internet. Always audit route tables,
  not subnet names.

- **NAT Gateway does NOT support IPv6.** NAT Gateway only processes IPv4
  traffic. IPv6 egress from private subnets requires an Egress-Only
  Internet Gateway (EIGW). A dual-stack VPC without an EIGW has IPv6
  traffic routed directly to the IGW — bypassing NAT entirely.

- **Security Groups are stateful; NACLs are stateless.** SGs
  automatically allow return traffic for any allowed inbound/outbound
  connection. NACLs require explicit inbound AND outbound rules for each
  connection. NACLs are evaluated BEFORE SGs — a NACL deny blocks traffic
  before the SG is consulted.

- **VPC Flow Logs do NOT capture all packet metadata.** Flow Logs capture
  source/dest IP, source/dest port, protocol, packet count, byte count,
  action (ACCEPT/REJECT), and log status. They do NOT capture packet
  payload, TLS SNI, DNS queries, or HTTP headers. For deep inspection,
  use VPC Traffic Mirroring to a network appliance.

- **Gateway Endpoints (S3, DynamoDB) are FREE.** They route traffic
  through the AWS private network without a NAT Gateway, saving $0.045/GB
  + $32/month NAT cost. Always provision Gateway Endpoints for S3 and
  DynamoDB — there is no downside.

- **Interface Endpoints cost ~$7/month per AZ per endpoint.** An
  Interface Endpoint for `com.amazonaws.us-east-1.secretsmanager` in a
  3-AZ VPC costs ~$21/month. Each service needs its own endpoint. A
  full Interface Endpoint suite (Secrets Manager, SSM, KMS, CloudWatch,
  ECR, STS) in 3 AZs costs ~$126/month. Budget for this.

- **enableDnsHostnames and enableDnsSupport are BOTH required.**
  `enableDnsHostnames: true` allows VPC resources to get DNS hostnames.
  `enableDnsSupport: true` enables DNS resolution within the VPC. Both
  must be true for the VPC to support Route 53 private hosted zones,
  Interface Endpoints with private DNS, and ALB/NLB DNS resolution.

- **DHCP option sets apply at the VPC level, not per-subnet.** Changing
  the DHCP option set affects all running instances in the VPC. The
  change requires instances to renew their DHCP lease (reboot or network
  restart). There is no rollback — the previous DHCP option set is lost.

- **VPC peering does NOT support transitive routing.** If VPC-A peers
  with VPC-B, and VPC-B peers with VPC-C, VPC-A CANNOT route to VPC-C
  through VPC-B. Each pair needs its own peering connection. For
  multi-VPC topologies, use Transit Gateway.

- **Transit Gateway has a per-attachment monthly cost.** Each VPC
  attached to a TGW costs ~$16.50/month + $0.02/GB processed. For 2
  VPCs, peering is cheaper. For 3+ VPCs, TGW is more manageable.

- **IPv6 addresses are assigned by AWS; you cannot bring your own.**
  AWS assigns a /56 IPv6 CIDR to the VPC. Each subnet gets a /64 from
  that range. IPv6 is internet-routable by default — private IPv6
  subnets need an Egress-Only Gateway for outbound-only connectivity.

- **A subnet's AZ is fixed at creation.** `create-subnet --availability-zone
  us-east-1a` pins the subnet to AZ-a. You cannot move a subnet to a
  different AZ. Always create subnets in matching AZ sets across tiers
  (public-a, private-a, database-a in us-east-1a; public-b, private-b,
  database-b in us-east-1b) so workloads can span AZs cleanly.

- **Route tables are subnet-level, not instance-level.** Each subnet
  associates with exactly one route table. A route table can be
  associated with multiple subnets. The "main" route table is the VPC
  default — any subnet without an explicit association uses the main
  table.

### Step 1: CIDR planning

**RFC 1918 private ranges:**

| Range | CIDR | IPs | Typical use |
|---|---|---|---|
| 10.0.0.0/8 | /8 to /28 | 16M+ | Large enterprises, multi-VPC, on-prem integration |
| 172.16.0.0/12 | /12 to /28 | 1M+ | Mid-size, common for VPCs |
| 192.168.0.0/16 | /16 to /28 | 65K+ | Small deployments, home/office overlap risk |

**CIDR allocation strategy for a /16 VPC (10.0.0.0/16):**

| Tier | AZ-a | AZ-b | AZ-c | Mask | IPs per subnet |
|---|---|---|---|---|---|
| Public | 10.0.0.0/20 | 10.0.16.0/20 | 10.0.32.0/20 | /20 | 4,094 |
| Private (app) | 10.0.48.0/20 | 10.0.64.0/20 | 10.0.80.0/20 | /20 | 4,094 |
| Database | 10.0.96.0/24 | 10.0.97.0/24 | 10.0.98.0/24 | /24 | 254 |
| Reserved | 10.0.112.0/20 | 10.0.128.0/17 | — | — | Future expansion |

**Overlap-check rule:** Before deploying, the CIDR range MUST be checked
against:
1. Existing VPCs in the account (`describe-vpcs`)
2. VPCs in peered accounts (peering connections)
3. On-premises CIDR ranges (Direct Connect, VPN)
4. Transit Gateway-attached VPCs
5. Reserved CIDR ranges for future VPCs

If ANY overlap exists → **PREREQUISITES_MISSING**. A non-overlapping CIDR
range is mandatory.

**Sizing rationale:** A /16 (65,536 IPs) seems excessive for a starter
VPC, but AWS reserves 5 IPs per subnet (network, broadcast, DNS, future
use ×2). A /28 subnet has only 11 usable IPs. A /24 has 251 usable.
Over-provisioning at /20 (4,094 IPs) per tier per AZ eliminates the need
for subnet migration later.

### Step 2: Subnet tier design

**Three-tier model (recommended for production):**

| Tier | Purpose | Route table | Internet egress |
|---|---|---|---|
| Public | ALB, NAT Gateway, Bastion | 0.0.0.0/0 → IGW | Direct via IGW |
| Private | Application workloads (ECS, EKS, EC2, Lambda-VPC) | 0.0.0.0/0 → NAT (AZ-local) | NAT Gateway |
| Database | RDS, ElastiCache, Redshift | Local only | No internet egress |

**Why database subnets have no internet route:** Database tier security
relies on defense-in-depth. The security group allows only app-tier
ingress. The NACL adds explicit IP-range filtering. The route table has
NO `0.0.0.0/0` route — even if an instance is compromised and the SG is
modified, the database cannot reach the internet for data exfiltration.

**Two-tier model (acceptable for non-production):**
- Public tier (ALB, NAT)
- Private tier (everything else, including databases grouped with apps)

**One-tier model (NEVER for production):**
- All resources in public subnets. No isolation. Only acceptable for
  throwaway sandboxes or demos. Flag as PREREQUISITES_MISSING.

### Step 3: Internet Gateway and public egress

An Internet Gateway (IGW) is the bidirectional gateway between the VPC
and the public internet. It is:
- **Highly available** across all AZs in the region by default.
- **Cost-free** (no per-hour or per-GB charge).
- **Required** for: public subnets, public IPv4 addresses, ALB public
  listeners, and NAT Gateway deployment (NAT lives in a public subnet).

**Egress-Only Internet Gateway (EIGW)** for IPv6:
- Provides outbound-only IPv6 internet access.
- Prevents inbound IPv6 connections from the internet.
- Required for private subnets that need IPv6 egress without IPv6 ingress.
- Cost-free.

**Deployment:**
```
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=prod-igw}]'
aws ec2 attach-internet-gateway --internet-gateway-id igw-xxx --vpc-id vpc-xxx
# IPv6 (optional):
aws ec2 create-egress-only-internet-gateway --vpc-id vpc-xxx
```

### Step 4: NAT Gateway topology

**HA topology (1 NAT Gateway per AZ):**
- Each private subnet routes to its AZ-local NAT Gateway.
- Survives AZ failure without cross-AZ data charges for NAT.
- Cost: ~$32/month × N AZs = ~$96/month for 3 AZs, plus per-GB.
- **Recommended for production.**

**Cost-optimized topology (1 NAT Gateway in AZ-a):**
- All private subnets route to the single NAT Gateway in AZ-a.
- If AZ-a fails, all private egress fails.
- Cross-AZ data transfer charges apply for AZ-b/c traffic routing to AZ-a NAT.
- Cost: ~$32/month, plus per-GB + cross-AZ.
- **Acceptable for dev/staging. Flag as a finding for production.**

**Deployment:**
```
aws ec2 allocate-address --domain vpc  # Elastic IP for NAT
aws ec2 create-nat-gateway --subnet-id subnet-public-a --allocation-id eipalloc-xxx
# Wait for NAT Gateway to become Available (1-3 minutes)
aws ec2 wait nat-gateway-available --nat-gateway-id nat-xxx
```

**Anti-pattern:** NEVER deploy a NAT Gateway in a private subnet. The NAT
Gateway MUST be in a public subnet with an IGW route — otherwise it
cannot route traffic to the internet and deployment fails.

### Step 5: Route table design

**Public route table (one per VPC, associated with all public subnets):**

| Destination | Target | Purpose |
|---|---|---|
| 10.0.0.0/16 | local | VPC-internal routing |
| 0.0.0.0/0 | igw-xxx | Internet egress |
| ::/0 | igw-xxx | IPv6 internet egress (if dual-stack) |

**Private route table (one per AZ, associated with AZ's private subnet):**

| Destination | Target | Purpose |
|---|---|---|
| 10.0.0.0/16 | local | VPC-internal routing |
| 0.0.0.0/0 | nat-xxx (AZ-local) | NAT egress via AZ-local NAT |
| ::/0 | eigw-xxx | IPv6 egress (Egress-Only Gateway) |

**Database route table (one per AZ, associated with AZ's database subnet):**

| Destination | Target | Purpose |
|---|---|---|
| 10.0.0.0/16 | local | VPC-internal routing ONLY |

**Critical:** The database route table has NO `0.0.0.0/0` route. This is
the defense-in-depth mechanism. Even if a database instance is compromised
and its SG is opened, the instance cannot reach the internet.

**Why one private route table per AZ (HA topology):** Each AZ's private
subnet routes to its own NAT Gateway. This avoids cross-AZ data transfer
charges ($0.01/GB each direction) and ensures AZ-local egress. With a
single route table, all AZs would route to one NAT Gateway, defeating the
HA topology.

### Step 6: Security Groups

Security Groups are **stateful** — return traffic is automatically allowed
for any allowed connection. Design principles:

1. **Reference by name/ID, not CIDR.** Use `Source: sg-xxx` instead of
   `Source: 10.0.1.0/24`. This prevents scope creep when CIDR ranges
   change.
2. **Least-privilege ports.** Allow only the exact port needed (e.g.,
   `443/tcp` not `0-65535/tcp`).
3. **No `0.0.0.0/0` inbound except for public ALBs.** The ALB security
   group allows `443/tcp` from `0.0.0.0/0`; the app security group allows
   `8080/tcp` from the ALB security group only.
4. **Separate SG per tier.** Public SG, App SG, Database SG — never reuse
   one SG across tiers.

**Standard security group layout:**

| SG | Inbound | Outbound |
|---|---|---|
| `public-alb-sg` | 443/tcp from 0.0.0.0/0, 80/tcp from 0.0.0.0/0 (redirect) | All to app-sg |
| `app-sg` | 8080/tcp from public-alb-sg, 8080/tcp from internal-alb-sg | 443/tcp to db-sg, all to NAT (for package updates) |
| `db-sg` | 5432/tcp from app-sg (PostgreSQL), 6379/tcp from app-sg (Redis) | None (default deny) |
| `bastion-sg` | 22/tcp from corporate CIDR | 22/tcp to app-sg, 5432/tcp to db-sg (for admin tunnelling) |

### Step 7: Network ACLs (NACLs)

NACLs are **stateless** — each connection requires an explicit inbound
AND outbound rule. They are evaluated before Security Groups. Use NACLs
for:

- **Defense-in-depth IP filtering** (e.g., block known-bad CIDRs).
- **Blocking specific traffic patterns** (e.g., block all SSH from
  non-corporate ranges, even if the SG allows it).
- **Compliance requirements** that mandate stateless filtering.

**Do NOT use NACLs as the primary security control.** SGs are stateful,
easier to manage, and support referencing by name. NACLs are IP/CIDR-only
and require managing ephemeral port ranges for return traffic.

**Standard NACL layout (rules are evaluated lowest-numbered first):**

| Rule # | Direction | Protocol | Source/Dest | Port | Action |
|---|---|---|---|---|---|
| 100 | Inbound | TCP | 10.0.0.0/16 | 8080 | ALLOW |
| 110 | Inbound | TCP | 0.0.0.0/0 | 443 | ALLOW |
| 120 | Inbound | TCP | 1024-65535 | 1024-65535 | ALLOW (return traffic for outbound) |
| 140 | Inbound | TCP | <corporate-cidr> | 22 | ALLOW |
| * | Inbound | All | 0.0.0.0/0 | All | DENY (default) |

**Ephemeral port rule:** NACLs require allowing the ephemeral port range
(1024-65535) for return traffic. Without this, outbound HTTPS connections
(HTTPS to the API, package updates) will fail because the response packets
hit the NACL's default deny.

### Step 8: VPC Flow Logs

VPC Flow Logs capture metadata about IP traffic to/from network interfaces
in the VPC. They are essential for:

- **Security forensics** (identifying the source of an attack after the fact).
- **Compliance** (most regulations require network-level logging).
- **Troubleshooting** (diagnosing connectivity issues).
- **Anomaly detection** (detecting data exfiltration patterns).

**Destination options:**

| Destination | Cost | Retention | Query capability |
|---|---|---|---|
| S3 bucket | $0.023/GB/month (standard) | Lifecycle rules (e.g., 90d standard, 1yr Glacier) | Athena queries |
| CloudWatch Logs | $0.50/GB ingested + $0.03/GB stored | 1-3650 days | CloudWatch Logs Insights |
| Kinesis Data Firehose | $0.029/GB | Depends on destination | Real-time processing |

**Recommendation:** S3 destination with Athena for querying. Cheapest for
long retention. Use CloudWatch Logs only if you need real-time alerts on
flow-log patterns.

**Deployment:**
```
# S3-destination flow logs
aws ec2 create-flow-logs \
  --resource-id vpc-xxx \
  --resource-type VPC \
  --traffic-type ALL \
  --log-destination-type s3 \
  --log-destination arn:aws:s3:::prod-vpc-flow-logs \
  --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status} ${vpc-id} ${subnet-id} ${instance-id} ${tcp-flags} ${pkt-srcaddr} ${pkt-dstaddr}'
```

**Configuration requirements:**
- `traffic-type: ALL` (not just ACCEPT or REJECT — both directions matter).
- Log format MUST include `srcaddr`, `dstaddr`, `srcport`, `dstport`,
  `protocol`, `action`, `pkt-srcaddr`, `pkt-dstaddr` at minimum.
- S3 bucket MUST have a bucket policy allowing `logs.amazonaws.com` to
  write `PutObject`.
- Retention via S3 lifecycle rule: 90 days standard → Glacier → expire at
  1 year (or longer per compliance).

### Step 9: VPC Endpoints

**Gateway Endpoints (free):**

| Service | Endpoint | Notes |
|---|---|---|
| S3 | `com.amazonaws.<region>.s3` | Route-table-based. No per-hour/per-GB cost. Add to every route table that needs S3 access from private subnets. |
| DynamoDB | `com.amazonaws.<region>.dynamodb` | Route-table-based. Same as S3. |

**Always deploy Gateway Endpoints for S3 and DynamoDB.** They save NAT
Gateway data-processing costs ($0.045/GB) and improve latency. There is
no downside.

**Interface Endpoints (ENI-based, ~$7/month per AZ):**

| Service | Endpoint | Why |
|---|---|---|
| Secrets Manager | `com.amazonaws.<region>.secretsmanager` | Avoid NAT for secret retrieval |
| SSM | `com.amazonaws.<region>.ssm` | Session Manager, Parameter Store |
| KMS | `com.amazonaws.<region>.kms` | KMS API calls without NAT |
| CloudWatch Logs | `com.amazonaws.<region>.logs` | Log delivery without NAT |
| STS | `com.amazonaws.<region>.sts` | AssumeRole without NAT |
| ECR | `com.amazonaws.<region>.ecr.api` + `ecr.dkr` | Container image pulls without NAT |

**Interface Endpoint deployment:**
```
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --subnet-ids subnet-private-a subnet-private-b subnet-private-c \
  --security-group-ids sg-endpoint-xxx \
  --private-dns-enabled
```

**Private DNS:** `--private-dns-enabled` rewrites the service's public DNS
name (e.g., `secretsmanager.us-east-1.amazonaws.com`) to the endpoint's
private IP within the VPC. Without it, applications must use the
endpoint-specific DNS name — most SDKs default to the public name and
would route through NAT. Always enable private DNS for Interface Endpoints
unless you have a specific reason not to.

### Step 10: DNS resolution

**Required VPC attributes:**
```
aws ec2 modify-vpc-attribute --vpc-id vpc-xxx --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id vpc-xxx --enable-dns-support
```

Both MUST be true for:
- Route 53 private hosted zones to resolve.
- Interface Endpoints with private DNS to work.
- ALB/NLB DNS hostnames to resolve within the VPC.
- VPC peering DNS resolution (if enabled).

**DHCP option sets:**
```
aws ec2 create-dhcp-options \
  --dhcp-configurations \
    "Key=domain-name,Values=[us-east-1.compute.internal]" \
    "Key=domain-name-servers,Values=[AmazonProvidedDNS]"
aws ec2 associate-dhcp-options --dhcp-options-id dopt-xxx --vpc-id vpc-xxx
```

`AmazonProvidedDNS` (at 169.254.169.253) is the Route 53 Resolver. It
resolves Route 53 private hosted zones and provides recursive DNS for
the VPC. Use the default unless you have a specific reason to use custom
DNS servers.

### Step 11: IPv6 dual-stack considerations

IPv6 is optional but recommended for public-facing workloads (ALB, NAT64).

**Deployment:**
```
aws ec2 associate-ipv6-cidr-block --vpc-id vpc-xxx --amazon-provided-ipv6-cidr-block
# AWS assigns a /56 to the VPC
aws ec2 associate-subnet-cidr-block --subnet-id subnet-xxx --ipv6-cidr-block 2600:1f18:xxxx:xxxx::/64
```

**Key differences from IPv4:**
- IPv6 addresses are **internet-routable by default**. There is no NAT for
  IPv6. Private IPv6 subnets need an Egress-Only Internet Gateway.
- Security Groups and NACLs filter IPv6 traffic independently. A rule
  allowing `0.0.0.0/0` does NOT allow IPv6 — add `::/0` explicitly.
- NAT Gateway does NOT process IPv6 traffic. IPv6 egress uses EIGW.
- Route 53 Resolver supports IPv6 (AAAA records) with AmazonProvidedDNS.

### Step 12: Multi-VPC connectivity

**VPC Peering (1:1):**
- Direct network connection between two VPCs.
- No transitive routing (A↔B, B↔C does NOT enable A↔C).
- No per-hour cost; $0.01/GB cross-region data transfer.
- **Use for:** Simple 2-VPC topologies, same-region, low complexity.

**Transit Gateway (hub-and-spoke):**
- Centralized router for N VPCs.
- Supports transitive routing, route tables, segmentation.
- ~$16.50/month per VPC attachment + $0.02/GB processed.
- **Use for:** 3+ VPCs, multi-account, shared-services VPC, VPN/Direct
  Connect integration.

**Decision rule:** If you have ≤2 VPCs and no VPN/Direct Connect, use
peering. If you have ≥3 VPCs, multi-account, or need centralized routing,
use Transit Gateway. Migrating from peering to TGW later is painful —
plan for growth.

## Output format (per VPC deployment plan)

```text
VPC_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Region: <region>
  CIDR: <vpc-cidr> (IPv4), <ipv6-cidr> (IPv6, if dual-stack)
  AZs: [<az-a>, <az-b>, <az-c>]
  Tiers:
    - Public: [<subnet-a>, <subnet-b>, <subnet-c>] → IGW
    - Private: [<subnet-a>, <subnet-b>, <subnet-c>] → NAT (HA per-AZ)
    - Database: [<subnet-a>, <subnet-b>, <subnet-c>] → local-only
  NAT: <HA (3 NAT Gateways, one per AZ) | Cost-optimized (1 NAT Gateway)>
  Endpoints: [Gateway: S3, DynamoDB | Interface: SecretsManager, SSM, KMS, ...]
  Flow Logs: S3 destination, 1-year retention
  DNS: enableDnsHostnames + enableDnsSupport, AmazonProvidedDNS
CHECKLIST:
  [x] CIDR range is RFC 1918 and does not overlap with existing VPCs/on-prem
  [x] Subnet tiers span 3 AZs with growth headroom (/20 per tier per AZ)
  [x] Public subnets route 0.0.0.0/0 → IGW
  [x] Private subnets route 0.0.0.0/0 → AZ-local NAT Gateway
  [x] Database subnets have NO internet route (local-only)
  [x] Security Groups reference by name/ID, least-privilege ports
  [x] NACLs allow ephemeral ports for return traffic
  [x] VPC Flow Logs capture ALL traffic to S3 with 1-year retention
  [x] Gateway Endpoints for S3 and DynamoDB (free, no downside)
  [x] Interface Endpoints for private-service connectivity
  [x] DNS hostnames and support enabled
FINDINGS:
  - [INFO] Gateway Endpoints for S3/DynamoDB will save ~$X/month in NAT processing
  - [WARN] Cost-optimized NAT topology — AZ-a failure cuts all private egress
DEPLOY_COMMANDS:
  <ordered list of aws ec2 create-* commands>
```

### Worked example — 3-AZ HA VPC with full tiers

```text
VPC_SPEC: prod-vpc-useast1
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Region: us-east-1
  CIDR: 10.0.0.0/16 (IPv4), 2600:1f18:xxxx::/56 (IPv6 dual-stack)
  AZs: [us-east-1a, us-east-1b, us-east-1c]
  Tiers:
    - Public: [10.0.0.0/20, 10.0.16.0/20, 10.0.32.0/20] → IGW
    - Private: [10.0.48.0/20, 10.0.64.0/20, 10.0.80.0/20] → NAT (HA per-AZ)
    - Database: [10.0.96.0/24, 10.0.97.0/24, 10.0.98.0/24] → local-only
  NAT: HA (3 NAT Gateways, one per AZ, ~$96/month base)
  Endpoints:
    - Gateway: S3, DynamoDB (free)
    - Interface: SecretsManager, SSM, KMS, CloudWatch Logs, STS (~$126/month)
  Flow Logs: S3 destination (arn:aws:s3:::prod-vpc-flow-logs), 1-year retention
  DNS: enableDnsHostnames + enableDnsSupport, AmazonProvidedDNS
CHECKLIST:
  [x] CIDR 10.0.0.0/16 is RFC 1918, no overlap with existing VPCs or on-prem
  [x] Subnet tiers span 3 AZs with /20 growth headroom per tier per AZ
  [x] Public subnets route 0.0.0.0/0 → igw-prod
  [x] Private subnets route 0.0.0.0/0 → AZ-local NAT Gateway
  [x] Database subnets have local-only route table (no internet egress)
  [x] Security Groups reference by name (sg-prod-alb, sg-prod-app, sg-prod-db)
  [x] NACLs allow ephemeral ports (1024-65535) for return traffic
  [x] VPC Flow Logs capture ALL traffic to S3 with 1-year retention
  [x] Gateway Endpoints for S3 and DynamoDB deployed to all route tables
  [x] Interface Endpoints for private-service connectivity (6 services × 3 AZs)
  [x] DNS hostnames and support enabled
FINDINGS:
  - [INFO] Gateway Endpoints for S3/DynamoDB will save ~$200/month in NAT processing
  - [INFO] Estimated monthly cost: VPC $0 + NAT $96 + Interface Endpoints $126 + Flow Logs S3 $10 = ~$232/month
  - [NOTE] IPv6 dual-stack requires Egress-Only Internet Gateway for private subnets
DEPLOY_COMMANDS:
  1. aws ec2 create-vpc --cidr-block 10.0.0.0/16 --amazon-provided-ipv6-cidr-block
  2. aws ec2 modify-vpc-attribute --vpc-id <vpc> --enable-dns-hostnames
  3. aws ec2 modify-vpc-attribute --vpc-id <vpc> --enable-dns-support
  4. aws ec2 create-internet-gateway + attach
  5. aws ec2 create-egress-only-internet-gateway
  6. aws ec2 create-subnet (×9: 3 tiers × 3 AZs)
  7. aws ec2 create-nat-gateway (×3: one per AZ, in public subnets)
  8. aws ec2 create-route-table (×7: 1 public + 3 private + 3 database)
  9. aws ec2 create-security-group (×4: alb, app, db, bastion)
  10. aws ec2 create-network-acl (×3: one per tier)
  11. aws ec2 create-flow-logs --traffic-type ALL --log-destination-type s3
  12. aws ec2 create-vpc-endpoint --vpc-endpoint-type Gateway (×2: S3, DynamoDB)
  13. aws ec2 create-vpc-endpoint --vpc-endpoint-type Interface (×6 services)
```

## Verification commands (run after deployment)

```bash
# Verify VPC exists and has correct CIDR
aws ec2 describe-vpcs --vpc-ids vpc-xxx --query 'Vpcs[0].[VpcId,CidrBlock,Ipv6CidrBlockAssociationSet]'

# Verify subnets exist with correct CIDRs and AZs
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Verify route tables have correct routes
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'RouteTables[*].[RouteTableId,Routes[*].[DestinationCidrBlock,GatewayId,NatGatewayId]]' \
  --output table

# Verify NAT Gateways are in public subnets and Available
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=vpc-xxx" \
  --query 'NatGateways[*].[NatGatewayId,State,SubnetId]'

# Verify Internet Gateway is attached
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=vpc-xxx"

# Verify Security Groups exist with correct rules
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'SecurityGroups[*].[GroupName,GroupId,IpPermissions[*].[FromPort,ToPort,UserIdGroupPairs[*].GroupId]]'

# Verify VPC Flow Logs are active
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-xxx"

# Verify VPC Endpoints exist and are available
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State,VpcEndpointType]'

# Verify DNS settings
aws ec2 describe-vpc-attribute --vpc-id vpc-xxx --attribute enableDnsHostnames
aws ec2 describe-vpc-attribute --vpc-id vpc-xxx --attribute enableDnsSupport

# Test connectivity from a private subnet instance
aws ssm start-session --target i-xxx  # Session Manager via SSM Interface Endpoint
# Inside the instance:
#   curl -s http://169.254.169.254/latest/meta-data/  # IMDS (should work)
#   ping 8.8.8.8  # NAT egress (should work from private subnet)
#   aws s3 ls  # Gateway Endpoint (should work without NAT)
```

## Edge-case handling

- **Single-AZ VPC.** A single-AZ VPC has no HA. Flag as PREREQUISITES_MISSING
  for production workloads. Acceptable for dev/sandbox only.

- **CIDR overlap with on-premises.** If the VPC CIDR overlaps with on-prem
  ranges, VPN/Direct Connect routing will fail (asymmetric routing, dropped
  packets). This is a hard blocker — choose a different CIDR before
  deploying.

- **NAT Gateway quota exceeded.** Default quota is 5 NAT Gateways per AZ
  per region. Request a quota increase before deploying a multi-VPC
  topology with per-AZ NAT.

- **VPC peering with overlapping CIDRs.** VPC peering does NOT support
  overlapping CIDR ranges. If two VPCs have the same CIDR, they cannot
  peer. Use Transit Gateway with a NAT/translation appliance, or
  re-provision one VPC with a different CIDR.

- **Interface Endpoint in only one AZ.** An Interface Endpoint deployed
  in one AZ only provides AZ-local failover. If that AZ fails, the
  endpoint is unreachable. Deploy Interface Endpoints in all AZs that have
  consumers.

- **VPC Flow Logs to CloudWatch with missing IAM role.** Flow Logs to
  CloudWatch require a dedicated IAM role with `logs:CreateLogGroup`,
  `logs:CreateLogStream`, `logs:PutLogEvents` on the log group ARN. Without
  this role, flow-log creation fails silently (log-status shows NODATA).

- **Gateway Endpoint not added to new route tables.** Gateway Endpoints
  are route-table-based. When you create a new route table in a VPC with
  an existing Gateway Endpoint, the endpoint route is NOT automatically
  added. You must explicitly add the endpoint to the new route table.

- **Ephemeral port range differs by OS.** Linux ephemeral ports are
  32768-60999 (modern kernels) or 1024-65535 (older). Windows is
  49152-65535. NACL rules for return traffic must match the OS of the
  instances. Use 1024-65535 for broadest compatibility.

## Anti-Patterns — NEVER

- NEVER use `192.168.0.0/16` as a VPC CIDR without checking for overlap
  with corporate VPN, home networks, or office WiFi. 192.168.x.x is the
  most common home/office range. Overlap breaks VPN connectivity for
  remote workers.

- NEVER create a single-tier VPC (all public subnets) for production.
  This eliminates all network isolation. Every instance is directly
  internet-reachable. Even with a strict security group, a single SG
  misconfiguration exposes every workload. Always use at least two tiers
  (public + private).

- NEVER put a database in a public subnet. Database subnets must have NO
  internet route (`0.0.0.0/0`). The route table should have only the
  `local` route. This is the defense-in-depth mechanism that prevents
  data exfiltration even if the security group is misconfigured.

- NEVER use the VPC "main" route table for private subnets. The main
  route table is the default and is used by any subnet without an explicit
  association. If you add an IGW route to the main table, every untagged
  subnet becomes public. Always create dedicated route tables per tier
  and associate subnets explicitly.

- NEVER deploy a NAT Gateway in a private subnet. The NAT Gateway must
  be in a public subnet with an IGW route. Deploying it in a private
  subnet fails — the NAT cannot route to the internet.

- NEVER use a single NAT Gateway for a production multi-AZ VPC unless
  you accept the AZ-failure risk. If the NAT Gateway's AZ fails, all
  private-subnet egress fails. For production, use one NAT Gateway per
  AZ and route each private subnet to its AZ-local NAT.

- NEVER open Security Group inbound to `0.0.0.0/0` on ports other than
  80/443. The only resources that should accept traffic from the entire
  internet are public ALBs and NLBs on web ports. App servers, databases,
  and internal services must reference specific security groups.

- NEVER reference CIDR ranges in Security Group rules when a SG reference
  is available. `Source: sg-app-xxx` is more secure and maintainable than
  `Source: 10.0.48.0/20`. CIDR-based rules break when subnet ranges
  change and are harder to audit.

- NEVER skip VPC Flow Logs for a production VPC. Without Flow Logs, you
  cannot diagnose connectivity issues, investigate security incidents, or
  satisfy compliance requirements. The cost ($0.023/GB/month on S3) is
  trivial relative to the forensic value.

- NEVER forget the ephemeral port rule in NACLs. NACLs are stateless —
  outbound HTTPS (port 443) requires allowing inbound return traffic on
  ephemeral ports (1024-65535). Without this rule, all outbound
  connections from the NACL-protected subnet fail silently.

- NEVER skip Gateway Endpoints for S3 and DynamoDB. They are FREE, route
  through the AWS backbone (lower latency than NAT), and save NAT Gateway
  data-processing costs ($0.045/GB). There is no downside to deploying
  them.

- NEVER assume Interface Endpoints work without private DNS. Without
  `--private-dns-enabled`, SDKs that construct URLs from the public DNS
  name route traffic through the NAT Gateway, not the endpoint. Always
  enable private DNS unless you have a specific multi-VPC reason not to.

- NEVER use `enableDnsHostnames: true` without `enableDnsSupport: true`.
  Both are required for DNS resolution within the VPC. Enabling hostnames
  without support produces instances with DNS names that do not resolve.

- NEVER assume IPv6 is private by default. IPv6 addresses are
  internet-routable. A dual-stack VPC without an Egress-Only Internet
  Gateway has IPv6 traffic routed directly to the IGW — private IPv6
  subnets are reachable from the internet. Always deploy EIGW for IPv6
  egress control.

- NEVER create a VPC peering connection to a VPC with an overlapping
  CIDR. VPC peering does NOT support overlapping CIDRs. The peering
  connection will be created but routes cannot be added — traffic will
  not flow. Choose non-overlapping CIDRs at VPC creation time.

- NEVER forget that Transit Gateway has per-attachment cost. For 2 VPCs,
  peering is cheaper ($0 + data transfer). TGW costs ~$33/month for 2
  attachments. Use TGW only when the topology complexity justifies it
  (3+ VPCs, multi-account, VPN/Direct Connect integration).

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-vpc`, `create-subnet`, `create-nat-gateway`, `delete-vpc`),
  the deployer MUST emit:
  `CONFIRM: About to deploy VPC <name> in account <account> region
  <region>. Estimated monthly cost: <$X>. This is a non-reversible
  deployment. Proceed? (yes/no)`

- **CIDR overlap check is MANDATORY.** Before `create-vpc`, run:
  `aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock]' --output table`
  and verify the proposed CIDR does not overlap. Overlapping VPCs cannot
  peer and produce asymmetric routing on Direct Connect.

- **Elastic IP quota check.** NAT Gateways require Elastic IPs. Default
  quota is 5 per region. Request a quota increase before deploying a
  multi-NAT topology:
  `aws service-quotas get-service-quota --service-code ec2 --quota-code L-0263D0A3`

- **Cost estimate.** The deployer MUST emit a monthly cost estimate before
  deployment:
  - NAT Gateways: ~$32/month each × count
  - Interface Endpoints: ~$7/month per AZ per endpoint
  - Flow Logs S3 storage: ~$0.023/GB/month
  - Cross-AZ data transfer: $0.01/GB (if cost-optimized NAT topology)

- **DeleteVpc is DESTRUCTIVE.** Deleting a VPC deletes all subnets,
  route tables, security groups, NACLs (default), and endpoint associations.
  The deployer MUST require confirmation for `delete-vpc` and verify no
  running instances, RDS, or ALBs are in the VPC before proceeding.

- **Tag everything at creation.** Use `--tag-specifications` on every
  `create-*` command. Tags are the primary cost-allocation mechanism. A
  VPC deployed without tags cannot be attributed to a team or project.
  Required tags: `Name`, `Environment`, `Team`, `CostCenter`.

## Expert knowledge: non-obvious VPC behaviors

- **AWS reserves 5 IPs per subnet.** The first 4 addresses and the last
  address are reserved (network address, VPC router, DNS, future use,
  broadcast). A /28 subnet has 16 total IPs but only 11 usable.

- **Subnet CIDR can be larger than needed.** A /20 subnet with 10
  instances costs the same as a /20 with 4,000 instances. AWS does not
  charge per IP — only per resource. Over-provision CIDRs aggressively.

- **Route tables are evaluated by longest-prefix match.** A more specific
  route (e.g., `10.0.1.0/24`) takes precedence over a less specific route
  (`10.0.0.0/16`). This allows "holes" in the routing for specific subnets.

- **Security Group changes take effect within seconds.** Unlike NACLs
  (which require a new network connection to pick up changes), SG changes
  apply to existing connections immediately. However, existing connections
  are NOT retroactively evaluated against new rules.

- **VPC Flow Logs have a delivery delay of 60 seconds to 10 minutes.**
  Flow-log records are aggregated into 10-minute windows. Real-time
  network monitoring requires VPC Traffic Mirroring, not Flow Logs.

- **NAT Gateway supports 100 Gbps by default.** A single NAT Gateway
  handles up to 100,000 concurrent connections. For higher throughput,
  deploy multiple NAT Gateways and use route-table-based load distribution.

- **VPC Endpoints do NOT support all AWS services.** Only services listed
  in the AWS PrivateLink catalog support Interface Endpoints. Check
  availability before planning a fully-private VPC.

- **enableDnsSupport: false breaks VPC endpoints.** Interface Endpoints
  with private DNS rely on the VPC DNS resolver. Disabling DNS support
  breaks endpoint resolution.

- **Transit Gateway route tables are separate from VPC route tables.**
  TGW has its own routing layer. A VPC attached to TGW does NOT
  automatically learn routes to other attached VPCs — the TGW route table
  must explicitly allow the propagation.

- **VPC peering connections are not transitive.** Even with Transit
  Gateway, peering connections established before TGW migration do not
  automatically route through TGW. Migrate peering connections to TGW
  attachments explicitly.

## Deep reference: VPC networking internals

### Packet flow through a VPC

```
Internet → IGW → Public subnet → ALB (SG: public-alb)
                              → App instance (SG: app, NACL: private)
                              → Database (SG: db, NACL: database)
```

Each arrow is a routing and filtering decision:
1. **IGW** routes based on destination IP (public IP → instance, private
   IP → drop for inbound from internet).
2. **Route table** directs traffic to the correct subnet/gateway.
3. **NACL** (stateless) filters by IP/port — evaluated first.
4. **Security Group** (stateful) filters by source/dest — evaluated second.
5. **Instance** receives the packet.

### NAT Gateway data flow

```
Private instance → Route table (0.0.0.0/0 → NAT) → NAT Gateway (public subnet)
  → IGW → Internet → IGW → NAT Gateway → Route table → Private instance
```

The NAT Gateway rewrites the source IP (instance private IP → NAT Elastic
IP). Return traffic hits the NAT's Elastic IP, is de-NAT'd, and routed
back to the instance.

### Cost optimization decision tree

```
Need S3/DynamoDB? → Gateway Endpoint (FREE, always deploy)
Need other AWS services from private subnet? → Interface Endpoint (~$7/AZ/month)
Need non-AWS internet from private subnet? → NAT Gateway (~$32/month)
Production HA required? → 1 NAT per AZ (3 × $32 = $96/month)
Dev/staging? → 1 NAT in AZ-a ($32/month)
```

## Recent AWS features (2024-2026)

- **VPC Block Public Access (2024-2025):** Account-level setting that blocks
  all internet ingress/egress to/from VPCs. Use for air-gapped compliance
  environments. Deployers should verify this setting is not accidentally
  blocking legitimate traffic after deployment.

- **VPC Lattice integration (2024):** Application-networking layer that
  sits above VPC routing. Deployers should understand that Lattice does
  not replace VPC subnets/route tables — it adds a service-discovery and
  load-balancing layer on top.

- **Internet Gateway Flow Logs (2024-2025):** Flow Logs can now capture
  traffic at the IGW level, not just VPC/subnet/ENI. This provides
  visibility into traffic entering/leaving the VPC before NAT processing.

- **VPC Resource Navigator (2025-2026):** Visual topology tool in the VPC
  console showing resource relationships. Useful for auditing, but does
  not replace CLI verification commands.

- **Subnet CIDR Reservation (2024-2025):** Reserve CIDR ranges within a
  subnet for specific purposes (e.g., Lambda VPC deployments, prefix-based
  routing). Useful for predictable IP allocation in large VPCs.

## Domain

AWS CloudOps / VPC Networking & Infrastructure Provisioning.

## AWS documentation

- **Amazon VPC User Guide** — https://docs.aws.amazon.com/vpc/latest/userguide/
- **VPC Security** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security.html
- **VPC CIDR Blocks** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html
- **VPC Endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **NAT Gateways** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- **Transit Gateway** — https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html
- **VPC Peering** — https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html
- **AWS CLI EC2 Reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
