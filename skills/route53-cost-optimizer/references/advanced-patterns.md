# Advanced Patterns — Route 53 Cost Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset — four cost principles

Route 53 cost optimization is an inventory and configuration exercise,
not a capacity-planning problem. The goal is to eliminate zones, health
checks, and logging volume that no longer serve traffic — not to tune
DNS performance.

Four principles guide every recommendation:

- **Zones are the fixed cost.** Every hosted zone bills monthly
  regardless of query volume. The highest-leverage action is inventory
  reduction: delete unused zones and consolidate low-traffic domains
  into a shared zone with subdomain records.
- **Health checks are the variable cost.** Each endpoint health check
  costs $0.50/month. Accounts with 100+ checks spend $600+/year on
  monitoring alone. Calculated health checks (free) can replace
  endpoint checks for composite monitoring.
- **Routing policy surcharges are the hidden cost.** A zone using
  latency-based routing at 500M queries/month pays $100 extra vs simple
  routing for the same volume. Weighted routing has no surcharge.
- **Query logging is the wildcard.** CloudWatch Logs charges $0.50/GB
  ingested. A high-traffic zone logging every query can generate
  terabytes per month. Sample, filter, or disable logging for
  non-compliance zones.

## Configuration dependency graph

```
HostedZone ─┬─ DNSSEC ──── KMS Key ($1/month)
            ├─ QueryLogging ── CloudWatch Logs ($0.50/GB ingested)
            ├─ Records ──── RoutingPolicy ──┬─ Simple (base rate)
            │                               ├─ Weighted (base rate)
            │                               ├─ Latency (+$0.20/B)
            │                               ├─ Geolocation (+$0.30/B)
            │                               └─ TrafficPolicy ($50/month)
            ├─ HealthChecks ─┬─ Endpoint ($0.50/month)
            │                ├─ Calculated (FREE)
            │                └─ Alarm-based ($0.50/month)
            └─ VPC Associations (Private Hosted Zones, no surcharge)
```

Each edge in this graph is a potential cost lever. Walk every node
before emitting a verdict.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Calculated health checks are free but have a nesting limit.** A
  calculated health check can monitor up to 25 other health checks. You
  cannot nest calculated health checks inside other calculated health
  checks — one level only.
- **DNSSEC signing uses a KMS key that costs $1/month.** The key bills
  independently of DNS query volume. A zone with DNSSEC enabled pays
  $0.50 (zone) + $1.00 (KMS key) = $1.50/month minimum.
- **Hosted zone deletion requires NS record delegation removal first.**
  If the domain registrar still points NS records at the zone, deleting
  the zone causes DNS resolution failure. Update the registrar to point
  elsewhere before deleting.
- **Traffic policies charge per policy, not per zone.** A single traffic
  policy applied to multiple records costs $50/month once. The cost
  trigger is policy CREATION and attachment, not the number of records.
- **Latency-based routing surcharge applies to ALL queries to the zone.**
  If any record in a zone uses latency-based routing, the surcharge
  applies to queries for that specific record set, not the entire zone.
- **Private hosted zones have no query surcharge.** Private DNS queries
  (VPC-resolved) are included in the hosted zone cost. No per-query
  billing for private zones.
- **Query logging charges for ingestion, not storage.** CloudWatch Logs
  bills $0.50/GB ingested plus retention storage. Disabling logging
  eliminates ingestion cost immediately.
- **Domain transfer does not reduce Route 53 cost.** Domain registration
  is billed separately from hosted zones. Transferring a domain between
  registrars does not affect hosted zone billing.
- **Health check interval does not affect cost.** Whether a check runs
  every 10 seconds or every 30 seconds, the price is $0.50/month flat.
  Reducing interval is a reliability decision, not a cost decision.
- **The first 25 hosted zones cost $0.50/month each; zones 26+ cost
  $0.10/month each.** Consolidation savings diminish after 25 zones
  unless the zone is entirely unused.

## Step 1 — unused-zone detection and consolidation procedures

**Unused zone detection:**
```
For each zone:
  1. Check DNSQueries metric over 30 days (Sum)
  2. If Sum == 0 → candidate for deletion
  3. Cross-check record sets for ACM validation CNAMEs
  4. Cross-check dependent services (SES, MX, API Gateway custom domain)
  5. If no dependents → FURTHER_OPTIMIZATION_AVAILABLE (delete zone)
```

**Zone consolidation:**
```
For domains owned by the same organization:
  1. Identify zones with < 10,000 queries/month
  2. Check if the domain is a subdomain of another active zone
  3. If zone2.example.com has its own zone AND example.com zone exists:
     → Move records to example.com zone as subdomain records
     → Delete zone2.example.com zone
     → Saving: $0.50/month per consolidated zone
```

## Step 2 — calculated health check conversion procedure

**Calculated health check conversion:**
```
If 3+ endpoint checks feed into a single DNS failover record:
  → Create a calculated health check (FQDN = the failover target)
  → Set the calculated check to monitor the endpoint checks
  → Point the failover record at the calculated check
  → The calculated check is FREE (saves $0.50/month per replaced check)
```

## Step 2 — redundancy elimination guidance

**Redundancy elimination:**
- If an ALB has its own health check AND Route 53 also checks the ALB
  endpoint, the Route 53 check is redundant when the target is an ALB
  with target group health checks. Evaluate whether the Route 53 check
  adds value (DNS-level failover) or merely duplicates ALB monitoring.
- Health check interval reduction does NOT save money. Whether 10s or
  30s, the cost is $0.50/month. Do not recommend interval changes for
  cost reasons.

## Step 3 — routing policy evaluation procedure

**Routing policy evaluation:**
```
For each zone using latency-based or geolocation routing:
  1. Check query volume for the policy-bearing records
  2. If queries < 1M/month from a single region:
     → Latency-based routing adds no value (single-region traffic)
     → Recommend switching to weighted or simple routing
     → Saving: removes the +$0.20/B or +$0.30/B surcharge
  3. If queries > 100M/month across multiple regions:
     → Latency-based routing is justified (multi-region latency)
     → Keep; evaluate other dimensions
```

## Step 3 — per-zone query ranking procedure

**Per-zone query ranking:**
```
Rank zones by monthly query volume (descending).
Focus optimization on the top 5 zones by volume × surcharge rate.
A zone at 500M latency-based queries costs $100/month in surcharges alone.
```

## Step 5 — private zone audit procedure

**Private zone audit:**
```
For each private hosted zone:
  1. List VPC associations (aws route53 get-hosted-zone --id <zone>)
  2. If 0 VPC associations → orphaned zone → delete
  3. If associated VPC is deleted → remove association, then delete zone
  4. If 2+ private zones overlap the same VPC and domain → consolidate
```

## Step 7 — query logging audit procedure

**Logging audit:**
```
For each zone with query logging enabled:
  1. Estimate log volume (queries/month × ~200 bytes/query)
  2. If volume > 50 GB/month AND no compliance requirement:
     → Recommend disabling logging or sampling
     → Saving: $0.50/GB × monthly_GB
  3. If retention > 90 days AND logs are never queried:
     → Reduce retention to 7-30 days
     → Saving: storage cost reduction (incremental)
```

## Expert heuristic (domain expert rules of thumb)

Three rules that a Route 53 cost expert applies instinctively:

1. **Hosted zone consolidation for low-traffic domains.** If the
   organization owns multiple domains with < 10K queries/month each,
   consolidate them into a single parent zone using subdomain records.
   Each eliminated zone saves $6/year minimum. The break-even point
   for consolidation effort is ~3 zones.

2. **Health check interval does not scale cost — check count does.** The
   cost lever is the NUMBER of endpoint checks, not the interval. A
   single check at 10s costs the same as at 30s. To reduce health check
   spend, reduce check COUNT by converting endpoint checks to calculated
   checks (free, nesting limit 25 per calculated check).

3. **Calculated health check nesting limit is one level.** A calculated
   health check can monitor up to 25 other health checks, but those 25
   cannot themselves be calculated checks. This means the maximum
   "fan-in" is 25 endpoint checks per calculated check. For > 25
   endpoints, you need multiple calculated checks plus a parent record
   that references both — but the parent record itself cannot use a
   calculated check of calculated checks. Plan the check topology
   accordingly.

## Recent AWS features (2024-2026)

- **DNSSEC signing GA (2024):** All public hosted zones support DNSSEC
  signing via KMS key. Enabled per-zone with key-signing-key.
- **Route 53 traffic policies visual editor (2024-2025):** Enhanced
  policy editor supporting geoproximity with bias tuning. Still $50/month
  per policy.
- **Calculated health checks enhancement (2024):** Increased monitoring
  capacity to 25 child checks per calculated check (up from 10).
- **CloudWatch Logs insights for Route 53 (2024-2025):** Query DNS log
  data directly in CloudWatch Logs Insights for top queried domains,
  NXDOMAIN rates, and source IP analysis.
- **Route 53 Resolver DNS Firewall (2024):** Domain filtering on
  Resolver queries. Separate billing from hosted zone cost optimization.
- **Cost Optimization Hub Route 53 recommendations (2025-2026):**
  Automated detection of unused hosted zones and idle health checks.
  Use as input to this skill.
