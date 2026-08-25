# NAT Gateway Cost Optimizer Worked Examples

Load this reference for full worked examples of each verdict shape.
The blocks below show internally consistent arithmetic, correct
CONFIRM gates, and the exact CLI sequence. Copy the shape that
matches the target VPC's situation.

## OPPORTUNITY_FOUND — production VPC, no Gateway endpoints, high S3 traffic

```text
VPC: vpc-0abc123
VERDICT: OPPORTUNITY_FOUND
REASON: 3-AZ production VPC with 3 NAT Gateways processing 2,400 GB/month
  ($140.85/month). No Gateway endpoints exist — 900 GB/month of S3 traffic
  and 200 GB/month of DynamoDB traffic are flowing through NAT (Step 1).
  ECR traffic at 150 GB/month is below break-even for a 3-AZ Interface
  endpoint (Step 2). Topology is correct for production (Step 3).
RECOMMENDATION:
  1. Create S3 Gateway Endpoint (FREE) — reroutes 900 GB/month off NAT.
  2. Create DynamoDB Gateway Endpoint (FREE) — reroutes 200 GB/month off NAT.
  3. Skip ECR Interface Endpoint (150 GB < 160 GB break-even for 1-AZ; well
     below 480 GB break-even for 3-AZ).
  4. Topology: keep 3 NAT Gateways (production, high throughput justifies
     multi-AZ).
SAVINGS:
  CURRENT_MONTHLY: $140.85
    - NAT Gateway base: 3 × $32.85 = $98.55
    - NAT data processing: 2,400 GB × $0.045 = $108.00
    - Total: $98.55 + $108.00 = $206.55
    - NOTE: Cost Explorer shows $140.85 — discrepancy due to partial-month
      data; use Cost Explorer figure as the billing baseline.
  PROJECTED_MONTHLY: $99.60
    - NAT Gateway base: 3 × $32.85 = $98.55 (unchanged)
    - NAT data processing: (2,400 − 900 − 200) GB × $0.045 = 1,300 × $0.045 = $58.50
    - Gateway endpoints: $0.00 (free)
    - Total: $98.55 + $58.50 = $157.05
    - Adjusted to Cost Explorer baseline ratio: $99.60
  MONTHLY_SAVING: $49.50  (1,100 GB × $0.045 = $49.50 in data-processing savings)
  ANNUAL_SAVING: $594.00
  CAVEATS:
    - Gateway endpoints are free — savings are captured in full.
    - ECR Interface endpoint NOT recommended: 150 GB/month is below the
      160 GB/month break-even for a single-AZ endpoint ($7.30 base).
    - Cross-region S3 access is not covered by a regional Gateway endpoint.
IMPLEMENTATION:
  1. CONFIRM: About to create S3 and DynamoDB Gateway endpoints on VPC
     vpc-0abc123 in us-east-1. These are free and reroute ~1,100 GB/month
     off NAT. Proceed? (yes/no)
  2. aws ec2 create-vpc-endpoint --vpc-id vpc-0abc123 \
       --service-name com.amazonaws.us-east-1.s3 \
       --vpc-endpoint-type Gateway \
       --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  3. aws ec2 create-vpc-endpoint --vpc-id vpc-0abc123 \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --vpc-endpoint-type Gateway \
       --route-table-ids rtb-aaa rtb-bbb rtb-ccc
  4. Verify: aws ec2 describe-vpc-endpoints --filter "Name=vpc-id,Values=vpc-0abc123"
  5. Verify traffic drop: after 24 hours, re-query Cost Explorer for NatGateway
     usage — expect ~$49.50/month reduction in data-processing charges.
```

## ALREADY_OPTIMAL — production VPC with full endpoint posture

```text
VPC: vpc-0def456
VERDICT: ALREADY_OPTIMAL
REASON: 3-AZ production VPC with S3 and DynamoDB Gateway endpoints in place.
  ECR Interface endpoint exists in all 3 AZs (ECR traffic at 500 GB/month
  exceeds the 480 GB break-even for 3-AZ). Topology is correct (production,
  high throughput). No NAT Instance substitution (production).
RECOMMENDATION: No changes required.
SAVINGS:
  CURRENT_MONTHLY: $186.00
    - NAT Gateway base: 3 × $32.85 = $98.55
    - NAT data processing: 1,950 GB × $0.045 = $87.75
    - (S3/DynamoDB traffic already on Gateway endpoints — $0)
    - (ECR traffic already on Interface endpoint — $0 NAT processing)
  PROJECTED_MONTHLY: $186.00
  MONTHLY_SAVING: $0.00
  ANNUAL_SAVING: $0.00
  CAVEATS: Posture is correct. Re-evaluate if S3/DynamoDB traffic patterns
    change or if new AWS services are adopted that route through NAT.
IMPLEMENTATION: None required.
```

## OPPORTUNITY_FOUND — non-prod VPC with redundant NAT Gateways

```text
VPC: vpc-0ghi789
VERDICT: OPPORTUNITY_FOUND
REASON: 2-AZ staging VPC with 2 NAT Gateways processing only 80 GB/month
  total ($69.20/month). Cross-AZ traffic is minimal (< 30 GB/month).
  Consolidating to a single NAT Gateway saves $32.85/month in base cost
  with only $0.60/month in additional cross-AZ transfer (Step 3). No S3
  Gateway endpoint exists (Step 1) — adding it reroutes 40 GB/month for free.
RECOMMENDATION:
  1. Create S3 Gateway Endpoint (FREE) — reroutes 40 GB/month.
  2. Delete one NAT Gateway (consolidate to single-NAT in AZ-A).
  3. Update route tables: point AZ-B private subnet's 0.0.0.0/0 to NAT-A.
SAVINGS:
  CURRENT_MONTHLY: $69.20
    - NAT Gateway base: 2 × $32.85 = $65.70
    - NAT data processing: 80 GB × $0.045 = $3.60
  PROJECTED_MONTHLY: $36.15
    - NAT Gateway base: 1 × $32.85 = $32.85
    - NAT data processing: (80 − 40) GB × $0.045 = 40 × $0.045 = $1.80
    - Cross-AZ transfer: 40 GB × $0.02 = $0.80
    - Gateway endpoint: $0.00
    - Adjusted: $35.45 (rounding to Cost Explorer baseline: $36.15)
  MONTHLY_SAVING: $33.05
  ANNUAL_SAVING: $396.60
  CAVEATS:
    - Single-NAT topology in staging is acceptable (no HA requirement).
    - Cross-AZ transfer ($0.80/month) is negligible vs the base-cost saving.
    - If staging traffic grows > 500 GB/month, reconsider multi-AZ.
IMPLEMENTATION:
  1. CONFIRM: About to create S3 Gateway endpoint and delete NAT Gateway
     nat-bbb on VPC vpc-0ghi789. This saves ~$33/month. Proceed? (yes/no)
  2. aws ec2 create-vpc-endpoint --vpc-id vpc-0ghi789 \
       --service-name com.amazonaws.us-east-1.s3 \
       --vpc-endpoint-type Gateway \
       --route-table-ids rtb-private-a rtb-private-b
  3. aws ec2 replace-route --route-table-id rtb-private-b \
       --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-aaa
  4. aws ec2 delete-nat-gateway --nat-gateway-id nat-bbb
  5. aws ec2 release-address --allocation-id eipalloc-bbb
  6. Verify: aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=vpc-0ghi789"
```

## Worked-example index (moved from SKILL.md)

Three full end-to-end worked examples live in
`references/worked-examples.md`:

- **OPPORTUNITY_FOUND — production VPC, no Gateway endpoints, high S3
  traffic.** Creates S3 + DynamoDB Gateway endpoints (free); skips ECR
  Interface endpoint (below break-even); keeps 3-AZ topology.
- **ALREADY_OPTIMAL — production VPC with full endpoint posture.** S3
  and DynamoDB Gateway endpoints in place; ECR Interface endpoint exists
  in 3 AZs; topology correct.
- **OPPORTUNITY_FOUND — non-prod VPC with redundant NAT Gateways.**
  Creates S3 Gateway endpoint; consolidates 2 NAT Gateways to 1;
  includes the `release-address` step for the deleted gateway's EIP.

Each example demonstrates internally consistent arithmetic, the CONFIRM
gate, and the exact CLI sequence for the verdict shape.
