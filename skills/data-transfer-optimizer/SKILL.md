---
name: data-transfer-optimizer
description: Optimizes AWS data transfer costs across seven dimensions — cross-AZ transfer ($0.01/GB each direction; pin consumers to data-source AZ), cross-region transfer ($0.02-0.09/GB; use CloudFront
  for global viewers, VPC peering for intra-region, S3 CRR only for DR), internet egress ($0.09/GB first 10TB; optimize via CloudFront with free S3-to-CF egress, S3 Multi-Region Access Points, Direct
  Connect), NAT Gateway data processing ($0.045/GB; route S3/DynamoDB via FREE VPC Gateway Endpoints), VPC peering (free intra-region) vs Transit Gateway ($0.02/GB), RDS Multi-AZ ($0.01/GB) vs Aurora
  (free replication), and Direct Connect break-even math. Emits OPPORTUNITY_FOUND with per-dimension savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when triaging surprise data-transfer bills, auditing CUR
  USAGE_TYPE line items, deciding peering vs TGW, or sizing Direct Connect.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation-document classification works from pasted Cost and Usage Report (CUR) line items and
  VPC/topology diagrams. Live-account optimization uses aws ce get-cost-and-usage (filtered by USAGE_TYPE for data-transfer dimensions), aws ec2 describe-vpc-peering-connections, describe -transit-gateways,
  describe-nat-gateways, describe-vpc-endpoints, aws s3api get-bucket-location, aws rds describe-db-instances, and aws directconnect describe-connections (AWS CLI v2, SSO or key-based credentials).
keywords:
- data transfer
- cross-AZ
- cross-region
- NAT Gateway
- VPC peering
- Transit Gateway
- internet egress
- S3 Transfer Acceleration
- Direct Connect
- VPC Gateway Endpoint
- VPC Interface Endpoint
- PrivateLink
- S3 Multi-Region Access Point
- RDS Multi-AZ
- Aurora replication
- Cost and Usage Report
- CUR
- FinOps
- surprise bill
tags:
- data-transfer
- networking
- cost-optimization
- finops
- vpc
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: FinOps
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimizing AWS data transfer costs, triaging a surprise data-transfer bill, auditing CUR data-transfer line items, deciding between VPC peering and Transit Gateway, evaluating NAT Gateway
    alternatives (Gateway/Interface endpoints), sizing a Direct Connect commitment, evaluating S3 Multi-Region Access Points, or building a monthly data-transfer cost projection.
  when_not_to_use: CloudFront-specific cost optimization (use cloudfront-cost-optimizer for Price Class, cache policy, Origin Shield), EC2 instance rightsizing (use ec2-rightsizing-optimizer), S3 storage
    lifecycle optimization (use s3-lifecycle-optimizer), RDS instance rightsizing (use rds-cost-optimizer), NAT Gateway high-availability troubleshooting (use nat-gateway-troubleshooter). This skill focuses
    on data-transfer cost optimization across the seven networking dimensions, not on instance/storage rightsizing or CloudFront-specific decisions.
  activation_triggers:
  - reduce data transfer cost
  - AWS surprise bill
  - cross-AZ data transfer
  - cross-region data transfer
  - NAT Gateway cost
  - VPC peering vs Transit Gateway
  - internet egress cost
  - Direct Connect break-even
  - VPC Gateway Endpoint
  - VPC Interface Endpoint
  - S3 Multi-Region Access Point
  - CUR data transfer audit
  - FinOps data transfer review
  - RDS Multi-AZ data transfer
  - Aurora cross-region replication cost
  - Transit Gateway cost
  invocation_schema: 'Input: either (a) an AWS account context with access to Cost Explorer / CUR, (b) a pasted Cost and Usage Report extract filtered to data-transfer USAGE_TYPEs, OR (c) a network topology
    description (VPCs, regions, AZs, NAT Gateways, VPC peering connections, Transit Gateway, Direct Connect, S3 buckets, RDS instances). Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION
    / ESTIMATED_SAVINGS / MIGRATION_STEPS block per account (or per top-cost dimension), where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION lists the per-dimension actions
    (cross-AZ, cross-region, internet egress, NAT Gateway, VPC topology, RDS, Direct Connect).'
  invocation_example: "# Minimal valid input (offline CUR classification):\nAccount: 123456789012\nRegion: us-east-1 primary; us-west-2 secondary\nMonthly data transfer costs (Cost Explorer, last 30 days):\n\
    \  - NAT Gateway DataProcessed: 12,000 GB × $0.045 = $540\n  - EC2 cross-AZ data transfer: 8,000 GB × $0.02 = $160\n  - S3 cross-region replication: 1,500 GB × $0.02 = $30\n  - CloudFront egress (already\
    \ optimized)\nVPC topology:\n  - VPC-A in us-east-1 (3 AZs; primary app)\n  - VPC-B in us-east-1 (3 AZs; analytics)\n  - VPC peering: A↔B (intra-region, free)\n  - Transit Gateway: not in use\nNAT Gateway:\
    \ 1 per AZ in VPC-A (3 total)\nVPC endpoints: only S3 Gateway Endpoint in VPC-A\nWorkload context: microservices in VPC-A pulling from S3 and\nDynamoDB; analytics EMR cluster in VPC-B reading same S3\n\
    buckets and writing cross-AZ back to VPC-A database.\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# Data Transfer Optimizer

## Quick start

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

## Mindset

AWS data transfer is the most overlooked cost dimension because it
appears as a flat per-GB charge on the bill, but the actual pattern
of transfer — which AZ, which region, which network path — is
hidden in the CUR USAGE_TYPE granularity. The cheapest data transfer
is the transfer that never happens. The second-cheapest is the
transfer that stays inside a single AZ. The third-cheapest is the
transfer that stays inside a single region. Every dimension that
escalates (cross-AZ → cross-region → internet egress) is a
multiplier on the per-GB rate.

## Philosophy

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

## Quick reference — verdict thresholds

| Observation (30-day CUR window) | Verdict | Recommendation |
|---|---|---|
| S3/DynamoDB traffic flowing through NAT Gateway | **OPPORTUNITY_FOUND** (NAT Gateway) | Step 5 — VPC Gateway Endpoints (FREE) |
| Workload reading from cross-AZ RDS primary | **OPPORTUNITY_FOUND** (cross-AZ) | Step 4 — pin consumer to primary AZ |
| EC2 internet egress > 10TB/month going to global viewers | **OPPORTUNITY_FOUND** (internet egress) | Step 6 — CloudFront in front of origin |
| Transit Gateway on ≤ 4 intra-region VPCs with mesh traffic | **OPPORTUNITY_FOUND** (VPC topology) | Step 7 — migrate to VPC peering |
| Interface endpoints on a high-volume service (e.g., SQS, SNS) routed through NAT | **OPPORTUNITY_FOUND** (NAT Gateway) | Step 5 — add Interface Endpoint (saves $0.035/GB delta) |
| Cross-region VPC peering for hub-and-spoke with 6+ VPCs | **OPPORTUNITY_FOUND** (VPC topology) | Step 7 — Transit Gateway with cross-region attachments |
| RDS Multi-AZ on a high-write workload (vs Aurora) | **OPPORTUNITY_FOUND** (RDS data transfer) | Step 8 — migrate to Aurora (Multi-AZ replication free) |
| Internet egress > 50TB/month steady-state | **OPPORTUNITY_FOUND** (Direct Connect) | Step 9 — Direct Connect committed port |
| All seven dimensions at cost-optimal config | **ALREADY_OPTIMAL** | None — continue monitoring |

See the ordered steps for edge cases (hybrid NAT + endpoints,
microservice fan-out, S3 cross-region replication for DR,
CloudFront cost crossover).

## Pre-flight: data gate (run before any optimization decision)

Data transfer optimization requires three data sources: Cost
Explorer / CUR for billing, VPC topology for routing decisions, and
service-level configurations (RDS, S3, NAT Gateway) for per-resource
context.

### Required data sources

```bash
# 1. Pull Cost Explorer data-transfer line items (last 30 days)
START=$(date -u -d '-30 days' +%F)
END=$(date -u +%F)

aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":[
    "Amazon Elastic Compute Cloud - Compute",
    "AmazonEC2",
    "Amazon Simple Storage Service",
    "Amazon Relational Database Service",
    "Amazon ElastiCache",
    "Amazon Redshift",
    "Amazon DynamoDB",
    "Amazon Nat Gateway",
    "Amazon Virtual Private Cloud",
    "Amazon Route 53",
    "AWS Direct Connect"
  ]}}' \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json > ce-data-transfer.json

# 2. Pull VPC topology
aws ec2 describe-nat-gateways --output json > nat-gateways.json
aws ec2 describe-vpc-peering-connections --output json > vpc-peerings.json
aws ec2 describe-transit-gateways --output json > transit-gateways.json
aws ec2 describe-vpc-endpoints --output json > vpc-endpoints.json

# 3. Pull service configurations (top-cost resources)
aws rds describe-db-instances --output json > rds-instances.json
aws s3api list-buckets --output json | \
  jq '[.Buckets[] | {name, region: "us-east-1"}]' > s3-buckets.json
# For each bucket, get actual region:
for bucket in $(jq -r '.[].name' s3-buckets.json); do
  region=$(aws s3api get-bucket-location --bucket $bucket \
    --query 'LocationConstraint' --output text)
  echo "$bucket,$region"
done > bucket-regions.csv

# 4. Pull Direct Connect (if in use)
aws directconnect describe-connections --output json > dx-connections.json
```

### Data-quality short-circuits

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

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

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

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
CUR line items, emit NEED_MORE_INFO for the cost-quantification
dimension:

```text
TARGET: <account or topology-description>
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer / CUR data is required to quantify per-
  dimension savings. Without USAGE_TYPE granularity, the seven
  dimensions can be analyzed qualitatively but the savings estimate
  cannot be computed.
RECOMMENDATION:
  1. Grant the auditor role `ce:GetCostAndUsage` permission.
  2. Or, paste the top 10 data-transfer USAGE_TYPE line items from
     the last 30 days of CUR.
  3. Re-evaluate with cost data to enable savings estimates.
ESTIMATED_SAVINGS: $0 (cannot quantify without CUR data)
MIGRATION_STEPS:
  - IAM policy addition:
    {
      "Effect": "Allow",
      "Action": ["ce:GetCostAndUsage", "ce:GetDimensionValues"],
      "Resource": "*"
    }
  - Or, CUR Athena query:
    SELECT line_item_usage_type, SUM(line_item_usage_amount) AS usage,
           SUM(line_item_unblended_cost) AS cost
    FROM cur_table
    WHERE line_item_product_service LIKE '%Data Transfer%'
      AND line_item_usage_start_date >= date_add('day', -30, now())
    GROUP BY 1 ORDER BY 3 DESC LIMIT 10;
```

If VPC topology is incomplete, emit a partial verdict covering the
dimensions that can be analyzed from CUR alone (NAT Gateway,
internet egress, RDS) and flag the topology-dependent dimensions
(VPC peering vs TGW, cross-AZ optimization) as NEED_MORE_INFO.

### Step 2: Cost Explorer reconciliation

```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-30 days' +%F),End=$(date -u +%F) \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE_GROUP","Values":[
    "EC2: Data Transfer - Internet (Out)",
    "EC2: Data Transfer - Region (Out)",
    "EC2: Data Transfer - Availability Zone (Out)",
    "EC2: Egress - Cross Region",
    "S3: Cross-Region Replication",
    "CloudFront: Egress",
    "RDS: Data Transfer",
    "VPC: NAT Gateway",
    "VPC: Transit Gateway"
  ]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber),
    usage_qty: (.Metrics.UsageQuantity.Amount | tonumber)}'
```

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `NatGateway-Bytes` | NAT Gateway | $0.045/GB processed |
| `DataTransfer-Regional-Bytes` | Cross-AZ | $0.01/GB each direction |
| `DataTransfer-Out-Bytes` | Internet egress | $0.09/GB first 10TB |
| `DataTransfer-Egress-Cross-Region` | Cross-region | $0.02-0.09/GB by region pair |
| `S3-Cross-Region-Replication-Bytes` | S3 CRR | Cross-region transfer + S3 requests |
| `RDS-DataTransfer` | RDS Multi-AZ | $0.01/GB for non-Aurora Multi-AZ |
| `TransitGateway-Bytes` | TGW | $0.02/GB inbound + outbound |

If a single USAGE_TYPE accounts for > 50% of the total data-transfer
cost, deep-dive that dimension first. The Pareto principle applies
heavily — typically NAT Gateway or internet egress dominates.

### Step 3: Cost classification

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

### Step 4: Cross-AZ transfer optimization

Cross-AZ is $0.01/GB each direction ($0.02/GB round trip). The fix
is to keep the consumer in the same AZ as the data source.

**Decision matrix:**

| Source | Consumer pattern | Recommendation | Savings |
|---|---|---|---|
| RDS Multi-AZ primary in us-east-1a | EC2 worker spread across all AZs | Pin worker to primary AZ via subnet routing | $0.02/GB on cross-AZ traffic |
| ElastiCache primary in us-east-1b | Lambda consumer (random AZ) | Pin Lambda to us-east-1b subnet | $0.01/GB on read traffic |
| ALB in us-east-1 (multi-AZ) | EC2 targets in all AZs | Expected — ALB routes by load. No optimization. | None |
| EFS mount target per AZ | EC2 consumer in another AZ | Add EFS mount target in consumer's AZ | $0.01/GB on EFS traffic |
| Aurora cluster (Multi-AZ) | EC2 in any AZ | Aurora's reader instances can be AZ-pinned | $0 — Aurora replication is free |
| S3 bucket (regional) | Any consumer | S3 is regional; AZ-pinning N/A | None |

**Detecting cross-AZ waste via CloudWatch:**

```bash
# For each EC2 instance, get network throughput by peer-AZ
# (Requires VPC Flow Logs enabled)
aws ec2 describe-flow-logs --output json

# Athena query on VPC Flow Logs to identify cross-AZ traffic
SELECT
  concat(split_part(srcaddr, '.', 1), '.',
         split_part(srcaddr, '.', 2), '.x.x') AS src_subnet,
  concat(split_part(dstaddr, '.', 1), '.',
         split_part(dstaddr, '.', 2), '.x.x') AS dst_subnet,
  SUM(bytes) AS total_bytes
FROM vpc_flow_logs
WHERE date >= date_add('day', -7, now())
  AND action = 'ACCEPT'
GROUP BY 1, 2
ORDER BY 3 DESC LIMIT 20;
```

**Worked AZ-pinning example:**

A worker fleet in VPC-A reads 100GB/day from an RDS for PostgreSQL
primary in us-east-1a. Workers are spread across 3 AZs by ASG; ~67%
of traffic is cross-AZ. Cross-AZ cost: 67GB/day × $0.02/GB × 30 =
$40.20/month. Pin workers to us-east-1a (subnet selection in the
ASG launch template): cross-AZ cost drops to $0/month. Trade-off:
if us-east-1a fails, the workers fail. Mitigate by adding a
standby in us-east-1b that activates only on primary failover.

### Step 5: NAT Gateway optimization

The biggest single lever for surprise bills.

```bash
# Identify NAT Gateways and their throughput
aws ec2 describe-nat-gateways --output json | \
  jq '.NatGateways[] | {id: .NatGatewayId, state: .State,
    az: .SubnetId, public_ip: .NatGatewayAddresses[0].PublicIp}'

# Get NAT Gateway traffic (CloudWatch)
for nat in $(aws ec2 describe-nat-gateways --query 'NatGateways[].NatGatewayId' --output text); do
  aws cloudwatch get-metric-statistics \
    --namespace AWS/NATGateway \
    --metric-name BytesOutToDestination \
    --dimensions Name=NatGatewayId,Value=$nat \
    --start-time $(date -u -d '-30 days' +%FT%TZ) \
    --end-time $(date -u +%FT%TZ) \
    --period 86400 --statistics Sum \
    --output json
done
```

**Decision matrix:**

| NAT Gateway traffic source | Recommendation | Savings |
|---|---|---|
| S3 traffic (high volume) | Add VPC Gateway Endpoint for S3 (FREE) | $0.045/GB on all S3 traffic |
| DynamoDB traffic | Add VPC Gateway Endpoint for DynamoDB (FREE) | $0.045/GB on all DynamoDB traffic |
| SQS / SNS / Kinesis high volume | Add Interface Endpoint (break-even ~3TB/month) | $0.035/GB delta above 3TB |
| Other AWS services (Secrets Manager, STS, etc.) | Add Interface Endpoints (low traffic, small savings) | $0.035/GB delta; may not break even on hourly charges |
| General internet traffic (third-party APIs) | Keep NAT Gateway | None — no endpoint alternative |
| Egress-only NAT for IPv6 | Use Egress-Only Internet Gateway (free) | $0.045/GB + $0.045/hour |
| Dev/test VPC with no AWS-service traffic | Replace NAT with VPC endpoints + EC2 Instance Connect Endpoint | Eliminates NAT hourly charge |

**Worked Gateway Endpoint savings:**

VPC with 5TB/month S3 traffic flowing through NAT Gateway.
- Current cost: 5,000GB × $0.045 = $225/month + hourly charges
- Add S3 Gateway Endpoint: route table redirects S3 traffic
- New cost: $0 (Gateway Endpoint is free; S3 request charges apply
  but are unaffected by endpoint choice)
- Monthly savings: $225

**Worked Interface Endpoint break-even:**

VPC with 2TB/month SQS traffic flowing through NAT Gateway.
- Current cost: 2,000GB × $0.045 = $90/month
- Add SQS Interface Endpoint (3-AZ): $0.05 × 3 × 730 = $109.50/month
  base + 2,000GB × $0.01 = $20 = $129.50/month
- Interface Endpoint is MORE expensive at 2TB/month (break-even at
  ~3.1TB/month). Recommend: keep NAT Gateway for now; revisit if
  SQS traffic exceeds 3TB/month.

### Step 6: Internet egress optimization

Internet egress is $0.09/GB first 10TB, tiered lower after. The
cheapest alternative is to reduce the egress through a different
network path.

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

**Worked CloudFront crossover:**

5TB/month S3 egress to global viewers.
- Current (direct S3 egress): 5,000GB × $0.09 = $450/month
- With CloudFront: S3-to-CF free + CF-to-viewer 5,000GB × $0.085
  (first 10TB at PriceClass_100) = $425/month
- Direct savings on egress: $25/month
- Additional cache savings: if CacheHitRate > 90%, only 500GB needs
  to come from S3 → $0 S3-to-CF + $425 CF-to-viewer = $425/month.
  If CacheHitRate = 100% on cached content, viewers fetch from edge
  without origin touch: $425/month flat.
- Total monthly cost: $425 + CloudFront request charges (~$0.225/M
  × 5M requests = $1.125) ≈ $426/month
- Net savings vs direct egress: $24/month + user-perceived latency
  improvement. **CloudFront's real win for internet egress is at
  higher volumes and with global viewers where APAC-tier billing
  kicks in (without CloudFront, APAC viewers pay $0.12-0.14/GB).**

**Worked Direct Connect crossover:**

50TB/month egress to on-premises or distant viewers (no CloudFront
applicable, e.g., bulk data transfer to a partner).
- Current (internet egress): 50,000GB × tiered internet rate.
  First 10TB × $0.09 + next 40TB × $0.085 + ... ≈ $4,400/month
- With Direct Connect 10Gbps port (~$2,000/month port fee + $0.02/
  GB outbound): $2,000 + 50,000GB × $0.02 = $3,000/month
- Net savings: $1,400/month + 1-2Gbps committed throughput (vs
  best-effort internet)
- Add Data Transfer Savings Plan (1-yr commit on the $1,000/month
  DX egress spend): 10% discount → another $100/month savings.

### Step 7: VPC topology optimization

VPC peering (free intra-region) vs Transit Gateway ($0.02/GB).

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

**Worked peering-vs-TGW example:**

5 VPCs in us-east-1, full mesh, each pair exchanging 100GB/month.
- Transit Gateway: 5 attachments × $0.05/h × 730h = $182.50/month
  base + 10 pairs × 100GB × $0.02/GB (in+out, $0.04/GB round trip)
  = $40/month in per-GB → $222.50/month total
- VPC peering: 10 peering connections (5 × 4 / 2) × free = $0/month
- Net savings: $222.50/month. Operational cost: managing 10
  peerings (vs 1 TGW). Recommend: peering if team has automation
  for peering management; TGW if ops burden exceeds $222/month.

**TGW cost-reduction patterns:**

If TGW is already deployed and the cost is high:
1. Identify low-traffic attachments and convert to peering (single
   pair of VPCs only).
2. Use TGW route tables to centralize only the egress VPC, peer the
   rest directly.
3. Reduce cross-AZ TGW traffic by pinning workloads to a single AZ
   per VPC (reduces TGW-AZ hop count).

### Step 8: RDS/Aurora data transfer optimization

RDS Multi-AZ replication has different cost models.

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

**Worked Aurora migration math:**

RDS for PostgreSQL Multi-AZ on a high-write workload (5TB/month
write volume).
- Current cross-AZ replication cost: 5,000GB × $0.01 = $50/month
- Aurora equivalent: $0 cross-AZ transfer (storage-layer replication)
- Aurora instance pricing is typically similar to RDS for the same
  vCPU/memory; may be slightly higher for compute but offset by
  storage/replication savings.
- Net data-transfer savings: $50/month
- Plus: Aurora's faster failover, no replication lag, 15-reader
  limit (vs 5 for RDS). Migration effort: 1-2 weeks for app
  compatibility testing.

### Step 9: Direct Connect evaluation

For high-volume steady-state egress, Direct Connect beats internet
egress on per-GB rate.

**Break-even calculation:**

```
DX_port_monthly_cost = port_rate (varies by speed: 50Mbps ~$60,
                                  1Gbps ~$220, 10Gbps ~$2000)
DX_per_GB = $0.02 (varies by region pair)

Internet_per_GB = $0.09 (first 10TB), $0.085 (10-40TB),
                  $0.070 (40-100TB), $0.05 (>150TB)

break_even_GB = DX_port_cost / (internet_rate - DX_per_GB)
```

| Port speed | Port cost/month | Break-even vs $0.09/GB | Break-even vs $0.05/GB |
|---|---|---|---|
| 50 Mbps | ~$60 | ~857 GB/month | ~2,000 GB/month |
| 1 Gbps | ~$220 | ~3,143 GB/month | ~7,333 GB/month |
| 10 Gbps | ~$2,000 | ~28,571 GB/month | ~66,667 GB/month |
| 100 Gbps | ~$20,000 | ~285,714 GB/month | ~666,667 GB/month |

If steady-state egress exceeds the break-even, recommend DX. If
below, internet egress is cheaper.

### Step 10: Impact estimation

Sum the per-dimension savings into a projected monthly bill.

```
current_monthly_data_transfer =
  (nat_GB × $0.045) + (nat_hourly_total) +
  (cross_az_GB × $0.02) +
  (internet_egress_GB × tiered_rate) +
  (cross_region_GB × $0.02-0.09) +
  (tgw_GB × $0.02) + (tgw_attachment_hourly_total) +
  (rds_multiaz_GB × $0.01) +
  (interface_endpoint_hourly_total + interface_endpoint_GB × $0.01)

projected_monthly = same formula with optimized values
monthly_savings = current − projected
```

**Pricing notes (us-east-1 baseline, 2026):**

- Cross-AZ: $0.01/GB each direction
- Cross-region: $0.02/GB (within North America) to $0.09/GB (to
  South America or Africa)
- Internet egress: $0.09/GB (first 10TB), $0.085 (10-40TB),
  $0.07 (40-100TB), $0.05 (>150TB)
- NAT Gateway: $0.045/GB + $0.045/hour
- VPC Gateway Endpoint (S3, DynamoDB): FREE
- VPC Interface Endpoint: $0.05/hour per AZ + $0.01/GB
- Transit Gateway: $0.05/hour per attachment + $0.02/GB (in + out)
- VPC peering (intra-region): FREE
- VPC peering (cross-region): $0.01-0.02/GB
- Direct Connect: port fee + $0.02/GB outbound
- RDS Multi-AZ (non-Aurora): $0.01/GB
- Aurora Multi-AZ: FREE
- S3 cross-region replication: cross-region transfer + S3 PUT
  requests

For per-region pricing precision, always check
`https://aws.amazon.com/ec2/pricing/on-demand/` (Data Transfer
section) for the current matrix.

### Step 11: Final verdict

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

## Output format

```text
TARGET: <account-id or topology-description>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: NAT=<GB and $>, cross-AZ=<GB and $>,
    cross-region=<GB and $>, internet-egress=<GB and $>,
    VPC topology=<peering/TGW>, RDS=<Multi-AZ setup>,
    DX=<in use or not>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (NAT Gateway): $<amount>
  Monthly (cross-AZ): $<amount>
  Monthly (cross-region): $<amount>
  Monthly (internet egress): $<amount>
  Monthly (VPC topology): $<amount>
  Monthly (RDS): $<amount>
  Monthly (Direct Connect): $<amount>
  Annual total: $<amount>
  Assumptions: <list (pricing region, 730h/month, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> in <account>. Proceed? (yes/no)"
```

### Worked example — multi-dimension optimization

```text
TARGET: account 123456789012
VERDICT: OPPORTUNITY_FOUND
REASON: Cost Explorer shows NAT Gateway as 42% of data transfer
  cost ($540/month on 12TB S3 traffic through NAT), cross-AZ
  transfer on RDS-primary workloads at $160/month, and no VPC
  Gateway Endpoints deployed. Three dimensions have actionable
  opportunities; combined projected savings $725/month,
  $8,700/year.
RECOMMENDATION:
  Current:
    NAT Gateway: 12,000 GB × $0.045 = $540/month + $98.55 hourly
      (3-AZ HA NAT setup)
    Cross-AZ transfer: 8,000 GB × $0.02 = $160/month (RDS primary
      in 1a, workers spread across 3 AZs)
    Internet egress: 1,200 GB × $0.09 = $108/month (modest, no
      optimization needed)
    Cross-region: minimal ($30/month S3 replication to eu-west-1
      for DR — keep, justified)
    VPC topology: VPC peering (free, intra-region) — already optimal
    RDS Multi-AZ: PostgreSQL on r6i.2xlarge, high write
    DX: not in use (egress volume too low to justify)
  Proposed:
    - NAT: add VPC Gateway Endpoints for S3 and DynamoDB → routes
      AWS-service traffic off NAT. Cuts NAT data processing by
      ~13,000 GB (S3+DynamoDB) → saves $585/month on per-GB.
      Hourly charges remain ($98.55/month for general internet
      egress).
    - Cross-AZ: pin worker ASG subnet routing to RDS primary AZ
      (us-east-1a) → cuts cross-AZ by 90% → saves $144/month.
      Trade-off: lose multi-AZ HA for workers (mitigate with
      standby in 1b activated on primary failover).
    - Internet egress: keep as-is ($108/month is below CloudFront
      or DX break-even).
    - Cross-region S3 CRR: keep (DR/compliance justification).
    - VPC topology: keep (peering is already free).
    - RDS: evaluate Aurora migration for the high-write primary
      → would save $50/month on Multi-AZ transfer. Defer to next
      quarterly review (migration effort is 2 weeks).
    - DX: not justified at current egress (<2TB/month steady).
  Confidence: HIGH — CUR line items confirm NAT composition; VPC
    topology confirms no Gateway Endpoints deployed; RDS confirms
    Multi-AZ non-Aurora.
ESTIMATED_SAVINGS:
  Monthly (NAT Gateway data processing): $585  (13,000GB × $0.045
    rerouted to Gateway Endpoints; hourly charges remain)
  Monthly (cross-AZ): $144  (8,000GB × 90% × $0.02 eliminated
    by AZ-pinning)
  Monthly (cross-region): $0  (S3 CRR retained for DR)
  Monthly (internet egress): $0  (below optimization threshold)
  Monthly (VPC topology): $0  (peering already free)
  Monthly (RDS): $0  (deferred to next review)
  Monthly (Direct Connect): $0  (not justified)
  Annual total: $8,748
  Assumptions: us-east-1 pricing, 730h/month, Gateway Endpoints
    fully route S3/DynamoDB traffic off NAT, AZ-pinning maintains
    RDS connectivity on primary failover via standby ASG.
MIGRATION_STEPS:
  1. Snapshot current route tables for rollback:
     for rtb in $(aws ec2 describe-route-tables --filters
       Name=vpc-id,Values=$VPC_A --query 'RouteTables[].RouteTableId'
       --output text); do
       aws ec2 describe-route-tables --route-table-ids $rtb \
         --output json > rtb-backup-$rtb-$(date +%s).json
     done
  2. Create VPC Gateway Endpoints (Step 5):
     aws ec2 create-vpc-endpoint --vpc-id $VPC_A \
       --service-name com.amazonaws.us-east-1.s3 \
       --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
       --vpc-endpoint-type Gateway
     aws ec2 create-vpc-endpoint --vpc-id $VPC_A \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
       --vpc-endpoint-type Gateway
     (No app changes required — Gateway Endpoints intercept S3 and
     DynamoDB DNS automatically.)
  3. Pin worker ASG to us-east-1a subnet:
     Update launch template subnet filter to us-east-1a only.
     Verify workers still reach RDS primary.
     Add a standby ASG in us-east-1b (min=0, desired=0; scale on
     RDS failover alarm).
  4. Validate CloudWatch NAT Gateway BytesOutToDestination drops
     by ~13TB/month over the next 7 days:
     aws cloudwatch get-metric-statistics --namespace AWS/NATGateway
       --metric-name BytesOutToDestination ...
  5. Validate cross-AZ DataTransfer-Regional-Bytes drops by ~90%
     in Cost Explorer over the next billing cycle.
CONFIRM: Before each state-changing CLI, emit and await:
  "CONFIRM: About to <action> in account 123456789012. Proceed?
   (yes/no)"
  Stage changes one dimension at a time per the spec; never batch
  NAT Gateway endpoint creation + ASG subnet change in the same
  maintenance window.
```

### Worked example — already optimal

```text
TARGET: account 987654321098
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  S3 and DynamoDB Gateway Endpoints in all VPCs with private
  subnets; workers AZ-pinned to Aurora cluster readers; CloudFront
  in front of S3 for global viewers; cross-region traffic limited
  to Aurora Global Database (DR-justified); VPC peering for the
  3 intra-region VPCs (free); Aurora Multi-AZ replication (free);
  Direct Connect 1Gbps for the 5TB/month on-prem sync (above
  break-even).
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CUR confirms 30-day spending pattern is
    stable; topology audit confirms Gateway Endpoints deployed in
    every VPC; CloudFront CacheHitRate > 90%.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CUR review.
  - Re-evaluate Direct Connect upgrade to 10Gbps if on-prem sync
    exceeds 20TB/month steady-state (12 months out, per growth
    forecast).
```

### Worked example — NEED_MORE_INFO (no CUR access)

```text
TARGET: account 111122223333
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer / CUR access denied for the auditor role.
  Topology dimensions (VPC peering, Gateway Endpoints) can be
  analyzed qualitatively but the per-dimension savings cannot be
  quantified without USAGE_TYPE granularity.
RECOMMENDATION:
  Current: topology partially analyzed
    NAT Gateway: 3 deployed across 3 AZs (assume significant
      traffic but volume unknown)
    VPC Gateway Endpoints: S3 only in VPC-A; missing DynamoDB and
      missing entirely in VPC-B
    Cross-AZ: unknown volume (no flow logs analyzed)
    VPC topology: peering for 3 VPCs (free, optimal)
  Proposed: partial (pending CUR data)
    - Add DynamoDB Gateway Endpoint in VPC-A and both Gateway
      Endpoints in VPC-B (high-confidence optimization, savings
      unquantified)
    - Other dimensions pending CUR analysis
  Confidence: MEDIUM — topology analysis confirms some
    optimizations; savings magnitude unknown.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): unknown pending CUR
  Qualitative: high confidence that NAT Gateway savings alone
    exceed $200/month based on the typical 3-AZ HA NAT workload.
MIGRATION_STEPS:
  1. Grant the auditor role CUR access:
     {
       "Effect": "Allow",
       "Action": ["ce:GetCostAndUsage", "ce:GetDimensionValues",
                  "ce:GetTags"],
       "Resource": "*"
     }
  2. Or, run this Athena query on the CUR and paste results:
     SELECT line_item_usage_type,
            SUM(line_item_usage_amount) AS usage,
            SUM(line_item_unblended_cost) AS cost
     FROM cur_table
     WHERE line_item_usage_type LIKE '%DataTransfer%'
        OR line_item_usage_type LIKE '%NatGateway%'
        OR line_item_usage_type LIKE '%TransitGateway%'
       AND line_item_usage_start_date >= date_add('day', -30, now())
     GROUP BY 1 ORDER BY 3 DESC LIMIT 20;
  3. Re-evaluate with CUR data to enable per-dimension savings
     estimates.
CONFIRM: Apply the high-confidence topology optimizations
  (Gateway Endpoints in VPC-B) only after operator approval. Do
  NOT quantify savings without CUR data.
```

## Verdict semantics — reconciling the verdict_shape

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one of the seven dimensions has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CUR line items confirm the new pattern lands within target bands. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND Data Transfer Savings Plan evaluated. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed for one or more dimensions: CUR access denied, topology missing, observation window < 14 days. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## NAT Gateway break-even formula (concrete)

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

## Error handling — CLI and data-source failures

The workflow depends on three live data sources (Cost Explorer, VPC
API, service-specific APIs). Each can fail independently.

### Cost Explorer failures

| Failure mode | Detection | Handling |
|---|---|---|
| `AccessDeniedException` for `ce:GetCostAndUsage` | Exit code non-zero | Role lacks billing permissions. Proceed without CE; flag the gap. Operator grants `ce:GetCostAndUsage` and re-runs. |
| CE returns no data-transfer line items | Empty Results | Account has no data transfer in window, OR CE API is filtering by linked account. Check `--filter` for linked-account scope. |
| CE cost disagrees with CloudWatch metric volume | Cross-source mismatch | Trust CE for billing, CloudWatch for operations. Delta is typically free tier, taxes, or SERVICE-level rounding. |
| CE returns very high cost on a service you don't recognize | Unknown USAGE_TYPE | Cross-reference USAGE_TYPE with AWS pricing docs. Some charges (e.g., CloudFront under "AmazonCloudFront" service) hide data transfer inside the line item. |

### VPC API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-nat-gateways` returns empty | Empty list | No NAT Gateways in region. Confirm by checking other regions. |
| `describe-vpc-endpoints` returns Gateway Endpoints only | No Interface Endpoints | Either no Interface Endpoints deployed, or scope mismatch. Default scope is `Cluster` (regional); check both. |
| `describe-transit-gateways` returns empty | Empty list | No TGW in region. Skip TGW dimension. |
| `describe-vpc-peering-connections` returns deleted peerings | `Code == deleted` | Filter to `active` status only. Deleted peerings don't affect current cost. |
| `AccessDeniedException` for `ec2:Describe*` | Exit code non-zero | Role lacks EC2 read permissions. Add `ec2:Describe*` to the policy. |

### Service-specific API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `rds describe-db-instances` returns empty | Empty list | No RDS in region. Skip RDS dimension. |
| `directconnect describe-connections` returns empty | Empty list | No DX in use. Skip DX dimension. |
| `s3api get-bucket-location` errors with `NoSuchBucket` | API error | Bucket was deleted between list and location query. Skip that bucket. |
| `s3api get-bucket-replication` returns empty config | `Replication == {}` | No CRR configured. Skip CRR dimension. |
| CloudWatch NAT Gateway metric returns no datapoints | Empty Datapoints | NAT Gateway is < 24h old, or had no traffic. Re-query later. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling,
network), retry up to 3 times with exponential backoff before
treating that dimension as NEED_MORE_INFO. For persistent failures
(IAM denial, missing service), emit the appropriate gating verdict
for that dimension and proceed with the remaining dimensions.

## Anti-Patterns — NEVER do these things

- NEVER recommend VPC Gateway Endpoints without checking the route
  table. Gateway Endpoints modify the route table; if the route
  table has a more specific route for S3 (e.g., on-premises via DX),
  the endpoint won't intercept the traffic.

- NEVER recommend replacing NAT Gateway with VPC Endpoints as a
  blanket optimization. Some traffic MUST go through NAT (third-
  party APIs, general internet egress). Endpoints only handle AWS
  service traffic.

- NEVER recommend AZ-pinning without a failover plan. Pinning
  workers to the primary AZ eliminates cross-AZ cost but creates a
  single-AZ dependency. Document the standby/failover strategy
  before recommending.

- NEVER recommend Transit Gateway purely for "operational
  simplicity" on a low-VPC topology. TGW charges $0.02/GB + hourly
  per attachment; for ≤ 4 intra-region VPCs, peering is almost
  always cheaper and the ops burden is manageable.

- NEVER recommend VPC peering for > 10 VPCs without automation in
  place. Full mesh on 10 VPCs is 45 peerings; manual management is
  error-prone. TGW earns its premium at this scale.

- NEVER recommend Direct Connect without confirming steady-state
  egress exceeds the break-even. DX is a 1- or 3-year commit;
  committing below break-even locks in overpayment.

- NEVER recommend S3 Cross-Region Replication for cost savings.
  CRR adds cross-region transfer on every byte. It's a DR/
  compliance feature, not a cost optimization.

- NEVER recommend CloudFront for non-cacheable high-volume egress
  (e.g., database sync, log streaming to a partner). CloudFront's
  value is cache-hit savings; without cacheability, it just adds
  cost.

- NEVER recommend Interface Endpoints for low-traffic services
  (Secrets Manager, STS) without doing the break-even math. The
  $0.05/h/AZ hourly charges often exceed the per-GB savings.

- NEVER recommend Aurora migration solely for data-transfer
  savings. The cross-AZ transfer savings on RDS Multi-AZ ($0.01/GB)
  is rarely the dominant factor vs the migration effort. Trigger
  Aurora migration for other reasons (HA, reader scale, storage
  auto-scaling); treat the data-transfer savings as a bonus.

- NEVER recommend Data Transfer Savings Plan commitments beyond
  steady-state. The 1- or 3-year commit locks in the discount only
  on the committed amount; over-committing pays for unused discount.

- NEVER assume intra-region traffic is free. Intra-region VPC
  peering is free, but intra-region EC2-to-EC2 across AZs still
  pays $0.01/GB. AZ-pinning is the lever, not just "same region."

- NEVER assume cross-AZ is symmetric. A read from cross-AZ pays
  $0.01/GB; a write back pays another $0.01/GB. Round-trip cost is
  $0.02/GB, not $0.01/GB.

- NEVER recommend removing a NAT Gateway without confirming that
  VPC Endpoints cover all AWS service traffic in the VPC. Removing
  NAT breaks any remaining AWS-service or internet-bound traffic.

- NEVER recommend Direct Connect without confirming there's a
  failover path. DX is a single physical connection (or LAG);
  internet egress or a Site-to-Site VPN provides resiliency.

- NEVER skip the Cost Explorer reconciliation. Topology analysis
  can identify the optimization; only CUR can quantify the savings.
  Emitting a recommendation without CE data is a guess.

- NEVER recommend IPv6 egress through NAT Gateway. IPv6 should use
  an Egress-Only Internet Gateway (free) — NAT Gateway charges
  apply only to IPv4.

- NEVER recommend cross-region VPC peering for hub-and-spoke
  topologies with > 3 regions. Cross-region peering connection
  count explodes combinatorially; TGW with cross-region attachments
  is simpler and roughly cost-equivalent.

- NEVER recommend replacing Transit Gateway with peering while
  centralized inspection (firewall, IPS) is in use. The
  centralized-routing value prop of TGW is the load-bearing
  feature; peering cannot replicate it without complex routing
  hacks.

- NEVER recommend Gateway Endpoints for hybrid scenarios (on-prem
  via DX). Gateway Endpoints are regional only; Interface Endpoints
  with PrivateLink extend to on-premises.

- NEVER stack multiple optimizations in a single maintenance
  window. Cross-AZ pinning, Gateway Endpoint deployment, and ASG
  changes each affect routing; isolating impact requires one
  dimension per change.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Diagnose NAT Gateway bill | Step 5 — NAT Gateway optimization |
| Reduce cross-AZ transfer | Step 4 — Cross-AZ transfer optimization |
| Decide peering vs Transit Gateway | Step 7 — VPC topology optimization |
| Evaluate Direct Connect | Step 9 — Direct Connect evaluation |
| Optimize internet egress | Step 6 — Internet egress optimization |
| Decide Aurora vs RDS Multi-AZ | Step 8 — RDS/Aurora data transfer optimization |
| Build the savings projection | Step 10 — Impact estimation |
| Handle missing data | Step 1 — Validate input and data sufficiency |
| Handle API errors | Error handling section |

## Expert heuristic — the 60-second triage

When handed a data-transfer bill and asked "why is this so high?",
run this 60-second triage before deep-diving any single dimension:

1. **Pull CE data-transfer breakdown.** If NAT Gateway is > 30% of
   the bill, deep-dive Step 5 (Gateway Endpoints).
2. **Pull VPC endpoint inventory.** No Gateway Endpoints in VPCs
   with private subnets = guaranteed optimization.
3. **Pull NAT Gateway count.** > 1 NAT per VPC + low traffic =
   consider consolidating (dev/test) or accepting HA cost (prod).
4. **Pull VPC topology.** > 4 VPCs on Transit Gateway with low
   inter-VPC traffic = peering migration candidate.
5. **Pull RDS Multi-AZ status.** Non-Aurora Multi-AZ on high-write
   workload = Aurora migration candidate.
6. **Pull internet egress volume.** > 10TB/month to global viewers
   without CloudFront = CloudFront migration candidate.

If any of the six checks hits, deep-dive the corresponding step.
If all six pass, the account is likely ALREADY_OPTIMAL on data
transfer — verify with the full ordered process.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`create-vpc-endpoint`, `modify-route-table`,
  `delete-nat-gateway`, `create-vpc-peering-connection`,
  `delete-transit-gateway-vpc-attachment`), emit and await operator
  approval.

- **Snapshot route tables before any change.** Capture the current
  state:
  ```bash
  for rtb in $(aws ec2 describe-route-tables --query 'RouteTables[].RouteTableId' --output text); do
    aws ec2 describe-route-tables --route-table-ids $rtb --output json \
      > rtb-backup-$rtb-$(date +%s).json
  done
  ```
  This provides a rollback path if a route change breaks connectivity.

- **One dimension per maintenance window.** Route changes, ASG
  changes, and Gateway Endpoint deployments each affect network
  behavior; stacking them obscures which change produced any
  observed impact.

- **Verify Gateway Endpoint propagation.** After creating a Gateway
  Endpoint, confirm the route table has the new prefix list entry:
  ```bash
  aws ec2 describe-route-tables --route-table-ids <rtb> --output json | \
    jq '.RouteTables[].Routes[] | select(.DestinationPrefixListId != null)'
  ```

- **Verify NAT Gateway removal is safe.** Before deleting a NAT,
  confirm no security groups or route tables still reference it:
  ```bash
  aws ec2 describe-route-tables --output json | \
    jq '.RouteTables[] | select(.Routes[].NatGatewayId != null)'
  ```

- **Bulk-operation safety limit.** Optimization across a fleet of
  VPCs MUST follow this algorithm:
  1. Sort flagged VPCs by estimated savings (largest first).
  2. Slice into batches of at most 3 VPCs.
  3. For each batch: emit per-VPC MIGRATION_STEPS, then a single
     CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `describe-route-tables` and verify connectivity before
     emitting the NEXT batch.
  5. Abort the sweep if any VPC loses connectivity or shows
     elevated error rates.
  The skill MUST NOT emit remediation CLI for more than 3 VPCs in
  a single output block.

- **RDS failover safety.** If an AZ-pinning change requires moving
  the primary DB, use `aws rds reboot-db-instance --force-failover`
  during a maintenance window. Do NOT trigger failover outside
  maintenance windows.

- **Direct Connect commit is billing-account-level.** A DX port is
  a physical connection at a colocation facility; committing to
  a 1Gbps port for 12 months affects the entire payer account.
  Surface this in the CONFIRMATION gate.

## Remediation guidance

### For OPPORTUNITY_FOUND — NAT Gateway (add Gateway Endpoints)

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.s3 \
  --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
  --vpc-endpoint-type Gateway \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint}]"

aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.dynamodb \
  --route-table-ids <rtb-1> <rtb-2> <rtb-3> \
  --vpc-endpoint-type Gateway
```

No application changes required. Gateway Endpoints intercept S3 and
DynamoDB DNS automatically.

### For OPPORTUNITY_FOUND — NAT Gateway (add Interface Endpoint)

```bash
# Only recommend if break-even analysis favors Interface Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$REGION.sqs \
  --vpc-endpoint-type Interface \
  --subnet-ids <subnet-1a> <subnet-1b> <subnet-1c> \
  --security-group-ids <sg-private> \
  --private-dns-enabled
```

### For OPPORTUNITY_FOUND — Cross-AZ (AZ-pinning)

```bash
# Update ASG launch template subnet filter to single-AZ
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <asg-name> \
  --vpc-zone-identifier "subnet-1a"  # was "subnet-1a,subnet-1b,subnet-1c"

# Create standby ASG in 1b for failover
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name <asg-name>-standby-1b \
  --launch-template <lt> \
  --vpc-zone-identifier "subnet-1b" \
  --min-size 0 --max-size 3 --desired-capacity 0
```

### For OPPORTUNITY_FOUND — Internet egress (CloudFront)

Route to `cloudfront-cost-optimizer` for the CloudFront-specific
optimization. The data-transfer-optimizer skill identifies the
opportunity and hands off.

### For OPPORTUNITY_FOUND — VPC topology (TGW → peering)

```bash
# Create peering connections for the full mesh
for src_vpc in $VPC_LIST; do
  for dst_vpc in $VPC_LIST; do
    if [ "$src_vpc" \< "$dst_vpc" ]; then
      aws ec2 create-vpc-peering-connection \
        --vpc-id $src_vpc --peer-vpc-id $dst_vpc
      # Accept the peering (if cross-account, requester accepts)
      aws ec2 accept-vpc-peering-connection \
        --vpc-peering-connection-id <pcx-id>
    fi
  done
done

# Update route tables to use peerings
# Then remove TGW attachments
aws ec2 delete-transit-gateway-vpc-attachment \
  --transit-gateway-attachment-id <tgw-attach-id>
```

### For OPPORTUNITY_FOUND — RDS migration

Multi-step: use `aws rds create-db-cluster` for Aurora, `aws dms
create-replication-task` for migration. Outside the scope of a
single skill invocation — hand off to the database team.

### For OPPORTUNITY_FOUND — Direct Connect

Provisioning DX is a multi-week physical-layer process (LOA, cross
connect, BGP configuration). Hand off to the network team for
provisioning; this skill sizes the commitment.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend monthly review of CUR data-transfer line items.
3. Re-evaluate Direct Connect upgrade at the next bandwidth
   forecast review.

## Deep reference: AWS data transfer pricing matrix

### Cross-AZ data transfer (per GB, each direction)

| Source → Destination | Rate |
|---|---|
| EC2 (AZ-1) → EC2 (AZ-2), same region | $0.01/GB |
| EC2 (AZ-1) → RDS (AZ-2), same region | $0.01/GB |
| RDS Multi-AZ replication (non-Aurora) | $0.01/GB |
| Aurora Multi-AZ replication | FREE (storage-layer) |
| ELB → EC2 target in different AZ | $0.01/GB |
| VPC peering intra-region | FREE |
| Transit Gateway intra-region | $0.02/GB (in + out) |

### Cross-region data transfer (per GB, outbound)

| Source region → Destination region | Rate |
|---|---|
| us-east-1 → us-west-2 | $0.02/GB |
| us-east-1 → eu-west-1 | $0.02/GB |
| us-east-1 → ap-southeast-1 | $0.09/GB |
| us-east-1 → sa-east-1 | $0.16/GB |
| eu-west-1 → ap-northeast-1 | $0.09/GB |
| Any region → CloudFront | FREE from S3; $0.02/GB from EC2 same-region |
| Any region → Direct Connect | $0.02/GB |

### Internet egress (per GB, tiered)

| Tier | Rate |
|---|---|
| First 10TB / month | $0.09/GB |
| Next 40TB (10-50TB) | $0.085/GB |
| Next 100TB (50-150TB) | $0.070/GB |
| Next 350TB (150-500TB) | $0.050/GB |
| > 500TB / month | Contact AWS |

### NAT Gateway pricing

| Component | Rate |
|---|---|
| Per GB processed | $0.045/GB |
| Hourly | $0.045/hour per NAT |

### VPC Endpoint pricing

| Endpoint type | Hourly | Per-GB |
|---|---|---|
| Gateway (S3, DynamoDB) | FREE | FREE |
| Interface (other AWS services) | $0.05/AZ/hour | $0.01/GB |
| PrivateLink (partner services) | $0.05/AZ/hour | $0.01/GB |
| Gateway Load Balancer Endpoint | $0.035/AZ/hour | $0.0035/GB |

### Transit Gateway pricing

| Component | Rate |
|---|---|
| Per attachment per hour | $0.05/hour |
| Per GB inbound | $0.02/GB |
| Per GB outbound | $0.02/GB |

### Direct Connect pricing (varies by region)

| Port speed | Port hourly | Per-GB outbound |
|---|---|---|
| 50 Mbps | ~$0.082 ($60/month) | $0.02/GB |
| 1 Gbps | ~$0.30 ($220/month) | $0.02/GB |
| 10 Gbps | ~$2.74 ($2,000/month) | $0.02/GB |
| 100 Gbps | ~$27.40 ($20,000/month) | $0.02/GB |

For per-region pricing precision, always check
`https://aws.amazon.com/ec2/pricing/on-demand/` (Data Transfer
section) for the current matrix.

## Recent AWS features (2024-2026)

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

## Domain

AWS CloudOps / Data Transfer Cost Optimization, FinOps & Networking.

## AWS documentation

- **AWS Data Transfer pricing** — https://aws.amazon.com/ec2/pricing/on-demand/ (Data Transfer section)
- **Amazon VPC Pricing** — https://aws.amazon.com/vpc/pricing/
- **VPC Endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **Transit Gateway** — https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html
- **Direct Connect** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/Welcome.html
- **NAT Gateways** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- **Amazon S3 Data Transfer** — https://aws.amazon.com/s3/pricing/
- **Amazon RDS Data Transfer** — https://aws.amazon.com/rds/pricing/
- **AWS Cost Explorer** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- **AWS Cost and Usage Report** — https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
