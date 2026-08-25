# Worked Examples (load on demand) — Data Transfer Optimizer

Secondary worked examples and per-step cost math moved verbatim from
SKILL.md. Loaded on demand.

---

## Step 1 — NEED_MORE_INFO branch (no CUR access) output template (moved from SKILL.md)



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



## Worked AZ-pinning example (Step 4) (moved from SKILL.md)



**Worked AZ-pinning example:**

A worker fleet in VPC-A reads 100GB/day from an RDS for PostgreSQL
primary in us-east-1a. Workers are spread across 3 AZs by ASG; ~67%
of traffic is cross-AZ. Cross-AZ cost: 67GB/day × $0.02/GB × 30 =
$40.20/month. Pin workers to us-east-1a (subnet selection in the
ASG launch template): cross-AZ cost drops to $0/month. Trade-off:
if us-east-1a fails, the workers fail. Mitigate by adding a
standby in us-east-1b that activates only on primary failover.



## Worked NAT-alternative savings examples (Step 5) (moved from SKILL.md)



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



## Worked internet-egress crossover examples (Step 6) (moved from SKILL.md)



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



## Worked peering-vs-TGW example (Step 7) (moved from SKILL.md)



**Worked peering-vs-TGW example:**

5 VPCs in us-east-1, full mesh, each pair exchanging 100GB/month.
- Transit Gateway: 5 attachments × $0.05/h × 730h = $182.50/month
  base + 10 pairs × 100GB × $0.02/GB (in+out, $0.04/GB round trip)
  = $40/month in per-GB → $222.50/month total
- VPC peering: 10 peering connections (5 × 4 / 2) × free = $0/month
- Net savings: $222.50/month. Operational cost: managing 10
  peerings (vs 1 TGW). Recommend: peering if team has automation
  for peering management; TGW if ops burden exceeds $222/month.



## Worked Aurora migration math (Step 8) (moved from SKILL.md)



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



## Step 10 — impact estimation formula (moved from SKILL.md)



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



## Worked example — already optimal (moved from SKILL.md)



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



## Worked example — NEED_MORE_INFO (no CUR access) (moved from SKILL.md)



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


