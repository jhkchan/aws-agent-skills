---
description: Optimise Route 53 DNS cost through hosted zone inventory reduction (unused zone deletion, low-traffic zone consolidation), health check analysis (endpoint vs calculated vs alarm-based), routing policy surcharge removal (latency-based and geolocation to weighted/simple), traffic policy replacement, DNSSEC cost impact analysis, and query logging volume reduction with monthly savings estimates.
nl_triggers:
  - "optimise Route 53 cost"
  - "Route 53 hosted zone audit"
  - "Route 53 unused zones"
  - "Route 53 health check cost"
  - "Route 53 traffic policy cost"
  - "Route 53 DNSSEC cost"
  - "Route 53 query logging cost"
  - "Route 53 routing policy cost"
  - "Route 53 FinOps savings"
  - "reduce DNS bill"
  - "hosted zone consolidation"
  - "calculated health checks"
  - "DNS query volume analysis"
  - "Route 53 monthly savings estimate"
  - "private hosted zone cost"
  - "Route 53 zone inventory cleanup"
routes_to: route53-cost-optimizer
---

# /aws:optimize-route53-cost

Activate the `route53-cost-optimizer` skill and optimize a Route 53
DNS footprint across seven dimensions: hosted zone inventory, health
check configuration, query volume and routing policy, traffic policies,
private zone VPC associations, DNSSEC overhead, and query logging
volume.

## What it does

Reads a hosted zone's CloudWatch metrics (DNSQueries,
HealthCheckPercentHealthy), Route 53 zone inventory, health check
inventory, traffic policy inventory, and query logging configs, then
applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If DNSQueries metrics are
   absent, cross-check record sets and dependent services.
2. **Hosted zone inventory** — detect zones with 0 queries, no ACM/SES
   dependencies. Delete unused zones. Consolidate low-traffic domains.
3. **Health check analysis** — convert redundant endpoint checks to
   calculated health checks (free). Eliminate checks monitoring deleted
   resources.
4. **Query volume and routing policy** — remove latency-based or
   geolocation routing surcharges when traffic is single-region. Switch
   to weighted or simple routing (no surcharge).
5. **Traffic policy evaluation** — replace $50/month traffic policies
   with record-level weighted routing when the policy logic is simple.
6. **Private zone VPC audit** — detect orphaned private zones with no
   VPC associations.
7. **DNSSEC cost impact** — disable DNSSEC on low-traffic zones without
   compliance requirements to eliminate the $1/month KMS key cost.
8. **Query logging volume** — reduce CloudWatch ingestion cost by
   disabling or sampling logging on high-volume zones.
9. **Impact estimation** — monthly + annual savings, assumptions
   documented.
10. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation), OPTIMIZED (applied and verified), or
    ALREADY_OPTIMAL.

Emits a deterministic optimization block per zone:

```text
TARGET: <zone-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <zone/config description>
  Proposed: <zone/config description>
  Dimensions changed: <zones | health_checks | routing | traffic_policy | dnssec | logging>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
REMEDIATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Route 53 zone's metrics and ask any of:

- "optimise this Route 53 zone's cost"
- "is this hosted zone still needed?"
- "should I convert endpoint health checks to calculated?"
- "is latency-based routing worth the surcharge?"
- "should I keep this traffic policy?"
- "is DNSSEC costing us for no benefit?"
- "is DNS query logging too expensive?"
- "Route 53 fleet cost optimization review"

A bare zone name + any optimization verb also routes here via the
orchestrator.

## Inputs

- Zone metadata: zone ID, domain name, zone type (public/private),
  region, record count.
- CloudWatch metrics (last 14-30 days):
  - `DNSQueries` (Sum) per zone
  - `HealthCheckPercentHealthy` (Average)
- Optional: health check inventory (type, count, interval).
- Optional: routing policy per record (simple, weighted, latency,
  geolocation, failover).
- Optional: traffic policy inventory (count, attached records, rules).
- Optional: DNSSEC status (enabled/disabled, KMS key ARN).
- Optional: query logging config (enabled, log group, retention).
- Optional: ACM certificate cross-reference for dependency check.

## Outputs

- One optimization block per zone.
- Confidence level with rationale.
- Estimated monthly and annual savings, broken down by dimension.
- Specific remediation steps with CLI commands.
- Seven-dimension check (zones, health checks, routing, traffic policy,
  DNSSEC, logging, private zones).
- Zone backup step before any deletion.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Route 53 DNS cost).
- `/aws:audit-route53-records` for record-level auditing (not cost
  optimization).
- `/aws:troubleshoot-route53-health-check` for health check functional
  debugging.
