---
description: Optimises NAT Gateway cost through traffic analysis (BytesOutToDestination, VPC Flow Logs), Gateway Endpoint creation (S3, DynamoDB — FREE), Interface Endpoint evaluation (SSM, STS, ECR, SQS — per-AZ break-even), topology consolidation (single vs multi-AZ for non-prod), NAT Instance substitution (dev/test), routing optimization (double-NAT detection), and CloudFront/PrivateLink patterns with monthly savings estimates.
nl_triggers:
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
  - "cross-AZ data transfer cost"
  - "subnet routing optimization"
  - "double NAT detection"
  - "S3 Gateway Endpoint free"
  - "CloudFront origin VPC endpoint"
  - "NAT Gateway hourly charge"
  - "consolidate NAT Gateways"
routes_to: nat-gateway-traffic-optimizer
---

# /aws:optimize-nat-gateway-traffic

Activate the `nat-gateway-traffic-optimizer` skill and design a cost-
optimised VPC endpoint and NAT topology plan for one or more VPCs, with
a dollar savings estimate and the exact `create-vpc-endpoint` payload.

## What it does

Reads a VPC configuration (NAT Gateways, route tables, existing
endpoints, Cost Explorer NAT spend, VPC Flow Logs traffic breakdown)
and applies the priority-ordered six-dimension analysis:

1. **Pre-flight VPC metadata gate** — short-circuit VPCs with no NAT
   Gateway spend, no Flow Logs, or transient gateway states.
2. **Gateway endpoints for S3 and DynamoDB** (FREE — always create if
   traffic exists). No hourly charge, no per-GB charge, persistent
   route table entry.
3. **Interface endpoints for high-traffic AWS services** (ECR, SSM,
   STS, SQS, Secrets Manager, CloudWatch Logs, KMS) — break-even at
   ~162 GB/month per AZ ($7.30/AZ/month endpoint cost vs $0.045/GB
   NAT data processing).
4. **NAT topology** (single vs multi-AZ) — non-prod consolidation saves
   $32.85/month per AZ removed, minus cross-AZ transfer cost ($0.01/GB
   each direction).
5. **NAT Instance substitution** (dev/test only) — t3.micro at $7.59/mo
   vs NAT Gateway at $32.85/mo + $0.045/GB. Crossover at ~800 GB/month.
6. **Routing optimization** — double-NAT detection (route table audit),
   CloudFront-to-origin via VPC endpoint, PrivateLink for SaaS API
   traffic.
7. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation) or OPTIMIZED (all dimensions pass).

Emits a deterministic optimization block per VPC:

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences citing the highest-leverage dimension and step>
RECOMMENDATION:
  Current: <NAT GW count>, <monthly GB>, <endpoints>, <environment>
  Proposed: <NAT GW count>, <remaining GB>, <new endpoints>, <topology>
  Dimensions changed: <gateway-endpoint | interface-endpoint | topology | nat-instance | routing | cloudfront>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a VPC configuration (or just a VPC ID) and ask any of:

- "why is my NAT Gateway bill so high?"
- "should I add VPC endpoints?"
- "can I reduce from 3 NAT Gateways to 1?"
- "is a NAT Instance cheaper for my dev environment?"
- "how much would S3 and DynamoDB Gateway endpoints save?"
- "ECR traffic through NAT — worth an Interface endpoint?"
- "detect double-NAT in my route tables"

A bare VPC ID + any optimise verb ("optimise NAT cost", "reduce NAT
bill") also routes here via the orchestrator.

## Inputs

- VPC configuration: NAT Gateways (`describe-nat-gateways`), route
  tables (`describe-route-tables`), existing endpoints
  (`describe-vpc-endpoints`).
- Cost Explorer NAT Gateway spend (last 30 days): separate base
  (hourly) from data-processing (per-GB) via the USAGE_TYPE dimension.
- VPC Flow Logs (last 7 days): per-service traffic breakdown filtered
  by the NAT Gateway ENI.
- Environment context: production vs dev/test/staging (affects topology
  and NAT Instance gating).
- For savings estimates: monthly GB per service (S3, DynamoDB, ECR, etc.).

## Outputs

- One optimization block per VPC.
- A full endpoint-creation plan combining all applicable dimensions
  (Gateway endpoints, Interface endpoints above break-even, topology
  consolidation, NAT Instance substitution).
- A dollar savings estimate with explicit caveats: Interface endpoint
  break-even thresholds, NAT Instance reliability warnings, cross-AZ
  transfer costs, cross-region S3 exclusion.
- Implementation steps including exact `create-vpc-endpoint`,
  `delete-nat-gateway`, `replace-route`, and `release-address` CLI
  commands.
- Route-table backup instructions for rollback safety.
- EIP release step (always after NAT Gateway deletion).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for NAT Gateway / networking cost).
- `/aws:optimize-ec2-instance-rightsizer` for the compute cost-
  optimisation sibling — NAT Gateway and EC2 are typically among the
  largest variable cost lines.
- `/aws:optimize-data-transfer` for broader data transfer cost
  optimization including cross-region and Transit Gateway.
