---
description: Optimize AWS data transfer costs across seven dimensions — NAT Gateway (Gateway/Interface Endpoints), cross-AZ pinning, cross-region routing, internet egress (CloudFront/DX), VPC topology (peering vs Transit Gateway), RDS/Aurora Multi-AZ, and Direct Connect break-even. Includes per-dimension savings estimates and staged remediation.
nl_triggers:
  - "reduce data transfer cost"
  - "AWS surprise bill"
  - "cross-AZ data transfer"
  - "cross-region data transfer"
  - "NAT Gateway cost"
  - "VPC peering vs Transit Gateway"
  - "internet egress cost"
  - "Direct Connect break-even"
  - "VPC Gateway Endpoint"
  - "VPC Interface Endpoint"
  - "S3 Multi-Region Access Point"
  - "CUR data transfer audit"
  - "FinOps data transfer review"
  - "RDS Multi-AZ data transfer"
  - "Aurora cross-region replication cost"
  - "Transit Gateway cost"
  - "data transfer savings plan"
routes_to: data-transfer-optimizer
---

# /aws:optimize-data-transfer

Activate the `data-transfer-optimizer` skill and optimize AWS data
transfer costs across the seven cost dimensions.

## What it does

Reads Cost Explorer / CUR data-transfer USAGE_TYPE line items, VPC
topology (NAT Gateways, peering connections, Transit Gateway, VPC
endpoints), and service configurations (RDS Multi-AZ, S3 buckets,
Direct Connect), then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If CUR access denied,
   emits NEED_MORE_INFO for cost-quantification dimension.
2. **CUR breakdown** — identify top USAGE_TYPEs (NAT Gateway,
   cross-AZ, cross-region, internet egress, TGW, RDS).
3. **NAT Gateway** — VPC Gateway Endpoints for S3/DynamoDB (FREE);
   Interface Endpoints for high-volume services ($0.01/GB vs NAT
   $0.045/GB, break-even ~3TB/month per 3-AZ endpoint).
4. **Cross-AZ** — pin consumers to data-source AZ ($0.02/GB round
   trip savings; mitigate HA loss with standby ASG).
5. **Cross-region** — CloudFront for global viewers (free S3-to-CF
   egress); VPC peering for intra-region (free); S3 CRR only for
   DR/compliance.
6. **Internet egress** — CloudFront tiered pricing; S3 Multi-Region
   Access Points; Direct Connect for committed bandwidth.
7. **VPC topology** — peering (free intra-region) vs Transit Gateway
   ($0.02/GB); peering for ≤ 4 same-region VPCs; TGW for complex or
   cross-region.
8. **RDS/Aurora** — RDS Multi-AZ $0.01/GB; Aurora Multi-AZ free
   (storage-layer replication).
9. **Direct Connect** — break-even math: 1Gbps port saves vs
   internet egress above ~3TB/month steady.
10. **Impact estimation** — per-dimension monthly savings summed
    into a projected bill.
11. **Verdict** — OPPORTUNITY_FOUND (any dimension has a
    recommendation), OPTIMIZED (post-remediation), or
    ALREADY_OPTIMAL.

Emits a deterministic optimization block per account:

```text
TARGET: <account-id or topology-description>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: NAT=<GB and $>, cross-AZ=<GB and $>, ...
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (NAT Gateway): $<amount>
  Monthly (cross-AZ): $<amount>
  ...
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a CUR breakdown, network topology, or billing question and
ask any of:

- "why is our data transfer bill so high?"
- "should we use VPC peering or Transit Gateway?"
- "is our NAT Gateway cost normal?"
- "should we get Direct Connect?"
- "are VPC endpoints worth it?"
- "does Aurora save data transfer vs RDS?"
- "FinOps data transfer review"

A bare account ID + any data-transfer optimization verb also routes
here via the orchestrator.

## Inputs

- Cost Explorer / CUR: 30-day USAGE_TYPE breakdown filtered to
  data-transfer line items (NatGateway-Bytes,
  DataTransfer-Regional-Bytes, DataTransfer-Out-Bytes,
  DataTransfer-Egress-Cross-Region, TransitGateway-Bytes,
  RDS-DataTransfer).
- VPC topology: NAT Gateways (count, AZ), VPC peering connections,
  Transit Gateway attachments, VPC endpoints (type: Gateway/
  Interface, service).
- Service configurations: RDS instances (Multi-AZ status, engine),
  S3 buckets (region, replication config), Direct Connect ports.
- Optional: workload context (consumer AZ placement, traffic
  patterns, DR/compliance requirements).

## Outputs

- One optimization block per account.
- Per-dimension confidence with rationale.
- Per-dimension estimated monthly savings and annual total.
- Staged one-dimension-per-window migration plan with CLI commands.
- Rollback path (route table snapshot).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 3 Optimize specialist for data transfer cost).
- `/aws:optimize-cloudfront-cost` for CloudFront-specific cost
  optimization (Price Class, cache policy, Origin Shield). This
  skill identifies CloudFront as an opportunity and hands off.
- `/aws:optimize-nat-gateway-cost` for NAT Gateway-specific cost
  and HA optimization.
- `/aws:audit-cur-cost-usage-report` to audit the CUR setup before
  running data-transfer analysis.
