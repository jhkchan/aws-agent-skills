---
description: Optimises NAT Gateway cost through VPC endpoint design (free Gateway endpoints for S3/DynamoDB, break-even maths for Interface endpoints), topology selection (single vs multi-AZ), and NAT Instance evaluation for dev/test. Emits a deterministic VERDICT, endpoint-creation payload, and dollar savings estimate per VPC.
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
  - "NAT Gateway cost review"
routes_to: nat-gateway-cost-optimizer
---

# /aws:optimize-nat-gateway-cost

Activate the `nat-gateway-cost-optimizer` skill and design a cost-optimised
VPC endpoint and NAT topology plan for one or more VPCs, with a dollar
savings estimate and the exact `create-vpc-endpoint` payload.

## What it does

Reads a VPC configuration (NAT Gateways, route tables, existing endpoints,
Cost Explorer NAT spend, VPC Flow Logs traffic breakdown) and applies the
priority-ordered four-dimension analysis:

1. Pre-flight VPC metadata gate — short-circuit VPCs with no NAT Gateway
   spend, misconfigured Flow Logs, or transient gateway states.
2. Gateway endpoints for S3 and DynamoDB (FREE — always create if traffic
   exists).
3. Interface endpoints for high-traffic AWS services (ECR, SSM, STS,
   Secrets Manager, CloudWatch, KMS) — break-even maths at ~160 GB/month
   per AZ.
4. NAT topology (single vs multi-AZ) — cross-AZ transfer cost modelling
   against base-cost saving.
5. NAT Instance substitution (dev/test only) — fixed-cost EC2 host with
   reliability warning.
6. Aggregation — emit the highest-leverage recommendation across all
   applicable dimensions.

Emits a deterministic VERDICT per VPC:

```text
VPC: <vpc-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences citing the highest-leverage dimension and step number>
RECOMMENDATION: <endpoint-creation and topology-change actions>
SAVINGS:
  CURRENT_MONTHLY: $<X.XX>
  PROJECTED_MONTHLY: $<Y.YY>
  MONTHLY_SAVING: $<X.XX - Y.YY>
  ANNUAL_SAVING: $<12 × monthly>
  CAVEATS: <Interface endpoint break-even, NAT Instance reliability warnings>
IMPLEMENTATION: <exact create-vpc-endpoint CLI + verification>
```

## When to invoke

Paste a VPC configuration (or just a VPC ID) and ask any of:

- "why is my NAT Gateway bill so high?"
- "should I add VPC endpoints?"
- "can I reduce from 3 NAT Gateways to 1?"
- "is a NAT Instance cheaper for my dev environment?"
- "how much would S3 and DynamoDB Gateway endpoints save?"
- "ECR traffic through NAT — worth an Interface endpoint?"

A bare VPC ID + any optimise verb ("optimise NAT cost", "reduce NAT bill")
also routes here via the orchestrator.

## Inputs

- VPC configuration: NAT Gateways (`describe-nat-gateways`), route tables
  (`describe-route-tables`), existing endpoints (`describe-vpc-endpoints`).
- Cost Explorer NAT Gateway spend (last 30 days): separate base (hourly)
  from data-processing (per-GB) via the USAGE_TYPE dimension.
- VPC Flow Logs (last 7 days): per-service traffic breakdown filtered by
  the NAT Gateway ENI.
- Environment context: production vs dev/test/staging (affects topology and
  NAT Instance gating).
- For savings estimates: monthly GB per service (S3, DynamoDB, ECR, etc.).

## Outputs

- One VERDICT block per VPC.
- A full endpoint-creation plan combining all applicable dimensions (Gateway
  endpoints, Interface endpoints above break-even, topology consolidation,
  NAT Instance substitution).
- A dollar savings estimate with explicit caveats: Interface endpoint break-
  even thresholds, NAT Instance reliability warnings, cross-region S3
  exclusion.
- Implementation steps including exact `create-vpc-endpoint`,
  `delete-nat-gateway`, `replace-route`, and `release-address` CLI commands.
- Route-table backup instructions for rollback safety.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for NAT Gateway / networking cost).
- `/aws:optimize-ec2-rightsizing` for the compute cost-optimisation sibling
  — NAT Gateway and EC2 are typically among the largest variable cost lines.
- `/aws:audit-vpc-flow-logs` for the Flow Logs configuration audit that
  enables the traffic breakdown this skill relies on.
