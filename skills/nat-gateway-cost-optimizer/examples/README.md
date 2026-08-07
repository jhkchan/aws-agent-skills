# Example usage: nat-gateway-cost-optimizer

A walkthrough showing the skill optimising a production VPC with high S3
traffic through NAT Gateways, demonstrating the four-dimension analysis
(Gateway endpoints, Interface endpoint break-even, topology, NAT Instance
gating), the free-endpoint priority, and the cost reconciliation.

## Input (user prompt)

> Our FinOps team flagged NAT Gateway as the #1 unexpected cost line this
> month. Here's the VPC config — can you tell me what to do?

```text
VPC: vpc-prod-app-stack
Region: us-east-1
Environment: production

NAT Gateways: 3 (one per AZ — us-east-1a, 1b, 1c), all available
Current VPC Endpoints: none

Data processing (Cost Explorer, last 30 days):
  - NAT Gateway data processing: 2,400 GB total ($108.00)
  - NAT Gateway base: 3 × $32.85 = $98.55
  - Total NAT cost: $206.55 (Cost Explorer shows $140.85 after discounts)

Traffic breakdown (VPC Flow Logs, last 7 days, monthly projection):
  - S3: 900 GB/month
  - DynamoDB: 200 GB/month
  - ECR: 150 GB/month
  - Other AWS services (SSM, STS, etc.): 150 GB/month
  - Internet (non-AWS): 1,000 GB/month

Workload context: EKS production cluster with multiple microservices
pulling container images from ECR and reading/writing S3 and DynamoDB.
```

## Skill output

```text
VPC: vpc-prod-app-stack
VERDICT: OPPORTUNITY_FOUND
REASON: 3-AZ production VPC with 3 NAT Gateways processing 2,400 GB/month
  ($140.85/month in Cost Explorer). No Gateway endpoints exist — 900 GB/month
  of S3 traffic and 200 GB/month of DynamoDB traffic are flowing through NAT
  (Step 1). ECR traffic at 150 GB/month is below break-even for a 3-AZ
  Interface endpoint (Step 2). Topology is correct for production (Step 3).
RECOMMENDATION:
  1. Create S3 Gateway Endpoint (FREE) — reroutes 900 GB/month off NAT.
  2. Create DynamoDB Gateway Endpoint (FREE) — reroutes 200 GB/month off NAT.
  3. Skip ECR Interface Endpoint (150 GB < 480 GB break-even for 3-AZ).
  4. Topology: keep 3 NAT Gateways (production, high throughput justifies
     multi-AZ).
SAVINGS:
  CURRENT_MONTHLY: $140.85 (Cost Explorer baseline)
  PROJECTED_MONTHLY: $91.35
    - NAT data processing reduced by 1,100 GB × $0.045 = $49.50
  MONTHLY_SAVING: $49.50
  ANNUAL_SAVING: $594.00
  CAVEATS:
    - Gateway endpoints are free — savings captured in full.
    - ECR Interface endpoint NOT recommended: 150 GB/month is below the
      480 GB/month break-even for 3-AZ ($21.90/month base).
    - Cross-region S3 access is not covered by a regional Gateway endpoint.
IMPLEMENTATION:
  1. CONFIRM: About to create S3 and DynamoDB Gateway endpoints on VPC
     vpc-prod-app-stack in us-east-1. These are free and reroute ~1,100
     GB/month off NAT. Proceed? (yes/no)
  2. aws ec2 create-vpc-endpoint --vpc-id vpc-prod-app-stack \
       --service-name com.amazonaws.us-east-1.s3 \
       --vpc-endpoint-type Gateway \
       --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  3. aws ec2 create-vpc-endpoint --vpc-id vpc-prod-app-stack \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --vpc-endpoint-type Gateway \
       --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  4. Verify: aws ec2 describe-vpc-endpoints --filter "Name=vpc-id,Values=vpc-prod-app-stack"
  5. Verify traffic drop: after 24 hours, re-query Cost Explorer for
     NatGateway usage — expect ~$49.50/month reduction.
```

## What the skill caught that a generic assistant misses

1. **Gateway endpoint absence is a defect.** A generic assistant says
   "consider VPC endpoints." The skill identifies the EXACT services (S3,
   DynamoDB) whose traffic is flowing through NAT, confirms the Gateway
   endpoints are FREE (no break-even), and quantifies the savings to the
   dollar.

2. **Interface endpoint break-even maths.** A generic assistant recommends
   "an ECR endpoint too." The skill computes the 3-AZ break-even (480 GB/
   month) and rejects the ECR Interface endpoint because ECR traffic (150
   GB) is well below — creating it would INCREASE cost by $15/month.

3. **Cost Explorer reconciliation.** A generic assistant accepts the
   $206.55 raw calculation. The skill reconciles against the Cost Explorer
   billing figure ($140.85) and uses it as the savings baseline — avoids
   overstating savings from a theoretical model that doesn't match the bill.

4. **Topology gating by environment.** A generic assistant might suggest
   consolidating to fewer NAT Gateways. The skill keeps the 3-AZ topology
   because this is production with high throughput — cross-AZ transfer
   would negate the base-cost saving.

5. **Route-table-aware implementation.** The skill specifies the exact
   route-table IDs for each endpoint, and verifies via
   `describe-vpc-endpoints` post-creation. A generic assistant gives a
   generic `create-vpc-endpoint` without the route-table parameter.

## Slash-command invocation

```
/aws:optimize-nat-gateway-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "our NAT Gateway bill is too high — find the savings"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: nat-gateway-cost-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After applying the Gateway endpoints, validate the traffic drop:

```bash
# Confirm the endpoints are in place
aws ec2 describe-vpc-endpoints \
  --filter "Name=vpc-id,Values=vpc-prod-app-stack" \
  --profile default --output json | \
  jq '.VpcEndpoints[] | {VpcEndpointId, ServiceName, State}'

# After 24 hours, re-check NAT Gateway data processing
aws ce get-cost-and-usage \
  --time-period Start=2026-08-06,End=2026-08-07 \
  --granularity DAILY \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE_GROUP","Values":["EC2: NatGateway"]}}' \
  --metrics "UsageQuantity" "AmortizedCost" \
  --profile default --output json

# Verify S3 traffic no longer appears on the NAT Gateway ENI in Flow Logs
aws logs start-query \
  --log-group-name <flow-logs-group> \
  --start-time $(date -d '-1 days' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, interface-id, dstaddr, bytes
    | filter interface-id = "<nat-gateway-eni>" and dstaddr like "s3"
    | stats sum(bytes) as total_bytes'
```

If NAT Gateway data processing does NOT drop by ~1,100 GB within 48 hours,
verify the route tables include the Gateway endpoint prefix list.

## Fleet-wide extension

For an AWS Organisation with multiple VPCs:

1. Run the skill per VPC, prioritising VPCs with the highest NAT Gateway
   spend from Cost Explorer.
2. Batch Gateway endpoint creation (it's free, low-risk) across all VPCs
   with S3 or DynamoDB traffic.
3. Evaluate Interface endpoints per-VPC using the break-even maths — do not
   assume the same Interface endpoint set applies everywhere.
4. For multi-account organisations, consider Gateway endpoint creation via
   CloudFormation StackSets for consistent rollout.
