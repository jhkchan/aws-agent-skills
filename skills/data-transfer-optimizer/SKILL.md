---
name: data-transfer-optimizer
description: Optimizes AWS data transfer costs across seven dimensions — cross-AZ transfer ($0.01/GB each direction; pin consumers to data-source AZ), cross-region transfer ($0.02-0.09/GB; use CloudFront for global viewers, VPC peering for intra-region, S3 CRR only for DR), internet egress ($0.09/GB first 10TB; optimize via CloudFront with free S3-to-CF egress, S3 Multi-Region Access Points, Direct Connect), NAT Gateway data processing ($0.045/GB; route S3/DynamoDB via FREE VPC Gateway Endpoints), VPC peering (free intra-region) vs Transit Gateway ($0.02/GB), RDS Multi-AZ ($0.01/GB) vs Aurora (free replication), and Direct Connect break-even math. Emits OPPORTUNITY_FOUND with per-dimension savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when triaging surprise data-transfer bills, auditing CUR USAGE_TYPE line items, deciding peering vs TGW, or sizing Direct Connect.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation-document classification works from pasted Cost and Usage Report (CUR) line items and VPC/topology diagrams. Live-account optimization uses aws ce get-cost-and-usage (filtered by USAGE_TYPE for data-transfer dimensions), aws ec2 describe-vpc-peering-connections, describe -transit-gateways, describe-nat-gateways, describe-vpc-endpoints, aws s3api get-bucket-location, aws rds...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimizing AWS data transfer costs, triaging a surprise data-transfer bill, auditing CUR data-transfer line items, deciding between VPC peering and Transit Gateway, evaluating NAT Gateway alternatives (Gateway/Interface endpoints), sizing a Direct Connect commitment, evaluating S3 Multi-Region Access Points, or building a monthly data-transfer cost projection.
  when_not_to_use: CloudFront-specific cost optimization (use cloudfront-cost-optimizer for Price Class, cache policy, Origin Shield), EC2 instance rightsizing (use ec2-rightsizing-optimizer), S3 storage lifecycle optimization (use s3-lifecycle-optimizer), RDS instance rightsizing (use rds-cost-optimizer), NAT Gateway high-availability troubleshooting (use nat-gateway-troubleshooter). This skill focuses on data-transfer cost optimization across the seven networking dimensions, not on instance/storage rightsizing or CloudFront-specific decisions.
  activation_triggers: reduce data transfer cost, AWS surprise bill, cross-AZ data transfer, cross-region data transfer, NAT Gateway cost, VPC peering vs Transit Gateway, internet egress cost, Direct Connect break-even, VPC Gateway Endpoint, VPC Interface Endpoint, S3 Multi-Region Access Point, CUR data transfer audit, FinOps data transfer review, RDS Multi-AZ data transfer, Aurora cross-region replication cost, Transit Gateway cost
  invocation_schema: 'Input: either (a) an AWS account context with access to Cost Explorer / CUR, (b) a pasted Cost and Usage Report extract filtered to data-transfer USAGE_TYPEs, OR (c) a network topology description (VPCs, regions, AZs, NAT Gateways, VPC peering connections, Transit Gateway, Direct Connect, S3 buckets, RDS instances). Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per account (or per top-cost dimension), where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION lists the per-dimension actions (cross-AZ, cross-region, internet egress, NAT Gateway, VPC topology, RDS, Direct Connect).'
  invocation_example: "# Minimal valid input (offline CUR classification):\nAccount: 123456789012\nRegion: us-east-1 primary; us-west-2 secondary\nMonthly data transfer costs (Cost Explorer, last 30 days):\n  - NAT Gateway DataProcessed: 12,000 GB × $0.045 = $540\n  - EC2 cross-AZ data transfer: 8,000 GB × $0.02 = $160\n  - S3 cross-region replication: 1,500 GB × $0.02 = $30\n  - CloudFront egress (already optimized)\nVPC topology:\n  - VPC-A in us-east-1 (3 AZs; primary app)\n  - VPC-B in us-east-1 (3 AZs; analytics)\n  - VPC peering: A↔B (intra-region, free)\n  - Transit Gateway: not in use\nNAT Gateway: 1 per AZ in VPC-A (3 total)\nVPC endpoints: only S3 Gateway Endpoint in VPC-A\nWorkload context: microservices in VPC-A pulling from S3 and\nDynamoDB; analytics EMR cluster in VPC-B reading same S3\nbuckets and writing cross-AZ back to VPC-A database.\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: data transfer, cross-AZ, cross-region, NAT Gateway, VPC peering, Transit Gateway, internet egress, S3 Transfer Acceleration, Direct Connect, VPC Gateway Endpoint, VPC Interface Endpoint, PrivateLink, S3 Multi-Region Access Point, RDS Multi-AZ, Aurora replication, Cost and Usage Report, CUR, FinOps, surprise bill
  tags: data-transfer, networking, cost-optimization, finops, vpc
---

# Data Transfer Optimizer

## Quick start

Quick-start summaries of the seven cost dimensions (NAT Gateway trap, cross-AZ pinning, CloudFront egress math, peering vs TGW, Aurora vs RDS Multi-AZ) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the compressed rules of thumb behind each recommendation.

## Mindset

Mindset framing (the cheapest transfer is the one that never happens; cross-AZ → cross-region → internet escalation multipliers) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when internalizing why topology granularity drives the bill.

## Philosophy

Philosophy (NAT default-route trap, cross-AZ per-hop charge, negotiable egress rates, recurring per-GB topology consequences) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the expert rationale behind the verdict thresholds.

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

Pre-flight data-gate intro (Cost Explorer + VPC topology + service configuration) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before pulling billing and topology data.

### Required data sources

The four required data-source CLI blocks (Cost Explorer query, VPC topology describe calls, bucket-region sweep, Direct Connect inventory) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before any optimization decision.

### Data-quality short-circuits

Data-quality short-circuit table (CE access denied, window < 14 days, consolidated billing, missing topology, hidden CRR) and the Cost-Explorer-vs-CloudWatch arbitration rule moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the input data is incomplete or self-contradictory.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Step 0 expert knowledge (NAT hourly+per-GB charging, Gateway vs Interface endpoint economics, bidirectional cross-AZ billing, TGW attachment costs, CRR as a cost, CloudFront egress math, DX break-even, Savings Plans, topology decision gates) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand — each gotcha reroutes the recommendation away from the obvious choice.

### Step 1: Validate input and data sufficiency

Step 1 NEED_MORE_INFO branch (missing CUR data output template with IAM policy and Athena CUR query, partial-verdict rule for missing topology) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when cost data is unavailable or topology is incomplete.

### Step 2: Cost Explorer reconciliation

Step 2 Cost Explorer reconciliation CLI (USAGE_TYPE_GROUP-filtered get-cost-and-usage), the USAGE_TYPE mapping table (NatGateway-Bytes, DataTransfer-Regional-Bytes, Out-Bytes, CRR, RDS, TGW), and the >50% Pareto deep-dive rule moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when pulling and classifying the 30-day data-transfer breakdown.

### Step 3: Cost classification

Step 3 cost-profile classification table (NAT-heavy, internet-egress heavy, cross-AZ heavy, cross-region heavy, TGW-heavy, RDS-heavy, mixed) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deciding which dimension to emphasize first.

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

Step 4 cross-AZ detection commands (describe-flow-logs plus the Athena VPC Flow Logs subnet-pair query) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when quantifying cross-AZ traffic before pinning consumers.

Worked AZ-pinning example (100GB/day RDS reader fleet, $40.20/month cross-AZ cost eliminated, failover mitigation) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when estimating AZ-pinning savings and the HA trade-off.

### Step 5: NAT Gateway optimization

The biggest single lever for surprise bills.

Step 5 NAT Gateway inventory CLI (describe-nat-gateways plus the per-NAT CloudWatch BytesOutToDestination loop) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when identifying NAT Gateways and their processed volume.

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

Worked Gateway Endpoint savings example (5TB/month S3-through-NAT, $225/month saved for free) and worked Interface Endpoint break-even example (2TB/month SQS, $129.50 vs $90 — loses below ~3.1TB/month) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when sizing endpoint alternatives against NAT.

### Step 6: Internet egress optimization

Internet egress is $0.09/GB first 10TB, tiered lower after. The
cheapest alternative is to reduce the egress through a different
network path.

The Step 6 internet-egress decision matrix (S3-to-global → CloudFront, known regions → S3 MRAP, EC2/ALB → CloudFront, cross-region → peering, on-prem sync → DX, >50TB → DX 10Gbps + Savings Plan, burst → no commit) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the per-egress-pattern recommendation and savings columns.

Worked CloudFront crossover example (5TB/month S3 egress, $450 → ~$426, cache-hit and APAC-tier effects) and worked Direct Connect crossover example (50TB/month, ~$4,400 internet vs $3,000 DX + Savings Plan) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when deciding between CloudFront, S3 MRAP, and Direct Connect.

### Step 7: VPC topology optimization

VPC peering (free intra-region) vs Transit Gateway ($0.02/GB).

The Step 7 VPC-topology decision matrix (hub-and-spoke by VPC count and traffic volume, cross-region, mesh, centralized egress/inspection → TGW; ≤4 intra-region → peering) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the full peering-vs-TGW branch table.

Worked peering-vs-TGW example (5-VPC full mesh, $222.50/month TGW vs free peering, ops-burden trade-off) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when choosing topology for small fleets.

Step 7 TGW cost-reduction patterns (convert low-traffic attachments to peering, centralize only egress, AZ-pin to cut TGW hops) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when TGW is already deployed and the bill is high.

### Step 8: RDS/Aurora data transfer optimization

RDS Multi-AZ replication has different cost models.

The Step 8 RDS/Aurora decision matrix (Aurora Multi-AZ free, RDS Multi-AZ $0.01/GB, read replicas, Aurora Global Database, Serverless v2, self-managed EC2) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the per-database-setup recommendation rows.

Worked Aurora migration math (5TB/month high-write RDS Multi-AZ, $50/month replication charge avoided) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when weighing RDS → Aurora migration.

### Step 9: Direct Connect evaluation

For high-volume steady-state egress, Direct Connect beats internet
egress on per-GB rate.

Step 9 DX break-even formula block (port cost / (internet rate − DX rate)) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when computing DX break-even for a specific port speed.

Step 9 DX port-speed break-even table (50 Mbps → 100 Gbps vs $0.09 and $0.05 internet tiers) with the recommend-DX-above-break-even rule moved verbatim to [references/data-transfer-pricing-reference.md](references/data-transfer-pricing-reference.md).
Load on demand when comparing DX port speeds against egress volume.

### Step 10: Impact estimation

Sum the per-dimension savings into a projected monthly bill.

Step 10 impact-estimation formula (current vs projected monthly data-transfer bill) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when summing per-dimension savings into a projection.

Step 10 us-east-1 pricing notes (all per-GB and hourly rates for the seven dimensions) moved verbatim to [references/data-transfer-pricing-reference.md](references/data-transfer-pricing-reference.md).
Load on demand when pricing the projection.

For per-region pricing precision, always check
`https://aws.amazon.com/ec2/pricing/on-demand/` (Data Transfer
section) for the current matrix.

### Step 11: Final verdict

Step 11 final-verdict aggregation rules (OPPORTUNITY_FOUND on any dimension, OPTIMIZED/ALREADY_OPTIMAL gating, per-dimension NEED_MORE_INFO) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when aggregating verdicts; the verdict semantics table stays inline.

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

Worked example (already optimal account, all seven dimensions verified) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the shape of a clean ALREADY_OPTIMAL block.

### Worked example — NEED_MORE_INFO (no CUR access)

Worked example (NEED_MORE_INFO with qualitative topology findings and the CUR grant/Athena remediation) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the shape of a NEED_MORE_INFO block.

## Verdict semantics — reconciling the verdict_shape

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one of the seven dimensions has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CUR line items confirm the new pattern lands within target bands. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND Data Transfer Savings Plan evaluated. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed for one or more dimensions: CUR access denied, topology missing, observation window < 14 days. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## NAT Gateway break-even formula (concrete)

NAT Gateway break-even formula (per-GB + hourly cost model, interface-endpoint break-even ≈ 1042 × endpoints × AZs GB/month, per-service break-even table) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when sizing endpoint alternatives against NAT.

## Error handling — CLI and data-source failures

Error-handling tables (Cost Explorer failures, VPC API failures, service-specific API failures) and aggregate retry/backoff behavior moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a data source fails mid-analysis.

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

The 60-second triage (six ordered checks: CE breakdown, endpoint inventory, NAT count, topology, RDS Multi-AZ status, egress volume) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before deep-diving any single dimension.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (CONFIRM gate, route-table snapshot, one dimension per window, endpoint propagation verification, NAT removal safety, 3-VPC batch limit, RDS failover window, DX billing-account note) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any remediation CLI.

## Remediation guidance

Remediation guidance per opportunity dimension (Gateway/Interface Endpoints, AZ-pinning ASG changes, TGW→peering mesh, CloudFront hand-off, RDS migration, DX hand-off, ALREADY_OPTIMAL follow-up) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when emitting MIGRATION_STEPS for a found opportunity.

## Deep reference: AWS data transfer pricing matrix

Deep pricing matrix (cross-AZ, cross-region pairs, internet egress tiers, NAT Gateway, VPC endpoints, TGW, Direct Connect ports) moved verbatim to [references/data-transfer-pricing-reference.md](references/data-transfer-pricing-reference.md).
Load on demand for per-dimension rate lookups.

## Recent AWS features (2024-2026)

Recent AWS features (Data Transfer Savings Plans, S3 MRAP, Aurora Global Database, VPC endpoint policies, Verified Access, CloudFront KeyValueStore, TGW Network Manager, IPv6 cross-region peering) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before recommending 2024-2026 capabilities.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Quick start, Mindset, Philosophy, Step 0 non-obvious behaviours, data-quality short-circuits, Step 3 classification, the Step 6/7/8 decision matrices, TGW reduction patterns, DX break-even math, Step 11 aggregation detail, NAT break-even formula, and Recent AWS features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — data-gate CLI blocks, Step 2/4/5 CLI listings, USAGE_TYPE mapping, 60-second triage, and pre-flight safety checks moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — CLI/data-source failure tables and remediation guidance; [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (already optimal, NEED_MORE_INFO) and per-step cost math moved from SKILL.md
- [references/data-transfer-pricing-reference.md](references/data-transfer-pricing-reference.md) — pricing tables and break-even data (pre-existing; extended with the SKILL.md pricing matrix and us-east-1 notes)

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
