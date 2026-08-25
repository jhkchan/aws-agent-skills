---
name: vpc-network-deployer
description: 'Provisions production-grade VPCs with secure, well-architected network infrastructure: RFC 1918 CIDR planning with growth headroom, multi-AZ public/private/database subnet tiers, NAT Gateway HA placement (1-per-AZ vs single for cost), Internet Gateway vs Egress-Only Gateway (IPv6), least-privilege route table design (public→IGW, private→NAT, database→ local-only), Security Groups that reference by name not CIDR, stateless NACLs for defense-in-depth, VPC Flow Logs with long retention, Gateway (S3/DynamoDB — free) vs Interface VPC Endpoints (private DNS, per-AZ cost), DHCP option sets and Route 53 Resolver DNS resolution, VPC peering vs Transit Gateway for multi-VPC, and IPv6 dual-stack considerations. Emits a deterministic deployment plan with a READY_TO_DEPLOY checklist and network architecture validation. Use when provisioning a new VPC, designing multi-tier subnet layouts, planning CIDR ranges to avoid overlaps, configuring NAT Gateway topology, setting up VPC endpoints for private connectivity, or...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws ec2 create-vpc, create-subnet, create-route-table, create-nat-gateway, create-security-group, create-flow-logs, create-vpc-endpoint, and describe-* verification commands (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new VPC for production, designing a multi-tier subnet layout (public/private/database), planning CIDR ranges to avoid overlaps with existing networks, selecting NAT Gateway topology for HA vs cost, configuring VPC endpoints for private S3/DynamoDB connectivity, setting up VPC Flow Logs for security forensics, designing route tables for least-privilege traffic flow, hardening VPC security groups and NACLs, or planning IPv6 dual-stack support.
  activation_triggers: create a new VPC, provision VPC network, plan CIDR ranges for VPC, design multi-AZ subnets, NAT gateway HA topology, VPC endpoint configuration, VPC flow logs setup, security group and NACL design, VPC route table design, IPv6 dual-stack VPC, Transit Gateway vs VPC peering
  invocation_schema: 'Input shape (one of): (a) a deployment specification including region, AZ count, CIDR range, tier requirements (public/private/database), NAT strategy (HA vs cost), endpoint requirements, and flow-log destination; (b) a partial spec for interactive refinement (e.g., "3-AZ VPC in us-east-1 with /16 CIDR, private-only"); (c) an existing VPC ID for architecture review against the well-architected checklist. Output shape: { VPC_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: VPC, CIDR planning, RFC 1918, subnet design, multi-AZ, public subnet, private subnet, database subnet, NAT Gateway, Internet Gateway, Egress-Only Gateway, route table, Security Group, NACL, VPC Flow Logs, VPC Endpoint, Gateway Endpoint, Interface Endpoint, PrivateLink, DHCP options, Route 53 Resolver, VPC peering, Transit Gateway, IPv6 dual-stack, network architecture
  tags: vpc, networking, deploy, subnets, nat-gateway, route-tables, security-groups, nacl, flow-logs, vpc-endpoints, ipv6, transit-gateway
---

# VPC Network Deployer

## Mindset

**One-line takeaway:** a production VPC is not "a /16 with subnets" — it is
a **routing graph** where every route-table entry, every security-group
rule, and every NACL rule is an explicit security decision. The CIDR block
is the least interesting part; the **subnet tiering, NAT topology, and
endpoint strategy** determine blast radius, cost, and failover behavior.

Three facts make VPC provisioning different from "draw a network diagram":

Mindset — three facts that make VPC provisioning different — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Live-account pre-flight checks (deployment spec gate) — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

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

PREREQUISITES_MISSING output example (incomplete deployment spec) — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious VPC behaviors that change the plan

These behaviors are easy to misjudge without operational VPC experience.
Each changes the architecture if ignored:

Step 0 — expert knowledge: non-obvious VPC behaviors that change the plan — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 1: CIDR planning

RFC 1918 private ranges (Step 1) — moved verbatim.
Full detail: [CIDR planning guide](references/cidr-planning-guide.md).

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

Sizing rationale — why /16 and /20 per tier (Step 1) — moved verbatim.
Full detail: [CIDR planning guide](references/cidr-planning-guide.md).

### Step 2: Subnet tier design

**Three-tier model (recommended for production):**

| Tier | Purpose | Route table | Internet egress |
|---|---|---|---|
| Public | ALB, NAT Gateway, Bastion | 0.0.0.0/0 → IGW | Direct via IGW |
| Private | Application workloads (ECS, EKS, EC2, Lambda-VPC) | 0.0.0.0/0 → NAT (AZ-local) | NAT Gateway |
| Database | RDS, ElastiCache, Redshift | Local only | No internet egress |

Why database subnets have no internet route (Step 2); Two-tier model (Step 2) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

**One-tier model (NEVER for production):**
- All resources in public subnets. No isolation. Only acceptable for
  throwaway sandboxes or demos. Flag as PREREQUISITES_MISSING.

### Step 3: Internet Gateway and public egress

Internet Gateway, EIGW, and deployment commands (Step 3) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

NAT Gateway deployment commands (Step 4); NAT anti-pattern — never a private subnet (Step 4) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Why one private route table per AZ (Step 5) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Standard security group layout (Step 6) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 7: Network ACLs (NACLs)

NACLs are **stateless** — each connection requires an explicit inbound
AND outbound rule. They are evaluated before Security Groups. Use NACLs
for:

NACL use cases and scope limits (Step 7); Standard NACL layout and ephemeral ports (Step 7) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 8: VPC Flow Logs

VPC Flow Logs capture metadata about IP traffic to/from network interfaces
in the VPC. They are essential for:

Why VPC Flow Logs (Step 8); Flow log destination options and recommendation (Step 8); Flow logs deployment command (Step 8); Flow logs configuration requirements (Step 8) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Interface endpoint service table (Step 9); Interface endpoint deployment and private DNS (Step 9) — moved verbatim.
Full detail: [VPC endpoint types](references/vpc-endpoint-types.md).

### Step 10: DNS resolution

DNS required VPC attributes commands (Step 10); DNS both-true requirements and DHCP option set commands (Step 10); AmazonProvidedDNS explanation (Step 10) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

### Step 11: IPv6 dual-stack considerations

IPv6 is optional but recommended for public-facing workloads (ALB, NAT64).

IPv6 association commands (Step 11) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

**Key differences from IPv4:**
- IPv6 addresses are **internet-routable by default**. There is no NAT for
  IPv6. Private IPv6 subnets need an Egress-Only Internet Gateway.
- Security Groups and NACLs filter IPv6 traffic independently. A rule
  allowing `0.0.0.0/0` does NOT allow IPv6 — add `::/0` explicitly.
- NAT Gateway does NOT process IPv6 traffic. IPv6 egress uses EIGW.
- Route 53 Resolver supports IPv6 (AAAA records) with AmazonProvidedDNS.

### Step 12: Multi-VPC connectivity

Multi-VPC connectivity options — peering vs Transit Gateway detail (Step 12) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Verification commands (run after deployment) — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

## Edge-case handling

Edge-case handling catalog — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

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

Pre-flight safety checks (run before any deployment CLI) — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

## Expert knowledge: non-obvious VPC behaviors

Expert knowledge — non-obvious VPC behaviors — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## Deep reference: VPC networking internals

Deep reference — VPC networking internals — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) — PREREQUISITES_MISSING output example; full worked example kept in SKILL.md
- [Diagnostic commands](references/diagnostic-commands.md) — live pre-flight checks, post-deployment verification commands, pre-flight safety checks
- [Advanced patterns](references/advanced-patterns.md) — Step 0 expert knowledge, per-step rationale and standard layouts, edge cases, expert behaviors, deep reference, recent features
- [CIDR planning guide](references/cidr-planning-guide.md) — RFC 1918 ranges, sizing rationale
- [VPC endpoint types](references/vpc-endpoint-types.md) — interface endpoint service table, deployment and private DNS

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
