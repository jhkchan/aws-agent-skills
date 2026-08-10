---
name: nat-gateway-cost-optimizer
description: >-
  Optimises NAT Gateway cost through traffic analysis, VPC endpoint design,
  and architecture selection. Identifies avoidable AWS-service traffic
  (S3, DynamoDB via FREE Gateway endpoints; ECR, SSM, STS, Secrets Manager,
  CloudWatch, KMS via Interface endpoints), runs break-even maths on
  interface endpoints (~160 GB/month threshold at $0.045/GB NAT vs $0.01/GB
  endpoint), selects single vs multi-AZ NAT topology by environment,
  evaluates NAT Instance alternatives for dev/test, and emits a deterministic
  verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per VPC with the
  exact endpoint-creation payload and estimated monthly savings. Use when
  reviewing NAT Gateway spend, triaging unexpected data-processing charges,
  planning a FinOps VPC endpoint rollout, or deciding between NAT Gateway
  and NAT Instance for a non-HA workload.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline configuration classification works from pasted VPC
  topology, Cost Explorer data, and VPC Flow Logs summaries. Live-account
  optimisation uses aws ec2 describe-nat-gateways, aws ec2 describe-vpc-endpoints,
  aws ce get-cost-and-usage with filter for NatGateway usage type,
  aws ec2 describe-route-tables, and aws logs start-query for VPC Flow Logs
  traffic breakdown (AWS CLI v2, SSO or key-based credentials). Pricing is
  us-east-1 published rates as of 2026; re-state regional rates before
  producing dollar estimates for other regions.
keywords:
  - NAT Gateway
  - VPC Endpoint
  - Gateway Endpoint
  - Interface Endpoint
  - PrivateLink
  - S3 Gateway Endpoint
  - DynamoDB Gateway Endpoint
  - ECR endpoint
  - SSM endpoint
  - STS endpoint
  - Secrets Manager endpoint
  - data processing charge
  - cost optimization
  - FinOps
  - NAT Instance
  - cross-AZ data transfer
  - VPC Flow Logs
  - Cost Explorer
  - AWS PrivateLink
tags: [nat-gateway, vpc, networking, cost-optimization, finops, vpc-endpoint, privatelink]
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
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Reviewing NAT Gateway spend, triaging unexpected AWS data-processing
    charges, designing a VPC endpoint rollout, deciding between single vs
    multi-AZ NAT topology, evaluating NAT Instance for dev/test, or building
    a networking FinOps plan.
  when_not_to_use: >-
    Auditing Transit Gateway routing (use the networking auditor), VPC
    peering topology design (architectural, not cost-driven), Direct Connect
    procurement, or Security Group rule review. This skill focuses on NAT
    Gateway cost reduction via VPC endpoints and topology choice, not on
    connectivity troubleshooting or route-table correctness audits.
  activation_triggers:
    - "optimise NAT Gateway cost"
    - "NAT Gateway data processing charge"
    - "VPC endpoint cost benefit"
    - "S3 traffic through NAT"
    - "create Gateway VPC Endpoint"
    - "single NAT Gateway vs multi-AZ"
    - "NAT Instance alternative"
    - "reduce NAT Gateway bill"
    - "VPC Flow Logs traffic breakdown"
    - "FinOps networking review"
    - "PrivateLink endpoint savings"
    - "ECR traffic through NAT"
    - "DynamoDB VPC endpoint"
    - "unexpected AWS data transfer charge"
  invocation_schema: >-
    Input: either (a) a VPC configuration (NAT Gateways, route tables, VPC
    endpoints, subnet-to-AZ mapping, monthly data-processing GB from Cost
    Explorer), OR (b) a VPC ID for live-account optimisation. Output: a
    deterministic VPC/VERDICT/REASON/RECOMMENDATION/SAVINGS/IMPLEMENTATION
    block per VPC, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND,
    ALREADY_OPTIMAL.
  invocation_example: |-
    # Minimal valid input (offline classification):
    VPC: vpc-0abc123
    Region: us-east-1
    Environment: production
    NAT Gateways: 3 (one per AZ — us-east-1a, 1b, 1c)
    Data processing (last 30 days, Cost Explorer): 2,400 GB total
    Current VPC Endpoints: none
    Traffic breakdown (VPC Flow Logs, last 7 days):
      - S3: 900 GB/month
      - DynamoDB: 200 GB/month
      - ECR: 150 GB/month
      - Other AWS services: 150 GB/month
      - Internet (non-AWS): 1,000 GB/month
    Emit the standard optimization block (VPC, VERDICT, REASON,
    RECOMMENDATION, SAVINGS, IMPLEMENTATION).
---

# NAT Gateway Cost Optimizer

## What this skill does

Translates NAT Gateway spend into a concrete VPC endpoint rollout plan and
a dollar-denominated savings estimate. NAT Gateway is the #1 source of
unexpected AWS bills: every GB processed costs $0.045, and the most common
sources of that traffic (S3, DynamoDB) can be redirected to **free** Gateway
VPC Endpoints. The verdict is the **highest-leverage action** across four
dimensions — Gateway endpoints (free), Interface endpoints (break-even
analysis), NAT topology (single vs multi-AZ), and NAT Instance substitution
(dev/test) — applied in priority order. Always pairs the recommendation with
the exact `create-vpc-endpoint` payload so the operator can paste, review,
and apply.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving endpoint or topology change available | Emit recommended endpoints/topology + savings estimate |
| `OPTIMIZED` | An endpoint or topology change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | All applicable Gateway endpoints exist, Interface endpoints above break-even are in place, topology matches environment | No action — confirm posture |

**Priority order for opportunity dimensions (apply in this sequence, aggregate
all that apply into a single recommendation):**

1. **Gateway endpoints for S3 and DynamoDB** — FREE, always create them if
   any S3/DynamoDB traffic flows through NAT. This is the single largest
   quick win on most AWS accounts.
2. **Interface endpoints for high-traffic AWS services** (ECR, SSM, STS,
   Secrets Manager, CloudWatch, KMS) — apply break-even maths; recommend if
   monthly traffic > ~160 GB.
3. **NAT topology** — single NAT Gateway for non-prod (saves base hourly
   cost), one per AZ for prod (avoids cross-AZ transfer).
4. **NAT Instance substitution** — dev/test workloads where HA is not
   required; fixed EC2 cost instead of per-GB processing.

**Cost baseline (us-east-1, 2026):**

| Component | Rate | Notes |
|---|---|---|
| NAT Gateway base | $0.045/hour (~$32.85/month) | Per gateway, billed regardless of traffic |
| NAT Gateway data processing | $0.045/GB | The multiplier — 1 TB = $45/month on top of base |
| Gateway VPC Endpoint (S3, DynamoDB) | **FREE** | No hourly, no per-GB, no AZ surcharge |
| Interface VPC Endpoint base | $0.01/hour per AZ (~$7.30/month per AZ) | Billed per ENI across AZs where the endpoint exists |
| Interface VPC Endpoint data | $0.01/GB | Inbound to the endpoint from the VPC |
| Cross-AZ data transfer | $0.01/GB (each direction) | Applies when traffic crosses an AZ boundary |
| NAT Instance (t3.micro) | ~$8.47/month (t3.micro, 730h × $0.0116) | Fixed cost, no per-GB; bandwidth ~1 Gbps, not HA |

**Break-even rule of thumb:** for an Interface endpoint, monthly savings =
`(GB × $0.045) − (GB × $0.01 + $7.30 × num_AZs)`. The break-even point is
~**160 GB/month per AZ** of traffic to the target service.

## Mindset

**One-line takeaway:** Gateway endpoints (S3, DynamoDB) are free and should
exist on every VPC that has a NAT Gateway — their absence is almost always a
missed saving. Interface endpoints require break-even maths because they
carry a fixed hourly cost. The decision is driven by four networking realities:

- **Gateway endpoints are free and binary.** There is no break-even
  calculation for S3 and DynamoDB Gateway endpoints — they cost nothing to
  create and nothing to operate. The only reason NOT to have them is a route-
  table or endpoint-policy constraint. If S3 or DynamoDB traffic flows through
  a NAT Gateway and the corresponding Gateway endpoint does not exist, the
  verdict is always OPPORTUNITY_FOUND on that dimension.

- **Interface endpoints have a fixed cost that must be amortised.** An
  Interface endpoint for ECR costs ~$7.30/month per AZ ($21.90/month for a
  3-AZ VPC) plus $0.01/GB. If the workload pushes 10 GB/month to ECR through
  NAT, the endpoint costs MORE than the NAT processing it replaces. The
  break-even threshold (~160 GB/month per AZ) is the load-bearing gate.

- **Cross-AZ data transfer is the hidden tax on single-NAT topology.** A
  single NAT Gateway in AZ-A means traffic from AZ-B and AZ-C must cross the
  AZ boundary to reach the gateway, incurring $0.01/GB. For high-throughput
  workloads, the cross-AZ cost can EXCEED the savings from consolidating NAT
  Gateways. The topology decision must model both base cost AND cross-AZ
  transfer.

- **NAT Instance is not a drop-in replacement.** A t3.micro NAT Instance
  costs ~$8/month flat but caps at ~1 Gbps aggregate, has no HA, and requires
  manual failover. It is appropriate ONLY for dev/test or workloads where an
  outage is tolerable. Production traffic on a NAT Instance is a reliability
  incident waiting to happen.

## Philosophy

Four behaviours separate a senior networking FinOps engineer from a generalist:

- **Gateway endpoint absence is a defect, not an optimisation opportunity.**
  Every VPC with outbound S3 or DynamoDB traffic should have the corresponding
  Gateway endpoint. A senior engineer treats its absence as a misconfiguration
  (like an open security group), not as a "nice to have." The recommendation
  is unconditional: create it.

- **Interface endpoint recommendations require traffic evidence, not
  assumptions.** Recommending an ECR Interface endpoint because "ECR traffic
  is probably high" is a guess. Pull VPC Flow Logs (or at minimum, Cost
  Explorer filtered by service) to quantify the GB/month before recommending.
  An Interface endpoint on a low-traffic VPC INCREASES cost.

- **Topology is environment-specific, not universal.** A 3-AZ production VPC
  with 3 NAT Gateways is correct if cross-AZ traffic is high. The same
  topology in a dev environment is waste. The recommendation must cite the
  environment AND the traffic volume that justifies (or eliminates) the
  multi-AZ topology.

- **NAT Instance recommendations must carry a reliability warning.** A NAT
  Instance is a single EC2 host with no SLA. If the underlying hardware fails,
  all outbound traffic from the VPC stops until the instance is replaced (or
  an Auto Scaling recovery kicks in, adding minutes of downtime). Surface
  this explicitly — a cost saving that causes a production outage is a net
  loss.

## Pre-flight: VPC metadata gate

Run before classification. Misclassifying these produces false positives.

**Live-account pre-flight (skip if offline audit):**

```bash
# 1. Enumerate NAT Gateways and their state
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.NatGateways[] | {
    nat_gateway_id: .NatGatewayId,
    state: .State,                        # "available" | "pending" | "deleting"
    subnet_id: .SubnetId,                 # identifies the AZ
    public_ip: .NatGatewayAddresses[0].PublicIp,
    private_ip: .NatGatewayAddresses[0].PrivateIp
  }'

# 2. Enumerate existing VPC endpoints
aws ec2 describe-vpc-endpoints --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.VpcEndpoints[] | {
    endpoint_id: .VpcEndpointId,
    type: .VpcEndpointType,               # "Gateway" | "Interface" | "GatewayLoadBalancer"
    service: .ServiceName,
    state: .State,
    subnet_ids: .SubnetIds,
    route_table_ids: .RouteTableIds
  }'

# 3. Pull NAT Gateway data-processing cost from Cost Explorer (last 30 days)
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE_GROUP","Values":["EC2: NatGateway"]}}' \
  --metrics "UsageQuantity" "AmortizedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --output json

# 4. Pull per-service traffic breakdown via VPC Flow Logs (last 7 days)
aws logs start-query \
  --log-group-name <flow-logs-group> \
  --start-time $(date -d '-7 days' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, interface-id, srcaddr, dstaddr, bytes
    | filter interface-id = "<eni-of-nat-gateway>"
    | stats sum(bytes) as total_bytes by dstaddr
    | sort total_bytes desc
    | limit 20'

# 5. Enumerate route tables to confirm which subnets route to which NAT
aws ec2 describe-route-tables \
  --filter "Name=vpc-id,Values=<vpc-id>" \
  --output json | jq '.RouteTables[] | {
    route_table_id: .RouteTableId,
    subnet_id: (.Associations[0].SubnetId // "main"),
    nat_gateway: ([.Routes[] | select(.NatGatewayId != null) | .NatGatewayId][0])
  }'
```

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer returns $0 NAT Gateway cost | VPC has no NAT Gateway spend. Verdict ALREADY_OPTIMAL for this VPC. |
| VPC Flow Logs not enabled on the VPC | Cannot quantify per-service traffic breakdown. Fall back to Cost Explorer service-level filter; flag Interface endpoint recommendations as MEDIUM confidence (traffic volume estimated, not measured). |
| NAT Gateway state `pending` or `deleting` | Transient state. Re-query after 5 minutes; do not optimise against a gateway that is not yet serving traffic. |
| Route table shows no route to the NAT Gateway for a private subnet | That subnet's traffic does not flow through NAT; its GB do not count toward NAT processing. Verify the route-table-to-subnet mapping before aggregating traffic. |
| VPC has no private subnets (all public) | NAT Gateway is unused. Surface as a topology finding — the NAT Gateway can be deleted entirely. |
| Cost Explorer shows NAT Gateway cost but Flow Logs show 0 bytes | Flow Logs are misconfigured or querying the wrong ENI. Trust Cost Explorer for the dollar amount; flag the traffic breakdown as unavailable. |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious NAT Gateway and VPC endpoint behaviours

These behaviours are easy to misjudge without operational networking experience.
Each changes a recommendation if ignored:

- **A Gateway endpoint does NOT have a per-GB or per-hour charge — it is
  genuinely free.** This is the single most misunderstood VPC pricing fact.
  The S3 and DynamoDB Gateway endpoints appear in the route table and reroute
  traffic through the AWS network backbone instead of through the NAT Gateway.
  There is no ENI, no hourly charge, and no data-processing fee. The only
  "cost" is the route-table entry, which is free. If any S3 or DynamoDB
  traffic flows through a NAT Gateway, the absence of the Gateway endpoint is
  a guaranteed saving.

- **A Gateway endpoint only affects traffic from the VPC to the service — it
  does not affect traffic FROM S3 TO the VPC.** S3 cannot initiate a
  connection to a private subnet; the Gateway endpoint optimises the outbound
  (GET, PUT) direction. For event-driven architectures where S3 triggers
  Lambda or EventBridge, the Gateway endpoint still applies to the Lambda-to-
  S3 API calls within the VPC configuration.

- **Gateway endpoints are regional.** A Gateway endpoint for S3 in us-east-1
  does NOT cover S3 buckets in eu-west-1. If the workload accesses cross-
  region S3 buckets, the traffic still goes through NAT (or through a
  regional Interface endpoint + Transit Gateway). Surface cross-region S3
  access as a finding.

- **Interface endpoint pricing is per-AZ-per-hour plus per-GB.** An Interface
  endpoint creates an ENI in EACH subnet (AZ) you specify. A 3-AZ VPC with an
  ECR Interface endpoint in all 3 AZs pays $7.30 × 3 = $21.90/month in base
  cost, regardless of traffic volume. Always specify the minimum set of AZs
  that covers the workloads generating the traffic.

- **The break-even threshold (~160 GB/month) is per-service, not aggregate.**
  You cannot aggregate S3 (100 GB) + ECR (60 GB) to hit a single break-even.
  Each Interface endpoint is a separate financial decision with its own
  break-even. Gateway endpoints (S3, DynamoDB) are exempt because they are
  free — always create them.

- **Cross-AZ data transfer ($0.01/GB each direction) applies when a private
  subnet in AZ-B sends traffic to a NAT Gateway in AZ-A.** The traffic
  crosses the AZ boundary twice (to the gateway and back). For a single-NAT-
  Gateway topology, the cross-AZ cost = `total_GB × $0.02` (both directions).
  This can exceed the base-cost saving of consolidating from 3 to 1 gateway.

- **A NAT Instance has no per-GB processing charge — it is a fixed-cost EC2
  host.** This makes it dramatically cheaper than a NAT Gateway for high-
  bandwidth dev/test workloads (1 TB/month through a NAT Instance costs the
  same as 0 GB). BUT: the bandwidth is capped by the instance type (t3.micro
  ~1 Gbps aggregate; t3.medium ~up to 5 Gbps with ENA), and the instance is a
  single point of failure. Source/destination checks must be disabled
  (`modify-instance-attribute --no-source-dest-check`).

- **NAT Gateway does not support port forwarding.** If the workload needs
  inbound port mapping (e.g., a legacy NAT rule), a NAT Instance with iptables
  is required. This is an architectural constraint, not a cost decision —
  surface it as a finding.

- **Deleting a NAT Gateway does not delete its Elastic IP.** The EIP remains
  allocated and incurs $0.005/hour ($3.65/month) until released. Always pair
  a NAT Gateway deletion with `aws ec2 release-address` for the associated EIP.

- **VPC Flow Logs capture the interface ID of the NAT Gateway ENI.** Filter
  Flow Logs by the NAT Gateway's ENI to isolate the traffic that incurs
  processing charges. Traffic to S3 (after the Gateway endpoint is created)
  will NOT appear on the NAT ENI — confirming the endpoint is working.

- **Gateway endpoints and Interface endpoints for the same service are
  different constructs.** S3 has BOTH a Gateway endpoint (free) and an
  Interface endpoint (PrivateLink, paid). For cost optimisation, always
  prefer the Gateway endpoint for S3. The Interface endpoint is only needed
  for cross-region access or for workloads that require a private IP for DNS
  resolution (rare).

- **Endpoint policies can restrict which resources an endpoint can access.**
  A misconfigured endpoint policy on an S3 Gateway endpoint can silently
  block access to legitimate buckets. Always review the endpoint policy and
  the IAM policy together when an endpoint "doesn't work."

- **A NAT Gateway in a public subnet serves private subnets in the SAME VPC.**
  Cross-VPC NAT (via Transit Gateway or VPC peering) routes the traffic
  through the peering connection first, then through the NAT. The data-
  processing charge applies to the traffic as it exits the NAT, regardless of
  the source VPC. Surface cross-VPC NAT topology as a finding.

### Step 1: Gateway endpoints for S3 and DynamoDB (FREE — always create)

If ANY S3 or DynamoDB traffic flows through the NAT Gateway and the
corresponding Gateway endpoint does not exist:

**Pattern — S3 Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.us-east-1.s3 \
  --vpc-endpoint-type Gateway \
  --route-table-ids <rtb-id-1> <rtb-id-2> \
  --output json
```

**Pattern — DynamoDB Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --vpc-endpoint-type Gateway \
  --route-table-ids <rtb-id-1> <rtb-id-2> \
  --output json
```

**Savings estimate:**
```
S3 savings   = S3_GB_through_NAT × $0.045
DynamoDB savings = DDB_GB_through_NAT × $0.045
```

These savings are captured in FULL — Gateway endpoints are free, so every
dollar of redirected traffic is a dollar saved. There is no break-even
threshold.

If S3 or DynamoDB traffic exists and the Gateway endpoint is absent:
**OPPORTUNITY_FOUND** on this dimension. This is the single highest-leverage
recommendation the skill can make.

### Step 2: Interface endpoints for high-traffic AWS services (break-even analysis)

For each AWS service with significant traffic through NAT (ECR, SSM, STS,
Secrets Manager, CloudWatch, KMS, CodeArtifact, etc.), compute the break-even:

```
Monthly savings = (service_GB × $0.045) − (service_GB × $0.01 + $7.30 × num_AZs)
```

**Decision matrix:**

| Monthly traffic to service | Verdict | Recommendation |
|---|---|---|
| > 200 GB/month (> break-even) | **OPPORTUNITY_FOUND** | Create Interface endpoint in the AZs that originate the traffic |
| 100-200 GB/month (near break-even) | **OPPORTUNITY_FOUND** (MEDIUM confidence) | Create Interface endpoint in 1-2 AZs; monitor for 30 days |
| < 100 GB/month (< break-even) | Skip (ALREADY_OPTIMAL for this service) | Do NOT create — endpoint would increase cost |

**Pattern — ECR Interface Endpoint (most common high-traffic candidate):**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --subnet-ids <subnet-1a> <subnet-1b> \
  --security-group-ids <sg-id> \
  --private-dns-enabled \
  --output json

# Also create the ecr.dkr endpoint for Docker pull/push (separate service name)
aws ec2 create-vpc-endpoint \
  --vpc-id <vpc-id> \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.dkr \
  --subnet-ids <subnet-1a> <subnet-1b> \
  --security-group-ids <sg-id> \
  --private-dns-enabled \
  --output json
```

**Common Interface endpoint candidates and their typical break-even:**

| Service | Service name suffix | Typical traffic pattern | Break-even GB/month (per AZ) |
|---|---|---|---|
| ECR (api + dkr) | ecr.api, ecr.dkr | Container image pulls/pushes | ~160 GB (note: TWO endpoints needed) |
| SSM | ssm | Systems Manager agent check-ins | Low (usually skip) |
| STS | sts | AssumeRole calls | Very low (skip) |
| Secrets Manager | secretsmanager | App secret fetches | Low unless high-frequency rotation |
| CloudWatch Logs | logs | Application log shipping | High if logs are verbose; evaluate |
| KMS | kms | Encrypt/decrypt API calls | Low (skip) |
| CodeArtifact | codeartifact.api | Package pulls | Medium; evaluate by CI volume |

### Step 3: NAT topology optimisation (single vs multi-AZ)

The topology decision depends on the environment AND the cross-AZ traffic
volume.

**Decision matrix:**

| Environment | Cross-AZ traffic volume | Recommendation |
|---|---|---|
| Production, high throughput (> 500 GB/month cross-AZ) | High | Keep one NAT Gateway per AZ — cross-AZ transfer would exceed the base-cost saving |
| Production, low throughput (< 100 GB/month cross-AZ) | Low | Consolidate to a single NAT Gateway — base-cost saving exceeds cross-AZ transfer |
| Non-production (dev/test/staging) | Any | Single NAT Gateway — accept cross-AZ cost; HA is not required |
| Non-production, minimal outbound (< 10 GB/month) | Very low | Consider NAT Instance (Step 4) instead |

**Cross-AZ cost calculation for single-NAT topology:**
```
Cross-AZ cost = total_GB_from_other_AZs × $0.02  (both directions)
Base saving = (eliminated_gateways × $32.85)
Net = base_saving − cross_AZ_cost
```

If `Net > 0`, single-NAT is cheaper. If `Net < 0`, keep multi-NAT.

**Pattern — consolidate to single NAT Gateway (non-prod):**
1. Update route tables in all private subnets to point `0.0.0.0/0` to the
   single remaining NAT Gateway.
2. Delete the redundant NAT Gateways:
   `aws ec2 delete-nat-gateway --nat-gateway-id <id>`.
3. Release the Elastic IPs:
   `aws ec2 release-address --allocation-id <eip-alloc-id>`.

### Step 4: NAT Instance substitution (dev/test only)

For dev/test environments with minimal outbound traffic and no HA requirement:

**Pattern — NAT Instance (t3.micro, dev/test):**
```bash
# Launch a NAT Instance from the public AMI (search for the latest amzn-ami-vpc-nat AMI)
aws ec2 run-instances \
  --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/amzn-ami-vpc-nat-hvm \
  --instance-type t3.micro \
  --subnet-id <public-subnet> \
  --associate-public-ip-address \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=nat-instance-dev}]" \
  --output json

# Disable source/destination checks (required for NAT function)
aws ec2 modify-instance-attribute --instance-id <id> --no-source-dest-check

# Update route tables to point to the instance instead of the NAT Gateway
aws ec2 replace-route --route-table-id <rtb-id> \
  --destination-cidr-block 0.0.0.0/0 --instance-id <id>
```

**Savings estimate:**
```
NAT Gateway cost = $32.85 (base) + (GB × $0.045)
NAT Instance cost = $8.47 (t3.micro, flat) + (GB × $0)  [no per-GB charge]
Saving = NAT_Gateway_cost − $8.47
```

**Reliability warning (MUST surface in output):**
- NAT Instance is a single point of failure — no SLA, no automatic failover.
- Bandwidth is capped by instance type (~1 Gbps for t3.micro).
- If the underlying host fails, outbound traffic stops until the instance is
  replaced (manual or via Auto Scaling recovery, which adds 2-5 minutes of
  downtime).
- NOT suitable for production workloads.

### Step 5: Aggregation — emit the highest-leverage recommendation

Aggregate ALL applicable dimensions into a single recommendation. The verdict
is `OPPORTUNITY_FOUND` if any dimension has a saving. The recommendation
includes the full endpoint-creation and topology-change plan.

If no dimension has an opportunity (all applicable Gateway endpoints exist,
Interface endpoints are above break-even where justified, topology matches
environment): **ALREADY_OPTIMAL**.

If the recommendation was applied this session and verified: **OPTIMIZED**.

## Output format (per VPC)

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION:
  <list of endpoint-creation and topology-change actions>
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <Interface endpoint break-even assumptions, NAT Instance reliability warnings>
IMPLEMENTATION:
  1. <create-vpc-endpoint CLI command>
  2. <delete-nat-gateway CLI command>
  3. <verification command>
```

### Worked example — production VPC with no Gateway endpoints and high S3 traffic

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

### Worked example — already optimal production VPC

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

### Worked example — non-prod VPC with redundant NAT Gateways

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

## Verdict consistency rules (prevent misclassification)

The skill MUST emit verdicts that are mathematically and logically
self-consistent:

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every dimension,
   the verdict MUST be `ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND`.

2. **Negative-savings rule.** If an Interface endpoint would cost MORE than
   the NAT processing it replaces (traffic below break-even), do NOT recommend
   it. The verdict for that dimension is "no action." Emitting
   `OPPORTUNITY_FOUND` with a negative saving is a hard error.

3. **OPPORTUNITY_FOUND requires a non-zero savings line.** When emitting
   `OPPORTUNITY_FOUND`, the SAVINGS block must show a positive `MONTHLY_SAVING`
   for at least one dimension.

4. **SAVINGS arithmetic check.** `CURRENT_MONTHLY − PROJECTED_MONTHLY` MUST
   equal `MONTHLY_SAVING`. Round to 2 decimal places.

5. **Gateway endpoint is always free.** Never include a Gateway endpoint
   (S3, DynamoDB) in the cost side of the equation. Its absence from a VPC
   with S3/DynamoDB traffic is always OPPORTUNITY_FOUND.

6. **NAT Instance recommendations MUST include the reliability warning.**
   A NAT Instance recommendation without the "single point of failure,
   not suitable for production" caveat is non-compliant.

7. **Elastic IP release must accompany NAT Gateway deletion.** A NAT Gateway
   deletion without `release-address` for the associated EIP leaves a
   $3.65/month orphan charge.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-nat-gateways` returns empty | `len(NatGateways) == 0` | VPC has no NAT Gateway. Verdict ALREADY_OPTIMAL. |
| `get-cost-and-usage` returns $0 for NatGateway | Cost is 0 | Either no NAT Gateway or no traffic. Verify with `describe-nat-gateways`. |
| VPC Flow Logs query returns empty results | `queryResults` empty | Flow Logs not enabled or querying wrong ENI. Fall back to Cost Explorer service-level data; flag Interface endpoint recommendations as MEDIUM confidence. |
| `create-vpc-endpoint` fails with `RouteConflict` | API error | A route in the specified route table already points to a different endpoint. Remove the conflicting route first, or use a different route table. |
| `create-vpc-endpoint` (Interface) fails with `PrivateDnsOptionsIncompatible` | API error | The VPC already has a conflicting private DNS configuration. Retry with `--no-private-dns-enabled` and surface the DNS resolution impact. |
| `delete-nat-gateway` fails with `NatGatewayNotFound` | API error | The gateway was already deleted or is in a different region. Re-query with the correct region. |
| `release-address` fails with `AddressInUse` | API error | The EIP is still associated with the NAT Gateway (deletion not yet complete). Wait for the NAT Gateway state to reach `deleted`, then retry. |

## Anti-Patterns — NEVER

- NEVER recommend an Interface endpoint without quantifying the monthly
  traffic volume. An Interface endpoint on a low-traffic VPC INCREASES cost
  by $7.30/AZ/month. Always cite the GB/month and confirm it exceeds
  break-even.

- NEVER recommend a NAT Instance for a production workload. NAT Instance is
  a single point of failure with no SLA and bandwidth caps. It is for dev/
  test only. A cost saving that causes a production outage is a net loss.

- NEVER delete a NAT Gateway without updating the route tables FIRST. If the
  route table still points `0.0.0.0/0` to a deleted NAT Gateway, all
  outbound traffic from the private subnet stops. Update routes to the
  remaining gateway before deleting.

- NEVER forget to release the Elastic IP after deleting a NAT Gateway. An
  unreleased EIP incurs $3.65/month indefinitely — a silent leak that
  defeats the purpose of the optimisation.

- NEVER recommend a single-NAT topology for production with high cross-AZ
  traffic without computing the cross-AZ transfer cost. The cross-AZ charge
  ($0.01/GB each direction) can exceed the base-cost saving of eliminating
  gateways.

- NEVER assume Gateway endpoints cover cross-region S3 access. A Gateway
  endpoint is regional; cross-region S3 traffic still goes through NAT.
  Surface cross-region S3 access as a finding.

- NEVER aggregate traffic across services to hit a single Interface endpoint
  break-even. Each Interface endpoint is a separate financial decision.

- NEVER recommend an Interface endpoint for S3 when a Gateway endpoint is
  available. The Gateway endpoint is free; the Interface endpoint is not.
  Only use the S3 Interface endpoint if cross-region or private-DNS
  requirements mandate it.

- NEVER create an Interface endpoint in all AZs of the VPC by default.
  Specify only the AZs (subnets) that originate the traffic. Extra AZs add
  $7.30/month each with no benefit.

- NEVER treat VPC Flow Logs traffic as NAT processing traffic. Flow Logs
  capture ALL traffic on the ENI, including traffic that does not incur NAT
  processing charges. Filter to the NAT Gateway ENI specifically.

- NEVER recommend a NAT Instance without confirming source/destination
  checks are disabled. Without `--no-source-dest-check`, the instance will
  not route traffic and the NAT function fails silently.

- NEVER auto-apply endpoint or topology changes without the CONFIRM gate.
  A wrong route-table update can black-hole an entire VPC's outbound traffic.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-vpc-endpoint`, `delete-nat-gateway`, `replace-route`,
  `release-address`, `run-instances` for NAT Instance), emit:
  `CONFIRM: About to <action> on VPC <vpc-id> in region <region>. This
  affects <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms.

- **Route-table backup before topology changes.** Before modifying routes:
  `aws ec2 describe-route-tables --route-table-ids <rtb-id> --output json >
  /tmp/<rtb-id>-backup-$(date +%s).json`. Route changes are atomic and
  non-versioned — a wrong update can black-hole a subnet instantly.

- **Verify NAT Gateway state before relying on it.** Ensure the remaining
  NAT Gateway is `available` before deleting others. Deleting the only
  available gateway leaves the VPC with no outbound path.

- **Endpoint policy review.** When creating a Gateway endpoint, the default
  policy is "full access." If the environment requires restricted S3 bucket
  access, attach a custom endpoint policy before creating.

- **Private DNS impact for Interface endpoints.** Creating an Interface
  endpoint with `--private-dns-enabled` overrides the public DNS for the
  service within the VPC. Verify no existing DNS configurations conflict.

- **Bulk-operation safety.** For fleet-wide NAT optimisation across multiple
  VPCs, process one VPC per CONFIRM gate. Do NOT batch VPC changes — a route-
  table error in one VPC should not cascade to others.

## Recent AWS features (2024-2026)

- **Gateway Load Balancer endpoints (expanded 2024-2025):** For security
  appliance insertion (firewalls, IDS/IPS). Not a cost-optimisation lever,
  but relevant to VPC endpoint topology. Surface as a finding if the VPC
  uses third-party security appliances.

- **VPC endpoint policies for S3 (enhanced 2024):** Support for
  condition-key-based policies (e.g., restricting to specific IAM roles).
  Use for least-privilege Gateway endpoint configurations.

- **CloudWatch Network Monitor (2024-2025):** Proactive monitoring of
  network paths including NAT Gateway. Use to establish a baseline before
  optimisation and to verify no latency regression post-change.

- **Cost Explorer NAT Gateway granularity (2024):** Cost Explorer now
  separates NAT Gateway base (hourly) from data-processing (per-GB) in the
  usage-type dimension. Use this split to quantify the base-cost vs
  data-processing contribution.

- **Graviton-based NAT Instances (2024-2025):** t4g.micro NAT AMIs offer
  better price-performance than t3.micro for NAT Instance workloads.
  Consider t4g for new NAT Instance deployments.

## Error handling — remediation procedure failures

These branches complement the CLI/data-source table above. Each entry
describes what to do when a step in the optimisation procedure itself
fails — not when a CLI call errors out, but when the optimisation
*logic* cannot proceed safely.

- **If `create-vpc-endpoint` (Interface) fails with
  `ServiceLimitExceeded` for ENIs per subnet:** The VPC has hit the
  per-subnet ENI cap (default varies by instance type and subnet size).
  Do NOT retry in a different AZ — the limit is account+subnet scoped.
  Remediation: (a) request a quota increase via
  `service-quotas request-service-quota-increase --service-code vpc
  --quota-code L-FE5A380F`, OR (b) fall back to a Gateway endpoint for
  S3/DynamoDB and defer the Interface endpoint until the quota is
  approved. Surface the blocked recommendation as `VERDICT:
  QUOTA_BLOCKED` with the quota name and current/applied values.

- **If the Gateway endpoint does not cover the required S3 bucket
  (same-region access expected but bucket is in a different partition
  or the access path is non-S3):** Gateway endpoints only cover S3 and
  DynamoDB in the same region and same partition. If the workload
  accesses S3 Object Lambda, S3 access points in another account, or
  uses SDK calls that bypass the endpoint DNS (custom endpoints,
  Direct Connect public VIF), the Gateway endpoint silently does NOT
  intercept the traffic. Detect by re-running the Flow Logs query
  after endpoint creation — if NAT data-processing bytes do not drop
  by the expected delta, the endpoint is not capturing the traffic.
  Remediation: an Interface endpoint for `com.amazonaws.<region>.s3`
  (covers all S3 API calls including access points), OR a route-table
  audit for custom DNS.

- **If the NAT Gateway has active connections during replacement
  (single-NAT-to-dual-NAT migration or AZ topology change):** Existing
  TCP connections through the old NAT Gateway will be reset when its
  ENI is deleted. Detection: `aws ec2 describe-network-interfaces
  --filters Name=description,Values='ELB managed NAT gateway ...'` and
  CloudWatch `NATGateway.BytesOutToDestination`. Remediation: do NOT
  delete the old gateway until connection count is zero. Add the new
  gateway to the route table, wait one TTL cycle (default 350s for
  established TCP, longer for long-lived sessions), verify new
  connections use the new gateway via Flow Logs, then delete the old
  one. For stateful workloads (long-lived WebSocket, RDS sessions),
  schedule a maintenance window — connection reset is unavoidable.

- **If the Elastic IP release fails after NAT Gateway deletion
  (`InvalidAddress.AllocationInUse` or stuck in `pending`):** The EIP
  remains associated with the now-deleted gateway ENI. Poll
  `aws ec2 describe-addresses --public-ips <ip>` until `AssociationId`
  is empty (can take 5-30 minutes). If still associated after 30
  minutes, open an AWS Support case — do NOT force-disassociate, the
  ENI cleanup is asynchronous. The EIP charge accrues during this
  window; surface as `VERDICT: CLEANUP_PENDING` with expected
  completion time.

- **If Cost Explorer returns `NatGateway` cost but Flow Logs show no
  matching traffic (cost/traffic delta > 20%):** Either the Flow Logs
  query is wrong (wrong ENI filter, wrong time window) or there is a
  second NAT Gateway in the VPC. Re-query
  `aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=<vpc>` and
  aggregate all gateway costs. Do NOT proceed with the recommendation
  until the cost/traffic reconciliation is within 20%.

## Edge cases

- **Transit Gateway + NAT Gateway interaction.** When a VPC is attached
  to a Transit Gateway (TGW) that routes egress through a central
  egress VPC ("hub-and-spoke"), the spoke VPC's NAT Gateway is NOT
  used for cross-VPC traffic — TGW routes override local `0.0.0.0/0`
  routes for destinations reachable via TGR. Detection: query
  `aws ec2 search-transit-gateway-routes` and look for `0.0.0.0/0` or
  specific CIDR entries pointing to a TGW attachment. Implication: a
  spoke NAT Gateway with low traffic may be a candidate for deletion,
  BUT verify the egress VPC's NAT is sized for the aggregate spoke
  traffic. The optimisation must run at the egress VPC, not the spoke.
  Surface as a finding: `TGW_EGRESS_CENTRALIZED — spoke NAT traffic
  low, evaluate spoke NAT removal; run optimisation on <egress-vpc>`.

- **VPC with only private subnets and no internet gateway.** A NAT
  Gateway cannot be created (requires an IGW). Such VPCs already have
  optimal egress via Gateway endpoints for S3/DynamoDB. If non-S3
  traffic is required, the workload must use Interface endpoints or a
  TGW egress path. Skip NAT cost optimisation; verdict `ALREADY_OPTIMAL
  (no NAT present, IGW not attached)`.

- **NAT Gateway in a VPC peered with another VPC.** VPC peering does
  NOT route traffic through a NAT Gateway in the peer — peering routes
  are direct subnets. If the peer VPC has no NAT and depends on the
  local NAT for egress, that traffic will NOT appear in local NAT Flow
  Logs. Detection: check peering connection route tables. Surface as a
  finding if a peer VPC's egress strategy is missing.

## Domain

AWS CloudOps / Networking Cost Optimisation & VPC Endpoint Design.

## AWS documentation

- **Amazon VPC User Guide — VPC Endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **AWS PrivateLink** — https://aws.amazon.com/privatelink/
- **NAT Gateways** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- **Gateway VPC Endpoints (S3, DynamoDB)** — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- **Interface VPC Endpoints (PrivateLink)** — https://docs.aws.amazon.com/vpc/latest/privatelink/interface-endpoints.html
- **VPC Pricing — NAT Gateway** — https://aws.amazon.com/vpc/pricing/
- **AWS CLI Command Reference: ec2** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
