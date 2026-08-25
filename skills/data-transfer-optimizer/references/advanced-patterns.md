# Advanced Patterns (load on demand) — Data Transfer Optimizer

Quick-start and Mindset framing, Step 0 non-obvious behaviours, data-quality
short-circuits, TGW cost-reduction patterns, break-even formulas, and Recent
AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Quick start (moved from SKILL.md)



- **NAT Gateway is the #1 surprise bill.** Every GB processed
  through a NAT Gateway costs $0.045 — regardless of whether the
  traffic was S3, DynamoDB, or general internet. The cheapest fix:
  VPC Gateway Endpoints for S3 and DynamoDB (FREE, route traffic
  through AWS private network instead of NAT). On a 10TB/month NAT
  workload, this saves $450/month.
- **Cross-AZ transfer is a per-GB cost.** $0.01/GB each direction
  ($0.02/GB round trip). The fix is to keep the processing in the
  same AZ as the data source: pin the RDS consumer to the primary
  AZ, pin the S3-processing Lambda to the bucket's region, run the
  EC2 worker in the AZ where the data lives.
- **Internet egress is the largest single line item.** $0.09/GB
  for the first 10TB, tiered lower after. CloudFront changes the
  math: S3-to-CloudFront egress is free in most regions, and
  viewers pay for the edge-to-browser hop (bundled in their ISP
  cost). On a 5TB/month egress workload going to global viewers,
  CloudFront saves 30-60% even after CloudFront's own charges.
- **VPC peering is free for intra-region traffic.** Transit
  Gateway charges $0.02/GB. For ≤ 4 VPCs in the same region,
  peering is almost always cheaper. Reserve TGW for complex
  topologies, cross-region connectivity, or central network
  firewall inspection.
- **RDS Multi-AZ is free for Aurora, $0.01/GB for RDS.** When
  choosing between Aurora and RDS for a Multi-AZ workload, the
  cross-AZ transfer differential shows up on the bill.



## Mindset (moved from SKILL.md)



AWS data transfer is the most overlooked cost dimension because it
appears as a flat per-GB charge on the bill, but the actual pattern
of transfer — which AZ, which region, which network path — is
hidden in the CUR USAGE_TYPE granularity. The cheapest data transfer
is the transfer that never happens. The second-cheapest is the
transfer that stays inside a single AZ. The third-cheapest is the
transfer that stays inside a single region. Every dimension that
escalates (cross-AZ → cross-region → internet egress) is a
multiplier on the per-GB rate.



## Philosophy — four behaviours (moved from SKILL.md)



Four behaviours separate a senior network/FinOps engineer from a
generalist:

- **NAT Gateway is a default-route trap.** Operators launch a VPC
  Wizard template with public + private subnets; the private subnet
  routes 0.0.0.0/0 through the NAT Gateway. Every byte the private
  subnet sends to the internet (including to AWS services like S3
  and DynamoDB) goes through the NAT Gateway and pays $0.045/GB.
  VPC Gateway Endpoints for S3 and DynamoDB route that traffic
  through AWS's private network instead — for FREE. Operators who
  don't know about Gateway Endpoints discover the $0.045/GB charge
  only when the bill hits 4-5 figures.
- **Cross-AZ is a per-hop charge, not a flat fee.** A workload that
  reads from RDS in us-east-1a and processes in us-east-1b pays
  $0.01/GB each direction. Pin the consumer to the primary AZ and
  the cost goes to zero. This requires knowing the data source's
  AZ, which requires actually reading the RDS configuration rather
  than assuming "Multi-AZ = same everywhere."
- **Internet egress is unavoidable for user-facing workloads, but
  the rate is negotiable.** Direct Connect offers per-GB pricing
  that beats internet egress at scale (typically 1-10Gbps committed
  ports). CloudFront shifts the egress cost to the CDN layer where
  pricing is tiered differently. Savings Plans for Data Transfer
  (available since 2023) lock in discounts on committed egress
  spend. Always evaluate the alternatives before paying the
  default $0.09/GB.
- **VPC topology decisions have recurring per-GB consequences.**
  Transit Gateway is convenient (centralized routing, scalable) but
  charges $0.02/GB on every byte that traverses it. VPC peering is
  free for intra-region but limited to 1:1 connections (full mesh
  for N VPCs = N×(N-1)/2 peerings). The break-even depends on VPC
  count AND traffic volume — not on a single dimension.



## Pre-flight data-quality short-circuits and conflicting-data arbitration (moved from SKILL.md)



| Condition | Effect on optimization |
|---|---|
| CUR / Cost Explorer access denied | **NEED_MORE_INFO** for cost estimates: cloud-team must grant `ce:GetCostAndUsage`. Topology dimensions still analyzable but savings unquantified. |
| Observation window < 14 days | **NEED_MORE_INFO**: workload may reflect atypical load (deploy week, incident response). Minimum 14 days; 30 days preferred. |
| Account is part of AWS Organizations with consolidated billing | Filter Cost Explorer by linked account; the consolidated view hides per-account patterns. |
| VPC topology missing from input | **NEED_MORE_INFO** for VPC topology dimension. NAT, internet egress, RDS dimensions still analyzable from Cost Explorer. |
| Cross-region replication hidden under S3 USAGE_TYPE | Cross-reference with `aws s3api get-bucket-replication` to identify which buckets are incurring cross-region charges. |
| CloudFront egress already in CloudFront service (not EC2) | Confirm CloudFront optimization is in scope; if yes, route to cloudfront-cost-optimizer for the CloudFront-specific dimensions. |

### Conflicting-data arbitration

When Cost Explorer and CloudWatch metrics disagree (e.g., NAT
Gateway BytesOut metric shows 8TB but Cost Explorer shows 10GB-
processed), trust Cost Explorer for billing, trust CloudWatch for
the operational pattern. Cost Explorer includes the $0.045/GB
processing charge; BytesOut captures only the egress volume. Always
sanity-check projected savings against the actual CUR line item.



## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)



These are the operational gotchas a senior network FinOps engineer
knows from incident experience — each one routes a recommendation
away from the obvious choice:

- **NAT Gateway charges on ALL traffic, including AWS-service
  traffic.** A private subnet EC2 instance fetching from S3, DynamoDB,
  SQS, SNS, Kinesis, or any AWS service routes through the NAT
  Gateway by default. Each of these has a VPC endpoint alternative:
  S3 and DynamoDB have FREE Gateway Endpoints; other services have
  Interface Endpoints ($0.01/GB) that still save vs NAT ($0.045/GB).

- **NAT Gateway has an hourly charge PLUS the per-GB charge.**
  $0.045/hour per NAT Gateway + $0.045/GB. A 3-AZ HA NAT setup
  costs $0.135/hour × 730 = $98.55/month just in hourly charges,
  even at zero throughput. For dev/test or low-traffic workloads,
  a single-AZ NAT or no NAT (with VPC endpoints for AWS services)
  may be cheaper.

- **Gateway Endpoints are route-table entries, not ENIs.** A VPC
  Gateway Endpoint for S3 modifies the VPC route table to redirect
  S3 traffic through AWS's private network. No ENI, no hourly
  charge, no per-GB charge. The endpoint is invisible to the
  application — it just works. The catch: Gateway Endpoints are
  regional (cannot extend to on-premises via Direct Connect). Use
  Interface Endpoints for hybrid scenarios.

- **Interface Endpoints cost $0.01/GB AND $0.05/hour per AZ.** A
  3-AZ Interface Endpoint for SQS costs $0.05 × 3 × 730 = $109.50/
  month base + $0.01/GB. Break-even vs NAT ($0.045/GB): $109.50 /
  ($0.045 - $0.01) = 3,128 GB/month. Below 3TB/month on that
  service, NAT is cheaper; above 3TB/month, Interface Endpoint is
  cheaper.

- **Cross-AZ transfer charges both directions.** A workload reading
  1GB from a cross-AZ source pays $0.01 (source AZ → consumer AZ).
  If the workload writes 1GB back, that's another $0.01 (consumer
  AZ → source AZ). Total: $0.02/GB round trip. The single-direction
  view undercounts by 2x.

- **VPC peering is FREE for intra-region traffic.** No per-GB
  charge, no hourly charge. The only cost is the VPC peering
  connection's absence of centralized routing. Full mesh for N
  VPCs requires N×(N-1)/2 connections; managing 10+ peerings is
  operationally painful, which is where Transit Gateway earns its
  $0.02/GB.

- **Transit Gateway charges per-attachment AND per-GB.** $0.05/
  hour per attachment (~$36.50/month per VPC attached) PLUS
  $0.02/GB inbound and outbound. For a hub-and-spoke with 5 VPCs
  in one region, that's 5 × $36.50 = $182.50/month base + per-GB
  charges. Compare to 5 peerings (free) — but only if the topology
  is mesh-compatible.

- **Cross-region VPC peering has per-GB charges; intra-region does
  not.** Cross-region peering: $0.01-0.02/GB depending on regions.
  Cross-region TGW attachment: similar per-GB rate. The rule:
  cross-region always pays per-GB regardless of technology; intra-
  region is the leverage point.

- **S3 cross-region replication is a cost, not a saving.** CRR
  replicates every object to a destination region, paying cross-
  region transfer on every byte. Useful for DR/compliance;
  counterproductive as a "latency optimization" (use CloudFront
  for global content delivery instead).

- **CloudFront changes the egress math.** Without CloudFront, S3
  egress to viewers pays $0.09/GB. With CloudFront, S3-to-CloudFront
  egress is FREE in most regions. You pay CloudFront's per-GB rate
  to viewers ($0.085/GB for first 10TB at PriceClass_100), which is
  less than the S3 direct-egress rate. On a 5TB/month global-viewer
  workload, CloudFront saves $25/month on the egress alone, before
  any cache-hit savings.

- **RDS Multi-AZ replication has different cost models.** Aurora's
  Multi-AZ replication is built into the storage layer (free data
  transfer). RDS for MySQL/PostgreSQL Multi-AZ uses synchronous
  block-level replication that incurs $0.01/GB for the replication
  traffic. On a high-write workload, the cross-AZ transfer alone
  can be significant.

- **Direct Connect breaks even at high committed volume.** A 1Gbps
  DX port costs ~$220/month (varies by region). At $0.02/GB
  outbound (DX rate, vs $0.09/GB internet egress), break-even is
  $220 / ($0.09 - $0.02) = 3,143 GB/month. Above 3TB/month steady-
  state egress, DX is cheaper. Below, internet egress is cheaper.

- **Data Transfer Savings Plans (2023+) discount committed egress.**
  A 1- or 3-year commit to a monthly egress spend (any region, any
  destination) yields 5-25% discount depending on commit term.
  Stack with CloudFront and Direct Connect where applicable.

- **Egress from CloudFront does NOT include origin-to-CloudFront
  transfer from S3.** S3-to-CloudFront is free in most regions;
  EC2/ALB-to-CloudFront pays $0.02/GB same-region. Use S3 origins
  for content that CloudFront will cache.

- **Same-AZ traffic is free in most cases.** EC2-to-EC2 in the
  same AZ using private IPs: free. EC2-to-RDS in the same AZ: free.
  EC2-to-S3 in the same region via Gateway Endpoint: free. The
  optimization lever is to KEEP traffic same-AZ where possible.

- **`describe-` API responses are the source of truth for topology.**
  Don't rely on console diagrams or hand-drawn architecture — they
  drift. Always query the API:
  ```bash
  # Identify NAT Gateway routes
  for vpc in $(aws ec2 describe-vpcs --query 'Vpcs[].VpcId' --output text); do
    for rtb in $(aws ec2 describe-route-tables --filters Name=vpc-id,Values=$vpc \
      --query 'RouteTables[].RouteTableId' --output text); do
      aws ec2 describe-route-tables --route-table-ids $rtb --output json | \
        jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock == "0.0.0.0/0") |
            {route_table: .RouteTableId, target: .NatGatewayId // .TransitGatewayId // .GatewayId,
             destination: "0.0.0.0/0"}'
    done
  done
  ```

  **Decision gates when reviewing topology:**

  | Topology field | Gate | Why it matters |
  |---|---|---|
  | Route table 0.0.0.0/0 → NatGatewayId | Check if Gateway Endpoints can intercept S3/DynamoDB traffic. | $0.045/GB charge on every byte NAT-processed. |
  | Route table 0.0.0.0/0 → TransitGatewayId | Compare per-GB cost vs VPC peering for the same topology. | TGW is $0.02/GB; peering is free intra-region. |
  | VPC Endpoint type = Gateway for S3/DynamoDB | Confirm coverage in every VPC with private subnets. | Missing Gateway Endpoint = NAT Gateway charges. |
  | VPC Endpoint type = Interface for service X | Check per-GB break-even vs NAT. | $0.05/h/AZ + $0.01/GB vs NAT $0.045/GB. |
  | Cross-region VPC peering present | Check if cross-region traffic warrants a TGW cross-region attachment instead. | Per-GB rates similar; TGW simplifies routing. |
  | RDS MultiAZ=true on non-Aurora | Check cross-AZ transfer charges on high-write workloads. | $0.01/GB cross-AZ replication. |
  | Aurora Multi-AZ (cluster mode) | Free replication — no cross-AZ transfer charge. | Already optimal. |

  If ANY field is missing from the response, the topology is
  incomplete. Re-query the specific resource before emitting the
  recommendation.



## Step 3 — cost classification profiles (moved from SKILL.md)



Classify the cost profile to guide optimization emphasis:

| Cost profile | Indicators | Emphasis |
|---|---|---|
| NAT-heavy bill | NatGateway-Bytes is > 30% of total | Gateway Endpoints (S3, DynamoDB), Interface Endpoints for high-volume services |
| Internet-egress heavy | DataTransfer-Out-Bytes > 30% | CloudFront, S3 Multi-Region Access Points, Direct Connect |
| Cross-AZ heavy | DataTransfer-Regional-Bytes > 20% | AZ-pinning of consumers to data sources |
| Cross-region heavy | DataTransfer-Egress-Cross-Region > 20% | Regional concentration, S3 MRAP, cross-region architecture review |
| TGW-heavy bill | TransitGateway-Bytes cost is significant | VPC peering for ≤ 4 intra-region VPCs |
| RDS-heavy bill | RDS-DataTransfer is significant | Migrate RDS Multi-AZ → Aurora |
| Mixed (no single dimension > 30%) | Even distribution | Apply all dimensions in parallel |



## Step 6 — internet egress decision matrix (moved from SKILL.md)



**Decision matrix:**

| Egress pattern | Recommendation | Savings |
|---|---|---|
| S3 egress to global viewers | CloudFront in front of S3 (S3-to-CF free in most regions) | Up to $0.005/GB after CloudFront charges; plus cache savings |
| S3 egress to known regions | S3 Multi-Region Access Point (routes to nearest bucket) | Cross-region transfer savings if multi-region buckets exist |
| EC2/ALB egress to global viewers | CloudFront in front of origin (origin-to-CF $0.02/GB same-region) | Variable; depends on cache hit ratio |
| EC2 cross-region to another AWS region | VPC peering (cheaper than internet for region-pair) | $0.01-0.02 vs $0.09 |
| On-premises data sync | Direct Connect (committed bandwidth) | DX $0.02/GB vs internet $0.09/GB above 3TB/month |
| Steady-state > 50TB/month egress | Direct Connect 10Gbps port + Data Transfer Savings Plan | DX per-GB + Savings Plan discount 5-25% |
| Spot / burst egress (inconsistent) | Internet egress (no commit) | None — already optimal |
| Third-party API responses | Internet egress (unavoidable) | None |



## Step 7 — VPC topology decision matrix (moved from SKILL.md)



**Decision matrix:**

| Topology | VPC count (intra-region) | Traffic volume | Recommendation |
|---|---|---|---|
| Hub-and-spoke, intra-region | ≤ 4 VPCs | Any | VPC peering (free) |
| Hub-and-spoke, intra-region | 5-10 VPCs | Low | VPC peering (full mesh = N(N-1)/2 connections) |
| Hub-and-spoke, intra-region | 5-10 VPCs | High | Transit Gateway (simpler ops, $0.02/GB) |
| Hub-and-spoke, intra-region | > 10 VPCs | Any | Transit Gateway (peering ops infeasible) |
| Hub-and-spoke, cross-region | Any | Any | Transit Gateway (cross-region peering has per-GB charges too; TGW simplifies routing) |
| Mesh, intra-region | ≤ 4 VPCs | Any | VPC peering (full mesh = 6 connections for 4 VPCs) |
| Mesh, cross-region | Any | Any | Transit Gateway with cross-region attachments |
| Centralized egress (all VPCs → 1 egress VPC) | Any | Any | Transit Gateway (centralized routing is the value prop) |
| Centralized inspection (all traffic → firewall VPC) | Any | Any | Transit Gateway (requires centralized routing) |



## Step 7 — TGW cost-reduction patterns (moved from SKILL.md)



**TGW cost-reduction patterns:**

If TGW is already deployed and the cost is high:
1. Identify low-traffic attachments and convert to peering (single
   pair of VPCs only).
2. Use TGW route tables to centralize only the egress VPC, peer the
   rest directly.
3. Reduce cross-AZ TGW traffic by pinning workloads to a single AZ
   per VPC (reduces TGW-AZ hop count).



## Step 8 — RDS/Aurora decision matrix (moved from SKILL.md)



**Decision matrix:**

| Database setup | Data transfer charge | Recommendation |
|---|---|---|
| Aurora (MySQL/PostgreSQL) Multi-AZ | Free (storage-layer replication) | Already optimal |
| RDS for MySQL/PostgreSQL Multi-AZ | $0.01/GB cross-AZ | High-write: migrate to Aurora. Low-write: accept the charge. |
| RDS read replica same-region | $0.01/GB cross-AZ (if replica in different AZ) | Pin replica to same AZ as primary (defeats HA purpose). Or accept. |
| RDS read replica cross-region | Cross-region transfer ($0.02-0.09/GB) | Only for DR/compliance. Use Aurora Global Database for cross-region. |
| Aurora Global Database | Cross-region storage replication (billed per Aurora pricing) | Already optimized for cross-region DR. |
| Aurora Serverless v2 | Free Multi-AZ (built-in) | Already optimal |
| Self-managed DB on EC2 | Standard EC2 cross-AZ/region charges | Same-AZ deployment for primary-replica pairs. |



## Step 9 — Direct Connect break-even calculation (moved from SKILL.md)



**Break-even calculation:**

```
DX_port_monthly_cost = port_rate (varies by speed: 50Mbps ~$60,
                                  1Gbps ~$220, 10Gbps ~$2000)
DX_per_GB = $0.02 (varies by region pair)

Internet_per_GB = $0.09 (first 10TB), $0.085 (10-40TB),
                  $0.070 (40-100TB), $0.05 (>150TB)

break_even_GB = DX_port_cost / (internet_rate - DX_per_GB)
```



## Step 11 — final verdict aggregation (moved from SKILL.md)



The verdict is the worst-case (most-actionable) finding across all
seven dimensions:

- If ANY dimension recommends a change (NAT, cross-AZ, cross-region,
  internet egress, VPC topology, RDS, Direct Connect), verdict is
  **OPPORTUNITY_FOUND**.
- If all dimensions pass AND Data Transfer Savings Plan has been
  evaluated (whether adopted or rejected with rationale), verdict
  is **OPTIMIZED** (post-remediation) or **ALREADY_OPTIMAL** (no
  change needed).
- If data is insufficient (no CUR, no topology), verdict is
  **NEED_MORE_INFO** for the affected dimensions.



## NAT Gateway break-even formula (moved from SKILL.md)



Step 0 references "NAT Gateway is the #1 surprise bill." Use this
formula to size the optimization:

```
nat_monthly_cost =
  (nat_GB_processed × $0.045) +
  (nat_count × $0.045 × 730)

gateway_endpoint_monthly_cost = $0  # S3, DynamoDB
interface_endpoint_monthly_cost =
  (endpoint_count × AZ_count × $0.05 × 730) +
  (endpoint_GB × $0.01)

break_even_GB_for_interface_endpoint =
  (endpoint_count × AZ_count × $0.05 × 730) /
  ($0.045 − $0.01)
  = (endpoint_count × AZ_count × 36.5) / 0.035
  ≈ 1042 × endpoint_count × AZ_count GB/month
```

| Service | Endpoint type | Hourly | Per-GB | Break-even vs NAT |
|---|---|---|---|---|
| S3 | Gateway | FREE | FREE | Always (Gateway always cheaper) |
| DynamoDB | Gateway | FREE | FREE | Always |
| SQS, SNS, Kinesis | Interface | $0.05/AZ/h | $0.01 | ~3,128 GB/month per 3-AZ endpoint |
| Secrets Manager, STS | Interface | $0.05/AZ/h | $0.01 | Rarely breaks even (low traffic) |
| Private endpoint for partner service | Interface (PrivateLink) | $0.05/AZ/h | $0.01 | Depends on traffic volume |



## Recent AWS features (2024-2026) (moved from SKILL.md)



- **Data Transfer Savings Plans (2023-2024):** 1- or 3-year commit
  on data transfer spend, 5-25% discount depending on term. Stack
  with CloudFront and Direct Connect where applicable.
- **S3 Multi-Region Access Points (2022, broadened 2024):** Route
  S3 requests to the nearest bucket. Use for global workloads
  with multi-region buckets. Per-request routing.
- **Aurora Global Database (2020, broadened 2023+):** Cross-region
  storage replication without per-GB cross-region transfer (billed
  via Aurora storage pricing instead). Use for cross-region DR.
- **VPC Endpoint Policies for S3 (2024):** Granular IAM-style
  policies on Gateway Endpoints. Use to scope down bucket access
  at the network layer.
- **AWS Verified Access (2023-2024):** Identity-aware proxy that
  replaces VPN for some access patterns. Cost-shifts from VPN
  per-hour to per-request pricing.
- **CloudFront KeyValueStore (2023-2024):** Key-value data store
  for CloudFront Functions, reducing Lambda@Edge dependency for
  data lookup patterns.
- **Transit Gateway Network Manager (2024):** Centralized
  monitoring for TGW topologies. Cost-neutral but improves
  operational visibility into per-attachment traffic.
- **Cross-region VPC peering with IPv6 (2024-2025):** IPv6 support
  for cross-region peering. Previously required DX or TGW.


