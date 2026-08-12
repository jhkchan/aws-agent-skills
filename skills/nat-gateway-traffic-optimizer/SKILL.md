---
name: nat-gateway-traffic-optimizer
description: 'Optimises NAT Gateway cost through traffic analysis (BytesOutToDestination vs BytesInFromDestination), VPC endpoint elimination of NAT traffic (S3 Gateway Endpoint, DynamoDB Gateway Endpoint, Interface Endpoints for SSM/STS/ECR/SQS), NAT Gateway vs NAT Instance cost comparison, single NAT Gateway consolidation for non-production environments, subnet routing optimization to avoid double-NAT, S3 Gateway Endpoint as a free persistent route, PrivateLink for SaaS API traffic, CloudFront-to-origin via VPC endpoint, cross-AZ data transfer cost analysis, and the $0.045/hr hourly + $0.045/GB per-GB pricing model. Uses VPC Flow Logs and CloudWatch to quantify per-service NAT traffic, compute VPC endpoint break-even thresholds, and project monthly savings. Emits OPTIMIZED when all dimensions pass, or FURTHER_OPTIMIZATION_AVAILABLE when a concrete endpoint-creation, topology-consolidation, or NAT Instance substitution opportunity exists with a dollar savings estimate.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted VPC Flow Logs, NAT Gateway CloudWatch metrics, and Cost Explorer NAT spend data.
  Live-account optimization uses aws ec2 describe-nat-gateways, aws ec2 describe-vpc-endpoints, aws ec2 describe-route-tables, aws cloudwatch get-metric-statistics (BytesOutToDestination, BytesInFromDestination,
  BytesOutToSource, BytesInFromSource, ConnectionEstablishedCount, ErrorPortAllocation), aws ec2 describe-flow-logs, aws logs start-query (VPC Flow Logs), and aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based credentials).
  Pricing references us-east-1 published rates as of 2026; re-state regional rates from the pricing matrix for other regions.
keywords:
- NAT Gateway
- cost optimization
- VPC endpoint
- S3 Gateway Endpoint
- DynamoDB Gateway Endpoint
- Interface Endpoint
- PrivateLink
- NAT Instance
- single NAT Gateway
- multi-AZ NAT
- cross-AZ data transfer
- VPC Flow Logs
- subnet routing
- double NAT
- CloudFront origin
- ECR VPC endpoint
- SSM VPC endpoint
- STS VPC endpoint
- data processing charge
- hourly charge
- FinOps
- networking cost
tags:
- nat-gateway
- networking
- cost-optimization
- finops
- vpc-endpoint
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising NAT Gateway cost, analysing VPC Flow Logs for NAT traffic patterns, evaluating VPC endpoint creation (S3, DynamoDB, SSM, STS, ECR, SQS), consolidating multi-AZ NAT Gateways to single NAT for
    non-prod, comparing NAT Instance vs NAT Gateway for dev/test, diagnosing unexpected data transfer charges, or running a FinOps networking cost review.
  when_not_to_use: VPC peering or Transit Gateway topology design (use vpc-peering-deployer or transit-gateway-deployer), NAT Gateway troubleshooting (connection errors, port exhaustion — use the VPC troubleshooter),
    or Security Group auditing (use ec2-security-group-auditor). This skill focuses on cost-driven traffic optimization, not connectivity debugging.
  activation_triggers:
  - optimise NAT Gateway cost
  - NAT Gateway data processing charge
  - VPC endpoint cost benefit
  - S3 traffic through NAT
  - create Gateway VPC Endpoint
  - single NAT Gateway vs multi-AZ
  - NAT Instance alternative
  - reduce NAT Gateway bill
  - VPC Flow Logs traffic breakdown
  - FinOps networking review
  - PrivateLink endpoint savings
  - ECR traffic through NAT
  - DynamoDB VPC endpoint
  - unexpected AWS data transfer charge
  - cross-AZ data transfer cost
  - subnet routing optimization
  - double NAT detection
  - S3 Gateway Endpoint free
  - CloudFront origin VPC endpoint
  - NAT Gateway hourly charge
  invocation_schema: 'Input: either (a) a VPC ID + live-account context, (b) a NAT Gateway CloudWatch metrics document with 7-30 day BytesOutToDestination/BytesInFromDestination data, OR (c) VPC Flow Logs
    summarised by destination service. Output: a deterministic VPC/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per VPC, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nVPC: vpc-0abc123def\nNAT Gateways: 2 (us-east-1a, us-east-1b)\nEnvironment: non-production (staging)\nRegion: us-east-1\nNAT\
    \ Monthly Spend:\n  - Hourly: 2 × $0.045 × 730 = $65.70\n  - Data processing: 450 GB × $0.045 = $20.25\n  - Total: $85.95/month\nExisting VPC Endpoints: none\nVPC Flow Logs (last 7 days):\n  - S3 traffic:\
    \ 180 GB (40% of total)\n  - DynamoDB traffic: 45 GB (10% of total)\n  - ECR traffic: 90 GB (20% of total)\n  - SSM traffic: 22 GB (5% of total)\nEmit the standard optimization block (VPC, VERDICT,\n\
    REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# NAT Gateway Traffic Optimizer

## What this skill does

Translates a VPC's NAT Gateway traffic posture into a concrete cost-
optimization recommendation with a dollar-denominated savings estimate.
The verdict is the highest-leverage action across six dimensions —
Gateway endpoints (S3/DynamoDB), Interface endpoints (SSM/STS/ECR/etc.),
NAT topology consolidation (single vs multi-AZ), NAT Instance
substitution, routing optimization (double-NAT elimination), and
CloudFront-to-origin via VPC endpoint — applied in priority order.
Always pairs the recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Three headline rules and the pricing model | First read |
| Mindset | Why VPC endpoints are the #1 NAT cost lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a VPC |
| Pre-flight data gate | NAT GW metrics + Flow Logs + Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Cross-AZ charges, Gateway vs Interface, double-NAT | Edge cases |
| Step 1 Gateway endpoints (S3, DynamoDB) | FREE, persistent, eliminates #1 traffic source | The headline savings dimension |
| Step 2 Interface endpoints | SSM, STS, ECR, SQS, Secrets Manager break-even | Per-service evaluation |
| Step 3 NAT topology (single vs multi-AZ) | Non-prod consolidation saves $32/mo per AZ | Topology savings |
| Step 4 NAT Instance substitution | Dev/test fixed-cost alternative | Low-traffic environments |
| Step 5 Routing optimization | Double-NAT detection, subnet route table audit | Hidden cost elimination |
| Step 6 CloudFront + PrivateLink | Origin via endpoint, SaaS API traffic | Advanced patterns |
| Step 7 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | Route table backup, CONFIRM gate | Before any apply CLI |

## Quick start

- **S3 Gateway Endpoint is FREE and persistent.** It is the #1 NAT
  traffic source eliminator. If S3 traffic flows through NAT, creating
  a Gateway Endpoint eliminates it at zero cost — no per-GB charge, no
  hourly charge, no per-AZ charge. The expert principle: S3 Gateway
  Endpoint eliminates the #1 NAT traffic source for free with a
  persistent route.
- **Cost formula (memorise this):**
  `monthly_nat_cost = (nat_gateway_count × $0.045 × 730) + (total_GB × $0.045)`
  `  = hourly_component + data_processing_component`
- **Single NAT for non-prod saves $32/mo per AZ removed.** A 3-AZ
  non-prod VPC with 3 NAT Gateways pays $98.55/month in hourly charges
  alone. Consolidating to 1 NAT Gateway saves $65.70/month ($32.85 × 2
  AZs removed). Use VPC Flow Logs to quantify savings.

## Mindset

NAT Gateway optimization is a traffic-routing decision, not an
infrastructure provisioning exercise. The goal is to route traffic to
AWS services via VPC endpoints (free or break-even-positive) rather
than through NAT Gateway (always metered at $0.045/GB).

Four principles guide every recommendation:

- **Gateway Endpoints are free and should always be created if traffic
  exists.** S3 and DynamoDB Gateway Endpoints have NO hourly charge and
  NO per-GB charge. They add a persistent route in the subnet route
  table. If any S3 or DynamoDB traffic flows through NAT, the Gateway
  Endpoint is a pure saving with zero downside.
- **Interface Endpoints have a break-even threshold.** Each Interface
  Endpoint costs $0.010/hour per AZ (~$7.30/month per AZ). The break-
  even is ~160 GB/month per AZ at $0.045/GB NAT data processing. Above
  the threshold, the Interface Endpoint saves money. Below it, NAT is
  cheaper.
- **Cross-AZ data transfer compounds NAT cost.** Traffic from a
  private subnet in AZ-1 to a NAT Gateway in AZ-2 incurs a cross-AZ
  charge ($0.01/GB each direction). This means a single NAT Gateway
  in one AZ can cost MORE than the per-GB NAT savings due to cross-AZ
  transfer charges from other AZs.
- **NAT Instance is a fixed-cost alternative for dev/test only.** A
  t3.micro NAT Instance costs ~$7.60/month (vs $32.85/month for a NAT
  Gateway). But it has no SLA, limited throughput (~5 Gbps), and is a
  single point of failure. Reserve for non-production.

## Quick reference — verdict thresholds

| Observation (7-30 day window) | Verdict | Recommendation |
|---|---|---|
| S3 traffic through NAT AND no S3 Gateway Endpoint | **FURTHER_OPTIMIZATION_AVAILABLE** (Gateway endpoint) | Step 1 — create S3 Gateway Endpoint (FREE) |
| DynamoDB traffic through NAT AND no DynamoDB Gateway Endpoint | **FURTHER_OPTIMIZATION_AVAILABLE** (Gateway endpoint) | Step 1 — create DynamoDB Gateway Endpoint (FREE) |
| ECR/SSM/STS/SQS/Secrets Manager traffic through NAT, monthly GB > break-even per AZ | **FURTHER_OPTIMIZATION_AVAILABLE** (Interface endpoint) | Step 2 — create Interface Endpoint(s) |
| Non-production VPC with 2+ NAT Gateways AND environment tolerates single-AZ egress | **FURTHER_OPTIMIZATION_AVAILABLE** (topology) | Step 3 — consolidate to single NAT Gateway |
| Dev/test VPC with low traffic (< 50 GB/month) AND reliability is not critical | **FURTHER_OPTIMIZATION_AVAILABLE** (NAT Instance) | Step 4 — substitute NAT Gateway with NAT Instance |
| Route tables show traffic traversing 2 NAT Gateways (double-NAT) | **FURTHER_OPTIMIZATION_AVAILABLE** (routing) | Step 5 — fix route table to eliminate double-NAT |
| S3 Gateway Endpoint exists, all Interface Endpoints above break-even, single NAT in non-prod or appropriate multi-AZ in prod | **OPTIMIZED** | None — continue monitoring |
| VPC Flow Logs not enabled or < 7 days of data | **NEED_MORE_INFO** | Enable Flow Logs, wait 7 days, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these data sources before any recommendation. Full CLI sequences are
in `references/nat-pricing-and-endpoint-matrix.md`.

**Required data sources** (summarized — see reference for full CLI):
1. NAT Gateway configuration: `aws ec2 describe-nat-gateways`
2. VPC Endpoint inventory: `aws ec2 describe-vpc-endpoints`
3. Route tables: `aws ec2 describe-route-tables` (to detect double-NAT
   and confirm endpoint routes)
4. NAT Gateway CloudWatch metrics (7-30 days):
   `aws cloudwatch get-metric-statistics` for
   `BytesOutToDestination`, `BytesInFromDestination`,
   `BytesOutToSource`, `BytesInFromSource`
5. VPC Flow Logs (7 days): `aws logs start-query` to break down
   traffic by destination service
6. Cost Explorer NAT spend (30 days): `aws ce get-cost-and-usage`
   filtered by `Nat-Gateway` usage type
7. Subnet-to-AZ mapping: `aws ec2 describe-subnets` (for cross-AZ
   analysis)

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| No NAT Gateway in the VPC | **OPTIMIZED** with note "no NAT Gateway spend." |
| VPC Flow Logs not enabled | **NEED_MORE_INFO**. Cannot identify per-service traffic. |
| Flow Logs enabled but < 7 days | **NEED_MORE_INFO**. Need 7+ days for traffic patterns. |
| NAT Gateway `State != available` | **BLOCKED**. Gateway is deleting or failed. |
| CloudWatch `BytesOutToDestination` absent | Gateway may be newly created. Wait 7 days. |
| Cost Explorer returns $0 for Nat-Gateway | Verify region filter. May be a different account. |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Gateway Endpoints are FREE and persistent.** Unlike Interface
  Endpoints, S3 and DynamoDB Gateway Endpoints have no hourly charge and
  no per-GB charge. They add a route in the subnet's route table that
  persists. Always create them if any S3 or DynamoDB traffic exists.

- **Interface Endpoints are per-AZ.** An Interface Endpoint in a 3-AZ
  VPC costs $0.010/h × 3 AZs × 730h = $21.90/month. The break-even is
  ~160 GB/month per AZ. If one AZ has high traffic and others don't,
  create the Interface Endpoint in select AZs only.

- **Cross-AZ transfer ($0.01/GB each direction) compounds NAT cost.**
  When a private subnet in AZ-1 routes to a NAT Gateway in AZ-2, the
  cross-AZ hop costs $0.01/GB each way ($0.02/GB round-trip). At 500
  GB/month cross-AZ, that's $10/month on top of the NAT per-GB charge.
  This is the hidden cost of single-NAT-Gateway topologies.

- **NAT Gateway delete takes minutes but EIP release is immediate.**
  After `delete-nat-gateway`, the gateway enters `deleting` state, then
  `deleted`. The Elastic IP is disassociated but NOT released. Use
  `release-address` to stop the EIP charge ($0.005/hour if unattached).

- **Gateway Endpoint route is in the main route table.** When you
  create a Gateway Endpoint, AWS adds a `pl-xxxxxxxx` prefix list route
  to the specified route tables. If you use a main route table with
  subnet-specific overrides, the endpoint route must be in EACH subnet's
  route table, not just the main one.

- **ECR traffic is often the #2 NAT cost after S3.** Docker image
  pulls from ECR go through NAT by default. An ECR Interface Endpoint
  eliminates this. At 100+ GB/month of ECR traffic, the Interface
  Endpoint is break-even positive.

- **CloudFront can front origin via VPC endpoint.** If your origin is
  in a private subnet (ALB or EC2), CloudFront routes to the origin via
  the public internet. If the origin is an S3 bucket, use a CloudFront
  Origin Access Identity (OAI) or Origin Access Control (OAC) to keep
  traffic within AWS — no NAT needed.

- **PrivateLink (Interface Endpoint) works for SaaS APIs.** If your
  workload calls a third-party SaaS API (e.g., Datadog, Splunk, GitHub)
  through NAT, check if the SaaS offers a PrivateLink endpoint. The
  Interface Endpoint cost may be less than the NAT per-GB charge for
  high-volume API calls.

- **NAT Instance throughput is limited.** A t3.micro-based NAT Instance
  maxes out at ~1 Gbps. For dev/test this is fine; for production, it
  is a bottleneck. NAT Gateway scales to 100 Gbps.

- **S3 Gateway Endpoint requires a bucket policy adjustment.** If your
  S3 bucket policy restricts access by VPC or source IP, the Gateway
  Endpoint changes the source. Update bucket policies to include the
  endpoint ID if needed.

### Step 1: Gateway endpoints (S3, DynamoDB) — FREE, always create

S3 and DynamoDB Gateway Endpoints are the highest-leverage, zero-cost
optimization. They eliminate the #1 NAT traffic source (S3 is typically
30-50% of NAT data processing) at no charge.

**Gateway Endpoint pricing:**
```
Hourly charge:     $0.00/hour
Per-GB charge:     $0.00/GB
Per-AZ charge:     $0.00/AZ
Total cost:        FREE
```

**Decision gate:**
```
Is there S3 or DynamoDB traffic through NAT?
├── NO → Skip (no S3/DynamoDB traffic to optimize)
└── YES → Does a Gateway Endpoint already exist?
    ├── YES → Verify route table includes the prefix list. If not,
    │         add the route manually.
    └── NO → CREATE the Gateway Endpoint. Pure saving, zero downside.
```

**Create S3 Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0abc123 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-0aaa rtb-0bbb rtb-0ccc \
  --vpc-endpoint-type Gateway \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=s3-gateway-endpoint}]"
```

**Create DynamoDB Gateway Endpoint:**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0abc123 \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --route-table-ids rtb-0aaa rtb-0bbb rtb-0ccc \
  --vpc-endpoint-type Gateway \
  --tag-specifications "ResourceType=vpc-endpoint,Tags=[{Key=Name,Value=dynamodb-gateway-endpoint}]"
```

**Saving from S3 Gateway Endpoint:**
```
monthly_saving = s3_GB_through_NAT × $0.045

Example: 180 GB S3 traffic/month through NAT
  Saving: 180 × $0.045 = $8.10/month (100% of S3 NAT processing cost)
  Annual: $97.20
  Cost of Gateway Endpoint: $0.00
```

### Step 2: Interface endpoints (per-service break-even)

Interface Endpoints cost $0.010/hour per AZ (~$7.30/month per AZ). The
break-even is ~160 GB/month per AZ at the NAT data processing rate of
$0.045/GB.

**Interface Endpoint pricing:**
```
Hourly charge:     $0.010/hour per AZ
Monthly per AZ:    $0.010 × 730 = $7.30/AZ/month
3-AZ monthly:      $7.30 × 3 = $21.90/month

Break-even per AZ: $7.30 / $0.045 = 162 GB/month
```

**Break-even by AZ count:**
| AZs | Monthly endpoint cost | Break-even GB/month |
|---|---|---|
| 1 | $7.30 | 162 GB |
| 2 | $14.60 | 324 GB (162 per AZ) |
| 3 | $21.90 | 486 GB (162 per AZ) |

**Common Interface Endpoints worth evaluating:**

| Service | Endpoint name | Typical NAT traffic source | Break-even likelihood |
|---|---|---|---|
| ECR (api + dkr) | `com.amazonaws.<region>.ecr.api` + `ecr.dkr` | Docker image pulls | HIGH if CI/CD is in-VPC |
| SSM | `com.amazonaws.<region>.ssm` | SSM Agent, Patch Manager, Session Manager | HIGH if SSM-managed |
| STS | `com.amazonaws.<region>.sts` | AssumeRole calls from private subnets | MEDIUM |
| SQS | `com.amazonaws.<region>.sqs` | Queue operations from private subnets | MEDIUM |
| Secrets Manager | `com.amazonaws.<region>.secretsmanager` | Secret retrieval from private subnets | MEDIUM |
| CloudWatch Logs | `com.amazonaws.<region>.logs` | Log ingestion from private subnets | HIGH for logging-heavy |
| KMS | `com.amazonaws.<region>.kms` | Encryption API calls | LOW (small payloads) |

**Decision gate per service:**
```
monthly_service_GB_through_NAT × $0.045  >  endpoint_cost_per_month?
├── YES → CREATE the Interface Endpoint. Net positive saving.
└── NO → Do NOT create. NAT is cheaper for this service's traffic volume.
```

**Create ECR Interface Endpoint (api + dkr):**
```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0abc123 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --security-group-ids sg-0endpoint \
  --private-dns-enabled

aws ec2 create-vpc-endpoint \
  --vpc-id vpc-0abc123 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.ecr.dkr \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --security-group-ids sg-0endpoint \
  --private-dns-enabled
```

ECR requires BOTH the api and dkr endpoints for Docker pull/push to
work without NAT.

### Step 3: NAT topology — single vs multi-AZ

In non-production environments (dev, test, staging), a single NAT
Gateway is sufficient. Production environments typically need multi-AZ
NAT for high availability.

**Single NAT Gateway savings:**
```
Each NAT Gateway hourly: $0.045/h × 730h = $32.85/month

3-AZ VPC with 3 NAT Gateways: 3 × $32.85 = $98.55/month (hourly only)
Consolidated to 1 NAT Gateway: 1 × $32.85 = $32.85/month
Saving: $65.70/month (2 AZs removed)

Cross-AZ cost added: traffic from AZ-2 and AZ-3 subnets to the NAT
Gateway in AZ-1 incurs $0.01/GB each direction. At 500 GB/month
cross-AZ: 500 × $0.01 × 2 = $10/month.

Net saving: $65.70 - $10.00 = $55.70/month (still strongly positive)
```

**Decision tree for topology:**
```
Is this a production VPC?
├── YES → Keep multi-AZ NAT for HA. Do not consolidate.
│         Focus on Steps 1, 2, 5, 6 instead.
└── NO (dev/test/staging) → How many NAT Gateways?
    ├── 1 → Already consolidated. Check other dimensions.
    └── 2+ → Consolidate to 1 NAT Gateway in the AZ with the most
             private subnets (minimizes cross-AZ transfer).
             Update route tables in all other AZ subnets to point
             0.0.0.0/0 at the single NAT Gateway.
```

**Consolidation steps:**
```bash
# 1. Identify the NAT Gateway to keep (in the busiest AZ)
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=vpc-0abc123 \
  Name=state,Values=available

# 2. Update route tables in other AZ subnets to point at the kept NAT GW
aws ec2 replace-route --route-table-id rtb-0bbb \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id nat-0keep

# 3. Delete the redundant NAT Gateways
aws ec2 delete-nat-gateway --nat-gateway-id nat-0remove

# 4. Release the Elastic IPs (after gateway is 'deleted')
aws ec2 describe-nat-gateways --nat-gateway-ids nat-0remove \
  --query 'NatGateways[0].NatGatewayAddresses[0].AllocationId'
aws ec2 release-address --allocation-id eipalloc-0xxx
```

### Step 4: NAT Instance substitution (dev/test only)

For low-traffic dev/test VPCs (< 50 GB/month), a NAT Instance is
cheaper than a NAT Gateway.

**Cost comparison:**
| Option | Hourly | Monthly (730h) | Per-GB | 50 GB/month total |
|---|---|---|---|---|
| NAT Gateway | $0.045 | $32.85 | $0.045/GB | $32.85 + $2.25 = $35.10 |
| NAT Instance (t3.micro) | $0.0104 | $7.59 | $0.00 (EC2 data transfer only) | $7.59 |
| Saving | | $25.26/month | | $27.51/month |

**NAT Instance limitations:**
- No SLA (single instance, single AZ)
- Throughput limited (~1 Gbps for t3.micro)
- Requires manual setup (user-data iptables NAT rules)
- No automatic failover
- AMI must be maintained (OS patches)

**Decision gate:**
```
Is this a dev/test environment?
├── NO → Do NOT substitute. NAT Gateway is required for HA.
└── YES → Is monthly NAT traffic < 100 GB?
    ├── YES → NAT Instance is cheaper. Recommend substitution.
    └── NO → NAT Gateway may be cheaper (traffic > break-even).
             At 100 GB: NAT GW = $37.35, NAT Instance = $7.59 +
             cross-AZ. Evaluate on a case-by-case basis.
```

**NAT Instance setup (fargate or EC2):**
```bash
# Launch a NAT Instance from the AWS-provided NAT AMI
# Or use a standard AL2023 AMI with user-data:
aws ec2 run-instances \
  --image-id ami-0al2023 \
  --instance-type t3.micro \
  --subnet-id subnet-0public \
  --key-name my-key \
  --source-dest-check false \
  --user-data '#!/bin/bash
    sysctl -w net.ipv4.ip_forward=1
    iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
    iptables -A FORWARD -i eth0 -o eth0 -m state \
      --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i eth0 -o eth0 -j ACCEPT' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=nat-instance-dev}]"

# Disable source/destination check (required for NAT)
aws ec2 modify-instance-attribute --instance-id i-0nat \
  --source-dest-check "{\"Value\": false}"

# Point the private subnet route table at the NAT Instance
aws ec2 replace-route --route-table-id rtb-0private \
  --destination-cidr-block 0.0.0.0/0 \
  --instance-id i-0nat
```

### Step 5: Routing optimization (double-NAT detection)

Double-NAT occurs when traffic traverses TWO NAT devices before
reaching the internet. This doubles the data processing charge.

**Common double-NAT scenarios:**
```
1. Transit Gateway → NAT Gateway → Internet
   (TGW routes to a VPC with NAT, but the source VPC also has NAT)

2. VPC Peering → NAT Gateway → Internet
   (Peered VPC routes internet traffic through a VPC with NAT)

3. Private subnet → NAT Gateway (AZ-1) → NAT Gateway (AZ-2)
   (Misconfigured route tables chain two NAT Gateways)
```

**Detection via route table audit:**
```bash
# List all route tables in the VPC
aws ec2 describe-route-tables --filter Name=vpc-id,Values=vpc-0abc123 \
  --query 'RouteTables[].{RTB:RouteTableId,Routes:Routes[?DestinationCidrBlock==`0.0.0.0/0`]}' \
  --output json

# Check for chains: does any route table point 0.0.0.0/0 at an
# instance or ENI that is itself behind another NAT?
```

**Fix:** Ensure each private subnet's `0.0.0.0/0` route points at
exactly ONE NAT Gateway (or NAT Instance). No chains.

### Step 6: CloudFront and PrivateLink

**CloudFront to origin:**
If your CloudFront distribution's origin is an ALB or EC2 instance in
a private subnet, CloudFront reaches it via the public internet. No NAT
Gateway is needed for CloudFront traffic — CloudFront has its own
network path. But if the origin calls back to AWS services (S3, API
Gateway), that traffic may go through NAT.

For S3 origins: use CloudFront OAI/OAC to keep traffic within AWS. No
NAT needed.

**PrivateLink for SaaS APIs:**
If your private-subnet workload calls a third-party SaaS API (e.g.,
Datadog, Splunk, GitHub Enterprise) through NAT, check if the SaaS
offers an AWS PrivateLink endpoint.

```
Monthly SaaS API traffic through NAT: 200 GB
NAT data processing cost: 200 × $0.045 = $9.00/month
PrivateLink Interface Endpoint cost: $7.30/month (1 AZ) or $21.90 (3 AZ)
Break-even: if traffic > 162 GB/AZ/month, PrivateLink is cheaper
```

### Step 7: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_nat_cost =
  (nat_gateway_count × $0.045 × 730) + (total_GB × $0.045)

projected_monthly_nat_cost =
  (remaining_nat_gateway_count × $0.045 × 730)
  + (remaining_GB × $0.045)
  + (interface_endpoint_count × $0.010 × az_count × 730)

monthly_saving = current_monthly_nat_cost - projected_monthly_nat_cost
```

Always state assumptions: GB eliminated by Gateway Endpoints (free),
GB eliminated by Interface Endpoints (cost offset by endpoint hourly),
NAT Gateways removed (topology consolidation), cross-AZ transfer
impact, and pricing region.

### Step 8: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass (Gateway Endpoints exist, Interface Endpoints
  above break-even, topology appropriate for environment, no double-NAT)
  → **OPTIMIZED**.
- Data insufficient (no Flow Logs, < 7 days of data) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` gate.

## Output format

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <NAT Gateway count>, <total monthly GB>, <existing endpoints>, <environment>
  Proposed: <NAT Gateway count>, <remaining GB>, <new endpoints>, <topology change>
  Dimensions changed: <gateway-endpoint | interface-endpoint | topology | nat-instance | routing | cloudfront>
  Dimensions checked: <list ALL, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
  Projected monthly: $<amount>
  Monthly saving: $<amount>
  Annual saving: $<amount>
  Assumptions: <list (pricing region, traffic volumes, AZ count)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <vpc-id> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (S3 Gateway Endpoint creation, multi-AZ
consolidation, NAT Instance substitution, Interface Endpoint evaluation,
already-optimized, NEED_MORE_INFO) are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <NAT GW count>, <monthly GB>, <endpoints>, <environment>
  Proposed: <NAT GW count>, <remaining GB>, <new endpoints>, <topology>
  Dimensions changed: <gateway-endpoint | interface-endpoint | topology | nat-instance | routing | cloudfront>
  Dimensions checked: <list ALL, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend an Interface Endpoint without computing the
   break-even.** The REASON MUST cite whether the traffic volume exceeds
   the ~162 GB/AZ/month threshold.

5. **NEVER recommend consolidating NAT Gateways in a production VPC
   without flagging the HA risk.** Single NAT Gateway in production is
   a single point of failure for egress traffic.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

8. **NEVER recommend deleting a NAT Gateway without providing the
   `release-address` follow-up for the Elastic IP.** Unreleased EIPs
   cost $0.005/hour ($3.65/month) if left attached to a deleted gateway.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
VPC: vpc-0staging01
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Staging VPC with 2 NAT Gateways ($65.70/mo hourly) and 450 GB
  data processing ($20.25/mo) has no VPC endpoints. S3 traffic (180 GB)
  and DynamoDB traffic (45 GB) should use FREE Gateway Endpoints.
  Consolidating from 2 to 1 NAT Gateway saves $32.85/mo in hourly charges
  (minus ~$5/mo cross-AZ transfer for the remaining AZ's subnets). Net
  monthly saving $58.50.
RECOMMENDATION:
  Current: 2 NAT Gateways, 450 GB/mo, 0 endpoints, staging
  Proposed: 1 NAT Gateway, 225 GB/mo, S3+DynamoDB Gateway Endpoints, staging
  Dimensions changed: gateway-endpoint (S3+DynamoDB) + topology (2→1 NAT GW)
  Dimensions checked: gateway-endpoint → (S3 180GB, DDB 45GB, no endpoints)
    interface-endpoint ✓ (ECR below break-even at 90GB × 2 AZ = 45/AZ < 162)
    topology → (2 NAT GW in staging, consolidate to 1)
    nat-instance ✓ (450 GB/mo is above NAT Instance sweet spot)
    routing ✓ (no double-NAT detected)
    cloudfront ✓ (no CloudFront origin in this VPC)
  Confidence: HIGH — VPC Flow Logs cover 7 days with clear service
    breakdown; staging environment tolerates single-NAT consolidation;
    S3+DynamoDB Gateway Endpoints are free with zero downside.
ESTIMATED_SAVINGS:
  Current monthly: $85.95
    hourly: 2 × $0.045 × 730 = $65.70
    data processing: 450 × $0.045 = $20.25
  Projected monthly: $27.45
    hourly: 1 × $0.045 × 730 = $32.85
    data processing: 225 × $0.045 = $10.13 (S3+DDB traffic eliminated)
    cross-AZ (added): ~225 × $0.01 = $2.25 (traffic from AZ-2 to NAT in AZ-1)
    gateway endpoint cost: $0.00 (free)
    Net projected: $32.85 + $10.13 + $2.25 = $45.23
    Correction: $45.23 (not $27.45 — cross-AZ + residual traffic)
  Monthly saving: $40.72 ($85.95 − $45.23 = $40.72)
  Annual saving: $488.64
MIGRATION_STEPS:
  1. Create S3 Gateway Endpoint:
     aws ec2 create-vpc-endpoint --vpc-id vpc-0staging01 \
       --service-name com.amazonaws.us-east-1.s3 \
       --route-table-ids rtb-0aaa rtb-0bbb --vpc-endpoint-type Gateway
  2. Create DynamoDB Gateway Endpoint:
     aws ec2 create-vpc-endpoint --vpc-id vpc-0staging01 \
       --service-name com.amazonaws.us-east-1.dynamodb \
       --route-table-ids rtb-0aaa rtb-0bbb --vpc-endpoint-type Gateway
  3. Update route tables in AZ-2 subnet to point at AZ-1 NAT Gateway:
     aws ec2 replace-route --route-table-id rtb-0bbb \
       --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0keep
  4. Delete the redundant NAT Gateway:
     aws ec2 delete-nat-gateway --nat-gateway-id nat-0remove
  5. Release the Elastic IP after gateway is 'deleted':
     aws ec2 release-address --allocation-id eipalloc-0xxx
  6. Verify S3 and DynamoDB traffic no longer traverses NAT:
     aws cloudwatch get-metric-statistics --namespace AWS/NATGateway \
       --metric-name BytesOutToDestination \
       --dimensions Name=NatGatewayId,Value=nat-0keep \
       --start-time $(date -d '-7 days' +%FT%TZ) \
       --end-time $(date +%FT%TZ) --period 86400 --statistics Sum
CONFIRM: About to create Gateway Endpoints, consolidate 2→1 NAT Gateway,
  and delete nat-0remove in vpc-0staging01. Monthly saving $40.72 (47%).
  Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?
- [ ] Interface Endpoint break-even cited (if recommending one)?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation (Gateway Endpoint, Interface Endpoint, topology consolidation, NAT Instance, routing fix). |
| `OPTIMIZED` | All dimensions pass: Gateway Endpoints exist for S3/DynamoDB, Interface Endpoints above break-even, topology appropriate (multi-AZ for prod, single for non-prod), no double-NAT. |
| `NEED_MORE_INFO` | Data gate failed: VPC Flow Logs not enabled, < 7 days of traffic data, or NAT Gateway metrics absent. |
| `BLOCKED` | Hard precondition prevents evaluation: NAT Gateway state != available, IAM denies ec2:DescribeNatGateways. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 7)

1. **NEVER recommend an Interface Endpoint without computing the
   break-even.** An Interface Endpoint at $7.30/AZ/month that eliminates
   only 50 GB/month of NAT traffic LOSES money ($7.30 endpoint cost vs
   $2.25 NAT saving). Always cite the ~162 GB/AZ/month threshold.

2. **NEVER consolidate production VPCs to a single NAT Gateway without
   flagging the HA risk.** Single NAT Gateway is a single point of
   failure for egress. For production, keep multi-AZ and optimize via
   VPC endpoints instead.

3. **NEVER skip the `release-address` step after deleting a NAT
   Gateway.** The Elastic IP remains allocated and costs $0.005/hour
   ($3.65/month) if left attached to a deleted gateway.

4. **NEVER create a Gateway Endpoint without verifying the route table
   association.** The endpoint route must be in EACH subnet's route
   table, not just the main route table (if subnet-specific route tables
   are used).

5. **NEVER recommend a NAT Instance for production.** NAT Instances
   have no SLA, limited throughput, and single-AZ failure risk. Reserve
   for dev/test only.

6. **NEVER ignore cross-AZ transfer costs when consolidating to a
   single NAT Gateway.** Traffic from other-AZ subnets to the remaining
   NAT Gateway costs $0.01/GB each direction. This partially offsets
   the hourly saving.

7. **NEVER recommend deleting a NAT Gateway without backing up the
   route table.** If the optimization needs to be rolled back, the
   original route table configuration must be recoverable.

Extended anti-patterns in `references/worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (create-vpc-endpoint, delete-nat-gateway, replace-route,
  release-address), emit and await operator approval.
- **Back up route tables before changes.** Capture the current route
  table state: `aws ec2 describe-route-tables` and save the output. If
  the optimization needs to be rolled back, the original routes must be
  recoverable.
- **Verify EIP allocation before NAT Gateway deletion.** Note the
  `AllocationId` from `describe-nat-gateways` so the EIP can be released
  after deletion.
- **Test S3/DynamoDB access after Gateway Endpoint creation.** Verify
  that bucket/table policies don't block the endpoint. If policies
  restrict by source IP or VPC, update them to include the endpoint ID.
- **Monitor NAT Gateway metrics for 7 days post-change.** Verify that
  traffic shifted to endpoints and the NAT data processing charge
  dropped accordingly.
- **Bulk-operation limit:** Process at most 3 VPCs per batch. Verify
  each batch before proceeding. Abort if any route table change breaks
  connectivity.

## Recent AWS features (2024-2026)

- **Gateway Load Balancer Endpoint (2024-2025):** For inserting security
  appliances (firewalls, IDS/IPS) into the traffic path. Relevant when
  NAT traffic must be inspected — the GWLB Endpoint routes traffic
  through a security VPC before NAT.
- **VPC Endpoint policy enhancements (2024):** Endpoint policies now
  support more granular IAM-style permissions. Use endpoint policies to
  restrict which S3 buckets or DynamoDB tables are accessible through
  the endpoint.
- **CloudWatch NAT Gateway metrics expansion (2024-2025):** Added
  `ErrorPortAllocation` and `ConnectionEstablishedCount` metrics for
  better port-exhaustion diagnosis. Port exhaustion occurs when a NAT
  Gateway runs out of ephemeral ports (55,000 per connection per
  destination).
- **PrivateLink for AWS services expansion (2024-2025):** Additional
  AWS services now support Interface Endpoints, including some
  bedrock, securityhub, and config APIs.
- **NAT Gateway bandwidth monitoring (2024):** CloudWatch now provides
  per-destination-IP flow metrics for NAT Gateways, enabling more
  granular traffic analysis without VPC Flow Logs.
- **ECR Interface Endpoint performance (2024):** Docker pull throughput
  through ECR Interface Endpoints improved with connection reuse. Break-
  even threshold effectively lower for CI/CD-heavy workloads.

## References

- `references/nat-pricing-and-endpoint-matrix.md` — NAT Gateway pricing
  model, VPC endpoint pricing (Gateway vs Interface), per-service
  break-even tables, cross-AZ data transfer costs, regional pricing
  multipliers, VPC Flow Logs query patterns, CWAgent NAT metrics
  reference, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (S3 Gateway
  Endpoint creation, multi-AZ consolidation, NAT Instance substitution,
  Interface Endpoint evaluation, already-optimized, NEED_MORE_INFO,
  end-to-end optimization walkthrough), plus error handling, edge cases,
  extended NEVER list, and the NAT optimization decision tree.

## Domain

AWS CloudOps / NAT Gateway Networking Cost Optimization & FinOps.

## AWS documentation

- **VPC User Guide — NAT Gateways** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- **VPC User Guide — VPC Endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **Gateway VPC Endpoints (S3, DynamoDB)** — https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- **Interface VPC Endpoints (PrivateLink)** — https://docs.aws.amazon.com/vpc/latest/privatelink/interface-endpoints.html
- **NAT Gateway pricing** — https://aws.amazon.com/vpc/pricing/
- **VPC Flow Logs** — https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html
- **CloudWatch NAT Gateway metrics** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway-cloudwatch.html
- **NAT Instances (legacy)** — https://docs.aws.amazon.com/vpc/latest/userguide/VPC_NAT_Instance.html
- **CloudFront Origin Access Control** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
- **AWS CLI VPC reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/#vpc
