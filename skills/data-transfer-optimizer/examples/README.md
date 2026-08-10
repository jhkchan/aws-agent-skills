# Example usage: data-transfer-optimizer

A walkthrough showing the skill optimizing a multi-dimension data
transfer bill, demonstrating the seven-dimension analysis (NAT
Gateway, cross-AZ, cross-region, internet egress, VPC topology,
RDS/Aurora, Direct Connect), the CUR USAGE_TYPE triage, the
per-dimension savings math, and the staged one-dimension-per-window
remediation with rollback path.

## Input (user prompt)

> Our data transfer bill crept up to ~$1,000/month and I can't
> figure out where the cost is going. Help me find and fix it.

```text
Account: 123456789012
Region: us-east-1 primary
Monthly data transfer costs (Cost Explorer, last 30 days):
  - NatGateway-Bytes: 12,000 GB × $0.045 = $540
  - NatGateway hourly: 3 NAT × $0.045/h × 730h = $98.55
  - DataTransfer-Regional-Bytes: 8,000 GB × $0.02 = $160
  - DataTransfer-Out-Bytes: 800 GB × $0.09 = $72
  - DataTransfer-Egress-Cross-Region: minimal ($30/month S3
    replication to eu-west-1 for DR)
VPC topology:
  - VPC-A in us-east-1 (3 AZs; primary app)
  - VPC-B in us-east-1 (3 AZs; analytics)
  - VPC peering: A↔B (intra-region, free)
  - Transit Gateway: not in use
  - NAT Gateway: 1 per AZ in VPC-A (3 total)
  - VPC endpoints: only S3 Gateway Endpoint in VPC-A
RDS inventory:
  - RDS for PostgreSQL primary in us-east-1a, Multi-AZ
    (standby in us-east-1b). Worker ASG spread across 3 AZs.
Workload context: microservices in VPC-A pulling from S3 and
DynamoDB; analytics EMR cluster in VPC-B reading same S3 buckets
and writing cross-AZ back to VPC-A database.
```

## Skill output

```text
TARGET: account 123456789012
VERDICT: OPPORTUNITY_FOUND
REASON: Cost Explorer shows NAT Gateway as 54% of data transfer
  cost ($638.55/month on 12TB AWS-service traffic through NAT),
  cross-AZ transfer on RDS-primary workloads at $160/month
  (workers not AZ-pinned), and no DynamoDB Gateway Endpoint.
  Three dimensions have actionable opportunities; combined
  projected savings $725/month, $8,700/year.
RECOMMENDATION:
  Current:
    NAT Gateway: 12,000 GB × $0.045 = $540/month + $98.55 hourly
      (3-AZ HA NAT setup). 95% of traffic is S3; 3% is DynamoDB.
    Cross-AZ transfer: 8,000 GB × $0.02 = $160/month (RDS primary
      in 1a, workers spread across 3 AZs)
    Internet egress: 800 GB × $0.09 = $72/month (modest)
    Cross-region: $30/month S3 CRR to eu-west-1 (DR — keep)
    VPC topology: VPC peering A↔B (free, optimal)
    RDS Multi-AZ: non-Aurora, incurring cross-AZ replication
    DX: not in use
  Proposed:
    - NAT: add VPC Gateway Endpoints for S3 (in VPC-A and VPC-B)
      AND DynamoDB (in VPC-A) → routes AWS-service traffic off
      NAT. Cuts NAT data processing by ~12,000 GB → saves
      $540/month on per-GB. Hourly charges remain ($98.55/month
      for general internet egress).
    - Cross-AZ: pin worker ASG subnet routing to RDS primary AZ
      (us-east-1a) → cuts cross-AZ by 90% → saves $144/month.
      Trade-off: lose multi-AZ HA for workers (mitigate with
      standby ASG in 1b activated on primary failover).
    - Internet egress: keep as-is ($72/month is below CloudFront
      or DX break-even at <1TB).
    - Cross-region S3 CRR: keep (DR/compliance justification).
    - VPC topology: keep (peering is already free).
    - RDS: evaluate Aurora migration for the Multi-AZ primary →
      would save ~$30/month on replication transfer. Defer to
      next quarterly review (migration effort is 2 weeks).
    - DX: not justified at current egress (<1TB/month steady).
  Confidence: HIGH — CUR line items confirm NAT composition; VPC
    topology confirms no Gateway Endpoints deployed; RDS confirms
    Multi-AZ non-Aurora.
ESTIMATED_SAVINGS:
  Monthly (NAT Gateway data processing): $540  (12,000GB × $0.045
    rerouted to Gateway Endpoints; hourly charges remain)
  Monthly (cross-AZ): $144  (8,000GB × 90% × $0.02 eliminated
    by AZ-pinning)
  Monthly (cross-region): $0  (S3 CRR retained for DR)
  Monthly (internet egress): $0  (below optimization threshold)
  Monthly (VPC topology): $0  (peering already free)
  Monthly (RDS): $0  (deferred to next review)
  Monthly (Direct Connect): $0  (not justified)
  Annual total: $8,208
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
  2. Create VPC Gateway Endpoints in VPC-A:
     aws ec2 create-vpc-endpoint --vpc-id $VPC_A \
       --service-name com.amazonaws.us-east-1.s3 \
       --route-table-ids <rtb-1a> <rtb-1b> <rtb-1c> \
       --vpc-endpoint-type Gateway
     aws ec2 create-vpc-endpoint --vpc-id $VPC_A \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --route-table-ids <rtb-1a> <rtb-1b> <rtb-1c> \
       --vpc-endpoint-type Gateway
  3. Repeat for VPC-B (S3 Gateway Endpoint; DynamoDB if VPC-B
     has DynamoDB consumers).
  4. Pin worker ASG to us-east-1a subnet:
     Update launch template subnet filter to us-east-1a only.
     Verify workers still reach RDS primary.
     Add a standby ASG in us-east-1b (min=0, desired=0; scale on
     RDS failover alarm).
  5. Validate CloudWatch NAT Gateway BytesOutToDestination drops
     by ~12TB/month over the next 7 days:
     aws cloudwatch get-metric-statistics --namespace AWS/NATGateway
       --metric-name BytesOutToDestination ...
  6. Validate cross-AZ DataTransfer-Regional-Bytes drops by ~90%
     in Cost Explorer over the next billing cycle.
CONFIRM: Before each state-changing CLI, emit and await:
  "CONFIRM: About to <action> in account 123456789012. Proceed?
   (yes/no)"
  Stage changes one dimension at a time; never batch NAT Gateway
  endpoint creation + ASG subnet change in the same window.
```

## What the skill caught that a generic assistant misses

1. **CUR USAGE_TYPE breakdown as the diagnostic starting point.**
   A generic assistant says "NAT Gateway is expensive, use VPC
   endpoints." The skill first pulls the per-USAGE_TYPE breakdown to
   identify that NAT Gateway is 54% of the bill, and that 98% of NAT
   traffic is AWS-service traffic (S3 + DynamoDB) eligible for free
   Gateway Endpoints. Without the CUR breakdown, the recommendation
   is a guess.

2. **Gateway Endpoints (free) vs Interface Endpoints (paid).** The
   skill recommends Gateway Endpoints for S3 and DynamoDB (FREE) and
   does NOT recommend Interface Endpoints for low-traffic services
   (which have $0.05/AZ/hour hourly charges that often exceed the
   savings). A generic assistant conflates "VPC endpoints" as a
   single category and may recommend the paid Interface type where
   the free Gateway type suffices.

3. **Cross-AZ pinning with failover mitigation.** The skill
   identifies that workers are spread across 3 AZs while the RDS
   primary is in one AZ — generating $160/month in cross-AZ transfer.
   The fix (pin to primary AZ) eliminates 90% of the cost. The
   skill also surfaces the trade-off (single-AZ HA loss) and
   recommends a standby ASG in the secondary AZ activated on
   failover alarm. A generic assistant recommends the pin without
   addressing the HA regression.

4. **VPC peering vs Transit Gateway cost-aware decision.** The skill
   confirms the existing VPC peering (free, intra-region) is already
   optimal for the 2-VPC topology and does NOT recommend migrating
   to Transit Gateway (which would add $0.02/GB). A generic
   assistant might recommend TGW for "operational simplicity"
   without quantifying the per-GB cost.

5. **Direct Connect break-even math.** The skill sizes the DX
   opportunity: at <1TB/month internet egress, DX is not justified
   (break-even is ~3TB/month for a 1Gbps port). A generic assistant
   might recommend DX as a blanket optimization without the
   break-even analysis.

6. **S3 CRR retained with justification.** The skill confirms the
   $30/month S3 cross-region replication is DR-justified and should
   be retained. A generic assistant might flag it as "optimization
   opportunity" without distinguishing DR-motivated replication
   from cost-wasteful replication.

7. **Staged one-dimension-per-window remediation.** The skill
   sequences the changes (Gateway Endpoints → AZ-pinning → verify)
   with monitoring between each, so any connectivity loss or
   elevated error rate can be attributed to a specific change. A
   generic assistant stacks all changes into one maintenance window,
   obscuring impact attribution.

8. **Rollback path.** The skill snapshots route tables before any
   change. A generic assistant goes straight to create-vpc-endpoint
   with no rollback plan.

## Slash-command invocation

```
/aws:optimize-data-transfer
```

Or via the orchestrator:

```
/aws:pipeline
You: "why is our data transfer bill so high?"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: data-transfer-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new pattern:

```bash
# Confirm Gateway Endpoints deployed
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=$VPC_A \
  --query 'VpcEndpoints[].{service:ServiceName,type:VpcEndpointType,state:State}' \
  --output table

# Monitor NAT Gateway BytesOutToDestination for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --dimensions Name=NatGatewayId,Value=$NAT_ID \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Confirm cross-AZ drop in Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '-7 days' +%F),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE","Values":["DataTransfer-Regional-Bytes"]}}' \
  --granularity DAILY --metrics "UsageQuantity" --output json
```

If NAT Gateway BytesOutToDestination does not drop by > 90% within
48h of Gateway Endpoint deployment, verify the route table has the
new prefix list entry and that no security group blocks S3 traffic
on the endpoint path.

## Fleet-wide extension

For an Organizations fleet of N accounts:

1. Identify all accounts with NatGateway-Bytes > $200/month in CUR.
2. For each flagged account, check VPC endpoint inventory.
3. Sort by Gateway Endpoint opportunity (largest NAT traffic first).
4. Slice into batches of 3 accounts (the spec's bulk-operation
   safety limit).
5. For each batch: emit per-account MIGRATION_STEPS, then a single
   CONFIRM for the batch.
6. Verify each batch before proceeding to the next.
7. After the NAT sweep, evaluate Data Transfer Savings Plan at the
   payer-account level for any remaining internet egress.
