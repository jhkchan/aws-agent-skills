# Advanced Patterns — VPC Network Deployer

Deep reference content moved verbatim from `vpc-network-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Mindset — three facts that make VPC provisioning different

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

## Step 0 — expert knowledge: non-obvious VPC behaviors that change the plan

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

## Why database subnets have no internet route (Step 2)

**Why database subnets have no internet route:** Database tier security
relies on defense-in-depth. The security group allows only app-tier
ingress. The NACL adds explicit IP-range filtering. The route table has
NO `0.0.0.0/0` route — even if an instance is compromised and the SG is
modified, the database cannot reach the internet for data exfiltration.

## Two-tier model (Step 2)

**Two-tier model (acceptable for non-production):**
- Public tier (ALB, NAT)
- Private tier (everything else, including databases grouped with apps)

## Internet Gateway, EIGW, and deployment commands (Step 3)

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

## NAT Gateway deployment commands (Step 4)

**Deployment:**
```
aws ec2 allocate-address --domain vpc  # Elastic IP for NAT
aws ec2 create-nat-gateway --subnet-id subnet-public-a --allocation-id eipalloc-xxx
# Wait for NAT Gateway to become Available (1-3 minutes)
aws ec2 wait nat-gateway-available --nat-gateway-id nat-xxx
```

## NAT anti-pattern — never a private subnet (Step 4)

**Anti-pattern:** NEVER deploy a NAT Gateway in a private subnet. The NAT
Gateway MUST be in a public subnet with an IGW route — otherwise it
cannot route traffic to the internet and deployment fails.

## Why one private route table per AZ (Step 5)

**Why one private route table per AZ (HA topology):** Each AZ's private
subnet routes to its own NAT Gateway. This avoids cross-AZ data transfer
charges ($0.01/GB each direction) and ensures AZ-local egress. With a
single route table, all AZs would route to one NAT Gateway, defeating the
HA topology.

## Standard security group layout (Step 6)

**Standard security group layout:**

| SG | Inbound | Outbound |
|---|---|---|
| `public-alb-sg` | 443/tcp from 0.0.0.0/0, 80/tcp from 0.0.0.0/0 (redirect) | All to app-sg |
| `app-sg` | 8080/tcp from public-alb-sg, 8080/tcp from internal-alb-sg | 443/tcp to db-sg, all to NAT (for package updates) |
| `db-sg` | 5432/tcp from app-sg (PostgreSQL), 6379/tcp from app-sg (Redis) | None (default deny) |
| `bastion-sg` | 22/tcp from corporate CIDR | 22/tcp to app-sg, 5432/tcp to db-sg (for admin tunnelling) |

## NACL use cases and scope limits (Step 7)

- **Defense-in-depth IP filtering** (e.g., block known-bad CIDRs).
- **Blocking specific traffic patterns** (e.g., block all SSH from
  non-corporate ranges, even if the SG allows it).
- **Compliance requirements** that mandate stateless filtering.

**Do NOT use NACLs as the primary security control.** SGs are stateful,
easier to manage, and support referencing by name. NACLs are IP/CIDR-only
and require managing ephemeral port ranges for return traffic.

## Standard NACL layout and ephemeral ports (Step 7)

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

## Why VPC Flow Logs (Step 8)

- **Security forensics** (identifying the source of an attack after the fact).
- **Compliance** (most regulations require network-level logging).
- **Troubleshooting** (diagnosing connectivity issues).
- **Anomaly detection** (detecting data exfiltration patterns).

## Flow log destination options and recommendation (Step 8)

**Destination options:**

| Destination | Cost | Retention | Query capability |
|---|---|---|---|
| S3 bucket | $0.023/GB/month (standard) | Lifecycle rules (e.g., 90d standard, 1yr Glacier) | Athena queries |
| CloudWatch Logs | $0.50/GB ingested + $0.03/GB stored | 1-3650 days | CloudWatch Logs Insights |
| Kinesis Data Firehose | $0.029/GB | Depends on destination | Real-time processing |

**Recommendation:** S3 destination with Athena for querying. Cheapest for
long retention. Use CloudWatch Logs only if you need real-time alerts on
flow-log patterns.

## Flow logs deployment command (Step 8)

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

## Flow logs configuration requirements (Step 8)

**Configuration requirements:**
- `traffic-type: ALL` (not just ACCEPT or REJECT — both directions matter).
- Log format MUST include `srcaddr`, `dstaddr`, `srcport`, `dstport`,
  `protocol`, `action`, `pkt-srcaddr`, `pkt-dstaddr` at minimum.
- S3 bucket MUST have a bucket policy allowing `logs.amazonaws.com` to
  write `PutObject`.
- Retention via S3 lifecycle rule: 90 days standard → Glacier → expire at
  1 year (or longer per compliance).

## DNS required VPC attributes commands (Step 10)

**Required VPC attributes:**
```
aws ec2 modify-vpc-attribute --vpc-id vpc-xxx --enable-dns-hostnames
aws ec2 modify-vpc-attribute --vpc-id vpc-xxx --enable-dns-support
```

## DNS both-true requirements and DHCP option set commands (Step 10)

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

## AmazonProvidedDNS explanation (Step 10)

`AmazonProvidedDNS` (at 169.254.169.253) is the Route 53 Resolver. It
resolves Route 53 private hosted zones and provides recursive DNS for
the VPC. Use the default unless you have a specific reason to use custom
DNS servers.

## IPv6 association commands (Step 11)

**Deployment:**
```
aws ec2 associate-ipv6-cidr-block --vpc-id vpc-xxx --amazon-provided-ipv6-cidr-block
# AWS assigns a /56 to the VPC
aws ec2 associate-subnet-cidr-block --subnet-id subnet-xxx --ipv6-cidr-block 2600:1f18:xxxx:xxxx::/64
```

## Multi-VPC connectivity options — peering vs Transit Gateway detail (Step 12)

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

## Edge-case handling catalog

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

## Expert knowledge — non-obvious VPC behaviors

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

## Deep reference — VPC networking internals

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
