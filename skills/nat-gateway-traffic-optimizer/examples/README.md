# Example usage: nat-gateway-traffic-optimizer

A walkthrough showing the skill optimizing a production VPC's NAT
Gateway cost by creating S3 and DynamoDB Gateway Endpoints (FREE),
demonstrating the VPC Flow Logs traffic analysis, the per-service
breakdown, the dollar savings math, and the post-change verification
via CloudWatch NAT Gateway metrics.

## Input (user prompt)

> Review this VPC's NAT Gateway costs before our Q3 FinOps review.
> I think we're paying too much for data processing.

```text
VPC: vpc-prod-finance-01
Environment: production
Region: us-east-1
NAT Gateways: 2 (us-east-1a, us-east-1b)

NAT Monthly Spend:
  - Hourly: 2 × $0.045 × 730 = $65.70
  - Data processing: 800 GB × $0.045 = $36.00
  - Total: $101.70/month

Existing VPC Endpoints: none

VPC Flow Logs (last 7 days, monthly projection):
  - S3 traffic: 300 GB (37.5% of total)
  - DynamoDB traffic: 50 GB (6.25% of total)
  - ECR traffic: 100 GB (12.5% of total)
  - SSM traffic: 30 GB (3.75% of total)
  - Other: 320 GB (40% of total)

Workload context: Production multi-AZ VPC serving a web application.
EC2 fleet in private subnets reads from S3 (config files, assets)
and DynamoDB (session data). Multi-AZ NAT required for HA.
```

## Skill output

```text
VPC: vpc-prod-finance-01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Production VPC with 2 multi-AZ NAT Gateways ($65.70/mo hourly)
  processes 800 GB/month ($36.00/mo data processing), of which 350 GB
  (43.75%) is S3 (300 GB) and DynamoDB (50 GB) traffic. No Gateway
  Endpoints exist. Creating S3 and DynamoDB Gateway Endpoints is FREE
  (no hourly, no per-GB charge) and eliminates 350 GB of NAT data
  processing. Monthly saving: $15.75. Multi-AZ topology retained
  (production HA).
RECOMMENDATION:
  Current: 2 NAT Gateways, 800 GB/mo, 0 endpoints, production
  Proposed: 2 NAT Gateways, 450 GB/mo, S3+DynamoDB Gateway Endpoints, production
  Dimensions changed: gateway-endpoint (S3 + DynamoDB)
  Dimensions checked: gateway-endpoint → (S3 300GB, DDB 50GB, no endpoints)
    interface-endpoint ✓ (ECR at 50 GB/AZ, below 162 GB/AZ break-even)
    topology ✓ (production, multi-AZ retained for HA)
    nat-instance ✓ (production, not applicable)
    routing ✓ (no double-NAT detected)
    cloudfront ✓ (no CF origin in this VPC)
  Confidence: HIGH — VPC Flow Logs cover 7 days with clear per-service
    breakdown; Gateway Endpoints are free with zero downside; production
    multi-AZ topology correctly retained.
ESTIMATED_SAVINGS:
  Current monthly: $101.70
    hourly: 2 × $0.045 × 730 = $65.70
    data processing: 800 × $0.045 = $36.00
  Projected monthly: $85.95
    hourly: 2 × $0.045 × 730 = $65.70
    data processing: 450 × $0.045 = $20.25 (S3+DDB eliminated)
    Gateway Endpoints: $0.00 (free)
  Monthly saving: $15.75 ($101.70 − $85.95 = $15.75 ✓)
  Annual saving: $189.00
MIGRATION_STEPS:
  1. Create S3 Gateway Endpoint:
     aws ec2 create-vpc-endpoint --vpc-id vpc-prod-finance-01 \
       --service-name com.amazonaws.us-east-1.s3 \
       --route-table-ids rtb-0aaa rtb-0bbb rtb-0ccc \
       --vpc-endpoint-type Gateway \
       --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint}]"
  2. Create DynamoDB Gateway Endpoint:
     aws ec2 create-vpc-endpoint --vpc-id vpc-prod-finance-01 \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --route-table-ids rtb-0aaa rtb-0bbb rtb-0ccc \
       --vpc-endpoint-type Gateway \
       --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=dynamodb-gateway-endpoint}]"
  3. Verify the prefix list routes were added to all route tables:
     aws ec2 describe-route-tables \
       --filters Name=vpc-id,Values=vpc-prod-finance-01 \
       --query 'RouteTables[].{RTB:RouteTableId,Routes:Routes[?GatewayId!=null]}'
  4. If S3 bucket policies restrict access by source, update to
     include the endpoint ID.
  5. Monitor BytesOutToDestination for 7 days to confirm traffic shift:
     aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
       --metric-name BytesOutToDestination \
       --dimensions Name=NatGatewayId,Value=nat-0prod01a \
       --start-time $(date -d '-7 days' +%FT%TZ) \
       --end-time $(date +%FT%TZ) --period 86400 --statistics Sum
CONFIRM: About to create S3 + DynamoDB Gateway Endpoints in
  vpc-prod-finance-01. Monthly saving $15.75 (15%); endpoint cost $0.00.
  Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Gateway Endpoints are FREE — no hourly, no per-GB.** A generic
   assistant may say "consider VPC endpoints" without distinguishing
   Gateway (free) from Interface ($0.010/h/AZ). The skill explicitly
   states the pricing model and cites the zero cost as the rationale.

2. **Interface Endpoint break-even is evaluated.** The skill checks ECR
   traffic (100 GB/month, 50 GB/AZ in 2-AZ prod) against the 162 GB/AZ
   break-even and correctly decides NOT to create the ECR Interface
   Endpoint. A generic assistant would recommend "add endpoints for
   everything" without the break-even math.

3. **Multi-AZ topology is retained for production.** The skill does NOT
   recommend consolidating NAT Gateways in a production VPC. A generic
   assistant might say "reduce to 1 NAT Gateway" without considering
   the HA requirement.

4. **All dimensions are listed in `Dimensions checked`.** The skill
   evaluates gateway-endpoint, interface-endpoint, topology,
   nat-instance, routing, and cloudfront — each marked ✓ or →. A
   generic assistant focuses on only the headline dimension.

5. **Route table verification is a post-step.** The skill includes a
   CLI to verify the prefix list routes were added to ALL route tables.
   A generic assistant assumes the endpoint "just works" without
   checking route propagation.

6. **Cost arithmetic is shown explicitly.** The skill shows the formula
   ($0.045 × 730 = $32.85, $36.00 → $20.25) so the operator can verify.
   A generic assistant says "this should save money" without showing
   the math.

## Slash-command invocation

```
/aws:optimize-nat-gateway-traffic
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our networking costs for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: nat-gateway-traffic-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm Gateway Endpoints exist and are available
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=vpc-prod-finance-01 \
    Name=vpc-endpoint-type,Values=Gateway \
  --query 'VpcEndpoints[].{Id:VpcEndpointId,Service:ServiceName,State:State}' \
  --output table

# Monitor NAT Gateway data processing for 7 days (should decrease)
aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --dimensions Name=NatGatewayId,Value=nat-0prod01a \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 86400 --statistics Sum --output json

# Verify S3 access still works from private subnets
aws s3 ls s3://my-config-bucket/ --region us-east-1 \
  --ec2-metadata-token $(curl -s http://169.254.169.254/latest/api/token)
```

If S3 access breaks after Gateway Endpoint creation, check the bucket
policy for source-IP or VPC restrictions. The endpoint changes the
traffic source from the NAT Gateway EIP to the VPC endpoint.

## Fleet-wide extension

For a fleet of N VPCs, run the skill in batch mode:

1. List all VPCs with NAT Gateways:
   `aws ec2 describe-nat-gateways --filter Name=state,Values=available`.
2. Group by VPC ID and check existing endpoints.
3. Pull 7-day VPC Flow Logs for each VPC.
4. Classify each VPC through the decision tree.
5. Sort by estimated monthly savings (largest first).
6. Slice into batches of 3 VPCs.
7. For each batch: emit per-VPC MIGRATION_STEPS, then a single
   CONFIRM for the batch.
8. Verify each batch before proceeding to the next.
9. After the Gateway Endpoint sweep, evaluate Interface Endpoints
   for remaining high-traffic services.
10. After endpoints, evaluate topology consolidation for non-prod VPCs.
