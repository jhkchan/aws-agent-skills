# Worked Examples — NAT Gateway Traffic Optimizer

Full worked examples covering S3 Gateway Endpoint creation, multi-AZ
consolidation, NAT Instance substitution, Interface Endpoint evaluation,
already-optimized, NEED_MORE_INFO, and an end-to-end optimization
walkthrough. Also includes error handling, edge cases, extended NEVER
list, and the NAT optimization decision tree.

## Worked example — S3 Gateway Endpoint creation (FREE saving)

```text
VPC: vpc-0prod01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Production VPC with 2 multi-AZ NAT Gateways ($65.70/mo hourly)
  processes 800 GB/month ($36.00/mo data processing), of which 300 GB
  (37.5%) is S3 traffic. No S3 Gateway Endpoint exists. Creating one
  eliminates 300 GB of NAT data processing at zero cost (Gateway
  Endpoints are free). Monthly saving: $13.50 (100% of S3 NAT
  processing). Multi-AZ NAT topology retained (production HA).
RECOMMENDATION:
  Current: 2 NAT Gateways, 800 GB/mo, 0 Gateway Endpoints, production
  Proposed: 2 NAT Gateways, 500 GB/mo, S3 Gateway Endpoint, production
  Dimensions changed: gateway-endpoint (S3)
  Dimensions checked: gateway-endpoint → (S3 300GB, no endpoint)
    interface-endpoint ✓ (ECR at 50GB/AZ below 162 GB break-even)
    topology ✓ (production, multi-AZ retained)
    nat-instance ✓ (production, not applicable)
    routing ✓ (no double-NAT)
    cloudfront ✓ (no CF origin)
  Confidence: HIGH — VPC Flow Logs cover 7 days with clear S3 traffic
    breakdown; Gateway Endpoint is free with zero downside; production
    multi-AZ topology correctly retained.
ESTIMATED_SAVINGS:
  Current monthly: $101.70
    hourly: 2 × $0.045 × 730 = $65.70
    data processing: 800 × $0.045 = $36.00
  Projected monthly: $88.20
    hourly: 2 × $0.045 × 730 = $65.70
    data processing: 500 × $0.045 = $22.50
    Gateway Endpoint: $0.00
  Monthly saving: $13.50 ($101.70 − $88.20 = $13.50 ✓)
  Annual saving: $162.00
MIGRATION_STEPS:
  1. Create S3 Gateway Endpoint:
     aws ec2 create-vpc-endpoint --vpc-id vpc-0prod01 \
       --service-name com.amazonaws.us-east-1.s3 \
       --route-table-ids rtb-0aaa rtb-0bbb rtb-0ccc \
       --vpc-endpoint-type Gateway
  2. Verify the prefix list route was added to all route tables:
     aws ec2 describe-route-tables \
       --filters Name=vpc-id,Values=vpc-0prod01 \
       --query 'RouteTables[].{RTB:RouteTableId,Routes:Routes[?GatewayId!=null]}'
  3. If S3 bucket policies restrict access by source, update to
     include the endpoint ID.
  4. Monitor BytesOutToDestination for 7 days to confirm S3 traffic
     shifted off NAT:
     aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
       --metric-name BytesOutToDestination \
       --dimensions Name=NatGatewayId,Value=nat-0prod01a \
       --start-time $(date -d '-7 days' +%FT%TZ) \
       --end-time $(date +%FT%TZ) --period 86400 --statistics Sum
CONFIRM: About to create-vpc-endpoint (S3 Gateway) in vpc-0prod01.
  Monthly saving $13.50 (13%); cost of endpoint $0.00. Proceed? (yes/no)
```

## Worked example — non-prod multi-AZ consolidation

```text
VPC: vpc-0staging01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Staging VPC has 3 NAT Gateways (one per AZ) at $98.55/month
  hourly, processing only 200 GB/month ($9.00/mo data processing).
  Staging does not require multi-AZ HA for egress. Consolidating to
  1 NAT Gateway saves $65.70/month in hourly charges, minus ~$2.60/month
  in cross-AZ transfer from AZ-2 and AZ-3 subnets. Net saving: $63.10/mo.
RECOMMENDATION:
  Current: 3 NAT Gateways, 200 GB/mo, 0 endpoints, staging
  Proposed: 1 NAT Gateway, 200 GB/mo, 0 endpoints, staging
  Dimensions changed: topology (3→1 NAT GW)
  Dimensions checked: gateway-endpoint ✓ (no S3/DDB traffic detected)
    interface-endpoint ✓ (200 GB total, no dominant service)
    topology → (3 NAT GW in staging, consolidate to 1)
    nat-instance ✓ (200 GB is above NAT Instance sweet spot at this
      traffic level; keep NAT Gateway for reliability)
    routing ✓ (no double-NAT)
    cloudfront ✓ (no CF origin)
  Confidence: HIGH — VPC Flow Logs confirm 200 GB/mo; staging
    environment tolerates single-AZ egress; cross-AZ impact quantified.
ESTIMATED_SAVINGS:
  Current monthly: $107.55
    hourly: 3 × $0.045 × 730 = $98.55
    data processing: 200 × $0.045 = $9.00
  Projected monthly: $44.45
    hourly: 1 × $0.045 × 730 = $32.85
    data processing: 200 × $0.045 = $9.00
    cross-AZ (added): 130 GB × $0.01 × 2 = $2.60
  Monthly saving: $63.10 ($107.55 − $44.45 = $63.10 ✓)
  Annual saving: $757.20
  Additional EIP release: 2 × $0.005 × 730 = $7.30/month ($87.60/yr)
  Total annual with EIP: $844.80
MIGRATION_STEPS:
  1. Back up current route tables:
     aws ec2 describe-route-tables --filters Name=vpc-id,Values=vpc-0staging01 \
       > /tmp/staging-rtb-backup.json
  2. Identify the NAT Gateway to keep (AZ-1):
     aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-0staging01 \
       Name=state,Values=available
  3. Update route tables in AZ-2 and AZ-3 to point at AZ-1 NAT Gateway:
     aws ec2 replace-route --route-table-id rtb-0bbb \
       --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0keep
     aws ec2 replace-route --route-table-id rtb-0ccc \
       --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0keep
  4. Delete the redundant NAT Gateways:
     aws ec2 delete-nat-gateway --nat-gateway-id nat-0removeB
     aws ec2 delete-nat-gateway --nat-gateway-id nat-0removeC
  5. Release the Elastic IPs after gateways are 'deleted':
     aws ec2 describe-nat-gateways --nat-gateway-ids nat-0removeB \
       --query 'NatGateways[0].NatGatewayAddresses[0].AllocationId'
     aws ec2 release-address --allocation-id eipalloc-0xxxB
     aws ec2 release-address --allocation-id eipalloc-0xxxC
  6. Verify connectivity from AZ-2 and AZ-3 subnets for 7 days.
CONFIRM: About to consolidate 3→1 NAT Gateway in vpc-0staging01
  (staging). Monthly saving $63.10 (59%) + $7.30 EIP release. Proceed?
  (yes/no)
```

## Worked example — Interface Endpoint evaluation (ECR above break-even)

```text
VPC: vpc-0ci01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: CI/CD VPC with 1 NAT Gateway processes 600 GB/month, of which
  400 GB (67%) is ECR Docker image traffic. ECR Interface Endpoint
  (api + dkr, 1-AZ) costs $7.30/month + $4.00/month per-GB = $11.30/mo.
  NAT data processing for ECR: 400 × $0.045 = $18.00/month. Net saving:
  $6.70/month. ECR traffic (400 GB) exceeds the 162 GB/AZ break-even.
RECOMMENDATION:
  Current: 1 NAT Gateway, 600 GB/mo, 0 Interface Endpoints, CI/CD
  Proposed: 1 NAT Gateway, 200 GB/mo, ECR Interface Endpoints (api+dkr), CI/CD
  Dimensions changed: interface-endpoint (ECR api + dkr)
  Dimensions checked: gateway-endpoint ✓ (no S3/DDB traffic)
    interface-endpoint → (ECR 400GB > 162 GB break-even)
    topology ✓ (1 NAT GW, already minimal)
    nat-instance ✓ (production CI, keep NAT Gateway)
    routing ✓ (no double-NAT)
    cloudfront ✓ (no CF origin)
  Confidence: HIGH — VPC Flow Logs confirm 400 GB ECR traffic;
    break-even math shows $6.70/mo net saving; ECR requires both
    api and dkr endpoints.
ESTIMATED_SAVINGS:
  Current monthly: $59.00
    hourly: 1 × $0.045 × 730 = $32.85
    data processing: 600 × $0.045 = $27.00
    ECR component: 400 × $0.045 = $18.00
  Projected monthly: $52.30
    hourly: 1 × $0.045 × 730 = $32.85
    data processing: 200 × $0.045 = $9.00 (remaining non-ECR traffic)
    ECR Interface Endpoint (api): $0.010 × 730 = $7.30
    ECR Interface Endpoint (dkr): $0.010 × 730 = $7.30
    ECR per-GB through endpoint: 400 × $0.010 = $4.00
    Correction: 2 endpoints = $14.60/mo, not $7.30
    Net projected: $32.85 + $9.00 + $14.60 + $4.00 = $60.45
  Monthly saving: ($59.00 − $60.45 = -$1.45)
  RE-EVALUATION: With 2 endpoints (api + dkr), cost is $14.60 + $4.00 =
  $18.60/month. NAT saving is $18.00/month. Net: -$0.60 (loses money).
  Break-even for 2 endpoints: ($14.60 + $4.00) / $0.045 = 413 GB/month.
  At 400 GB, ECR Interface Endpoints are BELOW break-even for 2 endpoints.
  REVISED VERDICT: Do NOT create (below break-even for 2-endpoint setup).
MIGRATION_STEPS:
  - Do NOT create ECR Interface Endpoints at this traffic level.
  - Re-evaluate when ECR traffic exceeds 413 GB/month (2-endpoint
    break-even) or consolidate to a single endpoint if possible.
CONFIRM: No action needed. ECR traffic (400 GB/mo) is below the
  2-endpoint break-even (413 GB/mo). NAT is cheaper for this volume.
```

**Key lesson:** ECR requires TWO Interface Endpoints (api + dkr),
which doubles the hourly cost. The break-even for ECR is higher than
for single-endpoint services. Always account for multi-endpoint
services in the break-even math.

## Worked example — NAT Instance substitution (dev/test)

```text
VPC: vpc-0dev01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Dev VPC with 1 NAT Gateway processes only 30 GB/month at a
  total cost of $34.20/mo ($32.85 hourly + $1.35 data processing).
  A t3.micro NAT Instance at $7.59/month handles this traffic volume
  easily (well within the ~800 GB crossover point). No HA requirement
  for dev. Saving: $26.61/month (78%) plus $3.65/mo EIP release.
RECOMMENDATION:
  Current: 1 NAT Gateway, 30 GB/mo, dev
  Proposed: 1 NAT Instance (t3.micro), 30 GB/mo, dev
  Dimensions changed: nat-instance (substitute NAT GW → NAT Instance)
  Dimensions checked: gateway-endpoint ✓ (minimal S3 traffic)
    interface-endpoint ✓ (below break-even)
    topology ✓ (already 1 NAT)
    nat-instance → (30 GB/mo, dev environment, ideal candidate)
    routing ✓ (no double-NAT)
    cloudfront ✓ (no CF origin)
  Confidence: HIGH — 30 GB/mo is well below the 800 GB crossover;
    dev environment has no HA requirement; t3.micro throughput (~1
    Gbps) is more than sufficient.
ESTIMATED_SAVINGS:
  Current monthly: $34.20
    hourly: 1 × $0.045 × 730 = $32.85
    data processing: 30 × $0.045 = $1.35
  Projected monthly: $7.59
    EC2 t3.micro: $0.0104 × 730 = $7.59
    Data transfer out: first 100 GB free = $0.00
  Monthly saving: $26.61 ($34.20 − $7.59 = $26.61 ✓)
  Annual saving: $319.32
  Additional EIP release: $0.005 × 730 = $3.65/month ($43.80/yr)
  Total annual with EIP: $363.12
MIGRATION_STEPS:
  1. Launch a NAT Instance:
     aws ec2 run-instances --image-id ami-0al2023 \
       --instance-type t3.micro --subnet-id subnet-0public \
       --source-dest-check false \
       --user-data '#!/bin/bash
         sysctl -w net.ipv4.ip_forward=1
         iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
         iptables -A FORWARD -i eth0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
         iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT'
  2. Disable source/destination check:
     aws ec2 modify-instance-attribute --instance-id i-0nat \
       --source-dest-check "{\"Value\": false}"
  3. Point the private subnet route table at the NAT Instance:
     aws ec2 replace-route --route-table-id rtb-0private \
       --destination-cidr-block 0.0.0.0/0 --instance-id i-0nat
  4. Verify connectivity from private subnets.
  5. Delete the NAT Gateway:
     aws ec2 delete-nat-gateway --nat-gateway-id nat-0dev01
  6. Release the EIP:
     aws ec2 release-address --allocation-id eipalloc-0dev01
CONFIRM: About to substitute NAT Gateway with NAT Instance (t3.micro)
  in vpc-0dev01 (dev). Monthly saving $26.61 (78%) + $3.65 EIP. Dev
  only — no HA. Proceed? (yes/no)
```

## Worked example — already optimized

```text
VPC: vpc-0prod02
VERDICT: OPTIMIZED
REASON: Production VPC with 2 multi-AZ NAT Gateways, S3 Gateway
  Endpoint, DynamoDB Gateway Endpoint, and ECR Interface Endpoints
  (above break-even at 500 GB/mo). No topology savings available
  (production requires multi-AZ). No double-NAT detected. All
  dimensions pass.
RECOMMENDATION:
  Current: 2 NAT Gateways, 850 GB/mo, S3+DDB Gateway + ECR Interface, production
  Proposed: no change
  Dimensions checked: gateway-endpoint ✓ (S3 + DDB endpoints exist)
    interface-endpoint ✓ (ECR at 500 GB > 324 GB 2-endpoint break-even)
    topology ✓ (production, multi-AZ for HA)
    nat-instance ✓ (production, not applicable)
    routing ✓ (no double-NAT)
    cloudfront ✓ (no CF origin)
  Confidence: HIGH — all endpoints verified; VPC Flow Logs confirm
    traffic patterns; multi-AZ appropriate for production.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if:
    (a) traffic patterns shift (new service becomes dominant)
    (b) environment changes (prod → staging enables consolidation)
    (c) quarterly FinOps review
```

## Worked example — NEED_MORE_INFO (Flow Logs not enabled)

```text
VPC: vpc-0newvpc03
VERDICT: NEED_MORE_INFO
REASON: VPC has 2 NAT Gateways ($65.70/mo hourly) but VPC Flow Logs
  are not enabled. Without Flow Logs, cannot break down traffic by
  destination service to identify S3/DynamoDB/ECR traffic patterns.
  Cannot make endpoint recommendations without per-service traffic data.
RECOMMENDATION:
  Current: 2 NAT Gateways, unknown traffic breakdown, 0 endpoints
  Proposed: pending Flow Logs data
  Confidence: LOW — no per-service traffic data to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without traffic breakdown)
MIGRATION_STEPS:
  1. Enable VPC Flow Logs:
     aws ec2 create-flow-logs --resource-ids vpc-0newvpc03 \
       --resource-type VPC --traffic-type ALL \
       --log-group-name /vpc/flowlogs/vpc-0newvpc03 \
       --deliver-logs-permission-arn arn:aws:iam::<acct>:role/flowlogs
  2. Wait 7 days for representative traffic data.
  3. Query Flow Logs for per-service breakdown:
     aws logs start-query --log-group-name /vpc/flowlogs/vpc-0newvpc03 \
       --start-time $(date -d '-7 days' +%s) \
       --end-time $(date +%s) \
       --query-string 'fields srcaddr, dstaddr, bytes \
         | stats sum(bytes) by dstaddr | sort sum(bytes) desc | limit 20'
  4. Re-evaluate with 7-day per-service traffic data.
  Do NOT optimize based on assumed traffic patterns.
```

## End-to-end optimization walkthrough (3-VPC fleet)

This example walks through the complete workflow for a 3-VPC fleet:
analyze each VPC's NAT spend, classify opportunities, and emit batched
recommendations.

**Fleet profile:**

| VPC | Env | NAT GW | Monthly GB | Existing Endpoints | Monthly Cost |
|---|---|---|---|---|---|
| vpc-prod01 | prod | 3 | 2,000 | none | $188.55 |
| vpc-stage01 | staging | 2 | 450 | none | $85.95 |
| vpc-dev01 | dev | 1 | 30 | none | $34.20 |

**Step 1 — Pull VPC Flow Logs for each VPC (7-day window):**
```bash
for vpc in vpc-prod01 vpc-stage01 vpc-dev01; do
  echo "=== $vpc ==="
  aws logs start-query \
    --log-group-name /vpc/flowlogs/$vpc \
    --start-time $(date -d '-7 days' +%s) \
    --end-time $(date +%s) \
    --query-string 'fields dstaddr, bytes | stats sum(bytes) as totalBytes by dstaddr | sort totalBytes desc | limit 20'
done
```

**Step 2 — Classify each VPC:**

- vpc-prod01: S3 (800 GB), DDB (200 GB), ECR (400 GB) → Gateway + eval Interface
- vpc-stage01: S3 (180 GB), DDB (45 GB), ECR (90 GB) → Gateway + consolidate topology
- vpc-dev01: Mixed (30 GB) → NAT Instance substitution

**Step 3 — Calculate fleet savings:**
```
vpc-prod01:  S3+DDB Gateway Endpoints (FREE) → saving $45.00/mo
vpc-stage01: S3+DDB Gateway + consolidate 2→1 NAT → saving $40.72/mo
vpc-dev01:   NAT Instance substitution → saving $26.61/mo + $3.65 EIP

Fleet monthly saving: $112.33 + $3.65 EIP = $115.98
Fleet annual saving: $1,391.76 + $43.80 EIP = $1,435.56
```

**Step 4 — Emit batched migration steps (max 3 VPCs per batch):**

```text
FLEET NAT OPTIMIZATION SUMMARY
VPCs evaluated: 3
FURTHER_OPTIMIZATION_AVAILABLE: 3
OPTIMIZED: 0
Total monthly saving: $115.98
Total annual saving: $1,435.56

Per-VPC recommendations:
1. vpc-prod01:  FURTHER_OPTIMIZATION_AVAILABLE — S3+DDB Gateway Endpoints ($45.00/mo)
2. vpc-stage01: FURTHER_OPTIMIZATION_AVAILABLE — S3+DDB Gateway + 2→1 NAT ($40.72/mo)
3. vpc-dev01:   FURTHER_OPTIMIZATION_AVAILABLE — NAT Instance substitution ($30.26/mo)

BATCH EXECUTION (in order of risk, lowest first):
Step 1: vpc-dev01 NAT Instance (dev only, zero risk)
Step 2: vpc-stage01 Gateway Endpoints (free, zero risk) + topology (low risk, staging)
Step 3: vpc-prod01 Gateway Endpoints (free, zero risk, production)

CONFIRM: Execute batch 1 (3 VPCs, $115.98/mo saving)?
Proceed? (yes/no)
```

---

## Error Handling and Edge Cases

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty for BytesOutToDestination | `len(Datapoints) == 0` | NAT Gateway may be newly created or idle. Check gateway state. If `available`, wait 7 days for data. |
| BytesOutToDestination present but only 1-2 days | Datapoint span < 7 days | NEED_MORE_INFO. Need 7+ days for traffic pattern analysis. |
| Flow Logs query returns no results | `results: []` | Flow Logs may not be filtering on the NAT Gateway ENI. Verify ENI ID. Check Flow Log filter (ALL vs ACCEPT). |
| CloudWatch API throttling | Exit code non-zero | Retry with `--max-attempts 5`. Fall back to Cost Explorer data as a proxy. |

### VPC Endpoint creation failures

| Failure mode | Detection | Handling |
|---|---|---|
| `create-vpc-endpoint` fails with `ResourceLimitExceeded` | API error | VPC endpoint quota reached. Request a quota increase via Service Quotas. |
| `create-vpc-endpoint` for Gateway fails with `RouteTableNotFound` | API error | Route table ID is invalid or in a different VPC. Verify VPC association. |
| Interface Endpoint creation fails with `SubnetNotFound` | API error | Subnet ID is invalid or in a different VPC. Verify subnet-VPC mapping. |
| S3 access breaks after Gateway Endpoint creation | Bucket policy restricts by source | Update bucket policy to include the endpoint ID or VPC ID. |

### NAT Gateway deletion failures

| Failure mode | Detection | Handling |
|---|---|---|
| `delete-nat-gateway` fails with `NatGatewayNotFound` | API error | Gateway already deleted or wrong region. Verify gateway ID. |
| Route table still references deleted NAT Gateway | `describe-route-tables` shows invalid NAT ID | Replace the route with the remaining NAT Gateway or a new one before traffic is affected. |
| EIP not released after deletion | EIP remains allocated | `release-address` must be called separately. The EIP is disassociated but not released automatically. |

### Operational edge cases

#### Transit Gateway with NAT Gateway

When a VPC is connected to a Transit Gateway (TGW), other VPCs may
route internet traffic through this VPC's NAT Gateway. This inflates
the NAT data processing charge. Detect via VPC Flow Logs: if source
IPs are from peered VPC CIDRs, the traffic is transiting from TGW.

**Resolution:** Each spoke VPC should have its own NAT Gateway, or
use a centralized egress VPC with cost allocation tags.

#### S3 bucket policy breaks after Gateway Endpoint

If an S3 bucket policy restricts access by VPC endpoint ID or source
IP, creating a Gateway Endpoint changes the source of the traffic. The
traffic now comes from the endpoint (prefix list) instead of the NAT
Gateway's EIP.

**Resolution:** Update the bucket policy to include the endpoint:
```json
{
  "Effect": "Allow",
  "Principal": "*",
  "Action": "s3:GetObject",
  "Resource": "arn:aws:s3:::my-bucket/*",
  "Condition": {
    "StringEquals": {
      "aws:sourceVpce": "vpce-0abc123"
    }
  }
}
```

#### Cross-region S3 traffic through NAT

S3 Gateway Endpoints are region-specific. If a workload in us-east-1
accesses an S3 bucket in eu-west-1 through a us-east-1 Gateway
Endpoint, the traffic does NOT go through the endpoint — it goes
through NAT. Cross-region S3 traffic always incurs NAT charges.

**Resolution:** Cannot be eliminated by Gateway Endpoints. Evaluate
Interface Endpoints (S3 does not support Interface Endpoints in all
regions). Or replicate data to the same region.

### Extended NEVER list

- NEVER recommend an Interface Endpoint without computing the break-
  even. An endpoint below break-even LOSES money.
- NEVER consolidate production VPCs to single NAT without flagging HA.
- NEVER skip `release-address` after deleting a NAT Gateway.
- NEVER create a Gateway Endpoint without verifying route table
  association for ALL subnets.
- NEVER recommend a NAT Instance for production.
- NEVER ignore cross-AZ transfer costs when consolidating.
- NEVER assume ECR needs only one Interface Endpoint (requires api + dkr).
- NEVER delete a NAT Gateway without backing up route tables.
- NEVER assume S3 Gateway Endpoint works for cross-region S3 access.
- NEVER batch-optimize more than 3 VPCs in a single operation.
- NEVER skip the CONFIRM gate before create/delete/replace operations.
- NEVER assume Flow Logs capture all traffic — rejected traffic may
  not appear if the Flow Log filter is ACCEPT-only.

### NAT optimization decision tree

```
Does the VPC have a NAT Gateway?
├── NO → OPTIMIZED. No NAT spend.
└── YES → Are VPC Flow Logs enabled with >= 7 days of data?
    ├── NO → NEED_MORE_INFO. Enable Flow Logs, wait 7 days.
    └── YES → Is there S3 or DynamoDB traffic through NAT?
        ├── YES → Are Gateway Endpoints created?
        │   ├── NO → FURTHER_OPTIMIZATION_AVAILABLE (Step 1).
        │   └── YES → Continue.
        └── NO → Continue.
        → Is any service's traffic above Interface Endpoint break-even?
        ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (Step 2).
        └── NO → Continue.
        → Is this non-production with 2+ NAT Gateways?
        ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (Step 3, consolidate).
        └── NO → Continue.
        → Is this dev/test with < 100 GB/month?
        ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (Step 4, NAT Instance).
        └── NO → Continue.
        → Is there double-NAT in route tables?
        ├── YES → FURTHER_OPTIMIZATION_AVAILABLE (Step 5, fix routing).
        └── NO → OPTIMIZED.
```
