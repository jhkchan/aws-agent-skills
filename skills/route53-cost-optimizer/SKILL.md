---
name: route53-cost-optimizer
description: 'Optimises Amazon Route 53 DNS cost across seven dimensions: hosted zone cost reduction (consolidating low-traffic domains into a single zone, detecting and removing unused zones that still bill $0.50/month), health check cost analysis (endpoint health checks at $0.50/check/month vs calculated health checks which are free vs alarm-based health checks), DNS query volume analysis per zone (tiered query pricing at $0.40 per billion standard queries, with latency-based routing at +$0.20/B and geolocation at +$0.30/B over
  base), traffic policy vs simple routing cost (traffic policies are $50/month flat vs free simple routing), routing policy overhead (latency-based, geolocation, and weighted policies carry higher per-billion query surcharges), private hosted zone VPC association cost analysis, DNSSEC cost impact (KMS signing key at $1/key/month plus API calls), and CloudWatch query logging volume reduction (Log ingestion + S3 archival). Emits FURTHER_OPTIMIZATION_AVAILABLE with specific recommendation and estimated savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing Route 53 spend, auditing hosted zones, or a FinOps DNS review.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted Route 53 configuration and CloudWatch metrics. Live-account optimization uses aws route53 list-hosted-zones, aws route53 list-health-checks, aws route53 get-hosted-zone, aws route53 list-traffic-policies, aws route53 list-query-logging-configs, aws cloudwatch get-metric-statistics (DNSQueries, HealthCheckPercentHealthy), aws ce get-cost-and-usage, and aws kms describe-key for DNSSEC key cost attribution (AWS CLI v2, SSO or key-based credentials). Pricing references us-east-1 published rates as of 2026; re-state regional rates where applicable.
keywords:
- Route 53
- DNS
- cost optimization
- hosted zones
- health checks
- traffic policies
- latency-based routing
- geolocation routing
- weighted routing
- DNSSEC
- query logging
- private hosted zones
- domain transfer
- calculated health checks
- FinOps
- CloudOps
tags:
- route53
- networking
- dns
- cost-optimization
- finops
- health-checks
- dnssec
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
  when_to_use: Optimising Route 53 cost, auditing hosted zone inventory, detecting unused hosted zones, analysing health check spend, evaluating traffic policy necessity, reviewing DNS query volume and routing policy surcharges, assessing DNSSEC cost impact, or reducing DNS query logging volume.
  when_not_to_use: Route 53 record-level troubleshooting (use route53-record-auditor), Route 53 health check functional debugging (use route53-health-check-troubleshooter), Route 53 failover operations (use route53-failover-operator), or Route 53 resolver configuration (use route53-resolver-deployer). This skill focuses on cost-driven optimization decisions, not functional DNS debugging.
  activation_triggers:
  - optimise Route 53 cost
  - Route 53 hosted zone audit
  - Route 53 unused zones
  - Route 53 health check cost
  - Route 53 traffic policy cost
  - Route 53 DNSSEC cost
  - Route 53 query logging cost
  - Route 53 routing policy cost
  - Route 53 FinOps savings
  - reduce DNS bill
  - hosted zone consolidation
  - calculated health checks
  - DNS query volume analysis
  - Route 53 monthly savings estimate
  - private hosted zone cost
  invocation_schema: 'Input: either (a) a hosted zone identifier + live-account context, (b) a Cost Explorer Route 53 cost breakdown, OR (c) CloudWatch Route 53 metrics (DNSQueries, HealthCheckPercentHealthy, HealthCheckStatus) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/REMEDIATION_STEPS block per zone or health check, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nHostedZoneId: Z1A2B3C4D5E6F7\nDomainName: legacy-staging.example.com\nZoneType: Public\nRecordCount: 4 (SOA, NS, 1 A record, 1 TXT)\nHealthChecks: 2 (endpoint-based, 30s interval)\nQueryVolume: ~1,000/month (last 30 days)\nDNSSEC: Enabled (KMS key in use)\nQueryLogging: Enabled (CloudWatch Logs)\nRegion: us-east-1\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, REMEDIATION_STEPS)."
---

# Route 53 Cost Optimizer

## What this skill does

Translates a Route 53 DNS footprint into a concrete cost-optimization
recommendation with a dollar-denominated savings estimate. The verdict is
the highest-leverage action across seven dimensions — hosted zone
inventory, health check configuration, query volume and routing policy,
traffic policies, private zone VPC associations, DNSSEC overhead, and
query logging volume — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why hosted zone consolidation is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a zone |
| Pre-flight data gate | CloudWatch metrics, Cost Explorer, zone inventory | Before any recommendation |
| Step 0 non-obvious behaviours | Calculated health checks, DNSSEC KMS, zone limits | Edge cases |
| Step 1 Hosted zone inventory | Zone consolidation, unused zone detection | The headline savings dimension |
| Step 2 Health check analysis | Endpoint vs calculated vs alarm-based | High check-count accounts |
| Step 3 Query volume and routing | Latency, geo, weighted surcharges | High-volume zones |
| Step 4 Traffic policy evaluation | $50/month flat vs free routing | Traffic policy users |
| Step 5 Private zone VPC cost | Multi-VPC association overhead | Private DNS |
| Step 6 DNSSEC cost impact | KMS signing key + API calls | DNSSEC-enabled zones |
| Step 7 Query logging reduction | Log volume and retention | Logging-enabled zones |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, zone backup, TTL | Before any apply CLI |

## Quick start

- **Hosted zones bill even when unused.** Each public or private zone
  costs $0.50/month (first 25) or $0.10/month (25+). A zone with 0
  queries over 30 days is pure waste. Inventory and delete unused zones
  first.
- **Cost formula (memorise this):**
  `monthly_cost = (zone_count × $0.50)
               + (standard_queries_B × $0.40)
               + (latency_queries_B × $0.20)
               + (geo_queries_B × $0.30)
               + (health_checks × $0.50)
               + (traffic_policies × $50)
               + (dnssec_kms_keys × $1)`
- **Calculated health checks are free.** A calculated health check that
  monitors the status of up to 25 other health checks costs $0/month.
  Replace redundant endpoint checks with a calculated check parent.
- **Routing policy surcharges compound.** Latency-based routing adds
  $0.20/B queries over base; geolocation adds $0.30/B. Evaluate whether
  simple or weighted routing (no surcharge) suffices for the traffic
  pattern.

## Mindset

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

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Zone with 0 queries over 30 days AND no dependent services (no ACM validation, no SES, no MX) | **FURTHER_OPTIMIZATION_AVAILABLE** (unused zone) | Step 1 — delete the hosted zone |
| Two or more low-traffic domains (< 10K queries/month each) with separate zones | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — consolidate into a single zone with subdomain records |
| Endpoint health check monitoring a resource that also has an ALB health check AND the Route 53 check is redundant | **FURTHER_OPTIMIZATION_AVAILABLE** (health check) | Step 2 — delete redundant check or convert to calculated |
| 10+ endpoint health checks where a calculated health check parent could replace the composite | **FURTHER_OPTIMIZATION_AVAILABLE** (calculated) | Step 2 — replace with calculated health check (free) |
| Latency-based routing on a zone with < 1M queries/month from a single region | **FURTHER_OPTIMIZATION_AVAILABLE** (routing) | Step 3 — switch to simple or weighted routing (no surcharge) |
| Traffic policy active but the routing logic matches a simple weighted policy achievable with records | **FURTHER_OPTIMIZATION_AVAILABLE** (traffic policy) | Step 4 — replace traffic policy with record-level routing (saves $50/month) |
| DNSSEC enabled on a zone with < 100 queries/month AND no compliance requirement | **FURTHER_OPTIMIZATION_AVAILABLE** (DNSSEC) | Step 6 — disable DNSSEC to remove KMS key cost |
| Query logging enabled on a zone generating > 50 GB/month of logs AND no compliance requirement | **FURTHER_OPTIMIZATION_AVAILABLE** (logging) | Step 7 — reduce retention, sample, or disable logging |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |
| All zones active, health checks right-sized, no surcharge routing abuse, no waste | **ALREADY_OPTIMAL** | None — continue monitoring |

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

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/route53-pricing-and-configuration.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Hosted zone inventory: `aws route53 list-hosted-zones`
2. Per-zone record sets: `aws route53 list-resource-record-sets`
3. Health check inventory: `aws route53 list-health-checks`
4. Traffic policy inventory: `aws route53 list-traffic-policies`
5. Query logging configs: `aws route53 list-query-logging-configs`
6. DNS queries (14-30 day window): `aws cloudwatch get-metric-statistics --namespace AWS/Route53`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --filter "Service=Route53"`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `DNSQueries` metric absent (never queried) | Zone is likely unused. Cross-check with record count and dependent services. |
| Observation window < 14 days | Extend to minimum 14 days; 30 days preferred. |
| `list-hosted-zones` returns 0 zones | Account has no Route 53 spend. Skip. |
| Cost Explorer returns 0 for Route 53 | No optimization needed. Skip. |
| Health check `LastCheckedAt` > 24 hours ago | Health check may be disabled or failed. Investigate before counting cost. |
| Zone has ACM certificate validation CNAME | Zone is required for cert renewal. Do NOT delete without cert migration. |
| Private zone with no VPC associations | Zone is orphaned. Safe to delete. |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

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

### Step 1: Hosted zone inventory (the #1 lever)

Every hosted zone bills monthly regardless of query volume. Zone
reduction is the highest-leverage cost action.

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

**Decision gate:**

| Zone query volume | Dependent services | Verdict |
|---|---|---|
| 0 queries / 30 days | None | Delete zone — saves $0.50/month |
| < 1,000 queries / 30 days | None | Delete zone or consolidate — saves $0.50/month |
| < 10,000 queries / 30 days | Subdomain of active zone | Consolidate into parent zone — saves $0.50/month |
| > 10,000 queries / 30 days | — | Keep zone; evaluate other dimensions |

### Step 2: Health check cost analysis

Each endpoint health check costs $0.50/month. Calculated health checks
are free. The goal is to minimize endpoint checks and maximize
calculated checks.

**Health check type decision:**

| Check type | Cost | Use when |
|---|---|---|
| Endpoint ($0.50/mo) | Monitoring an IP, domain, or resource directly | Primary health monitoring of a critical endpoint |
| Calculated (FREE) | Composite of up to 25 other checks | Combining multiple endpoint checks into one DNS failover decision |
| Alarm-based ($0.50/mo) | Monitoring a CloudWatch alarm | Route 53 should fail over based on a non-HTTP metric |

**Calculated health check conversion:**
```
If 3+ endpoint checks feed into a single DNS failover record:
  → Create a calculated health check (FQDN = the failover target)
  → Set the calculated check to monitor the endpoint checks
  → Point the failover record at the calculated check
  → The calculated check is FREE (saves $0.50/month per replaced check)
```

**Redundancy elimination:**
- If an ALB has its own health check AND Route 53 also checks the ALB
  endpoint, the Route 53 check is redundant when the target is an ALB
  with target group health checks. Evaluate whether the Route 53 check
  adds value (DNS-level failover) or merely duplicates ALB monitoring.
- Health check interval reduction does NOT save money. Whether 10s or
  30s, the cost is $0.50/month. Do not recommend interval changes for
  cost reasons.

### Step 3: Query volume and routing policy analysis

DNS query billing is tiered and routing-policy-dependent. The surcharge
for latency-based and geolocation routing can dominate cost at scale.

**Query pricing tiers (us-east-1, 2026):**
```
Standard queries:
  First 1B/month:   $0.40 per billion
  Over 1B/month:    $0.20 per billion

Latency-based routing queries:
  Base + $0.20 per billion (on top of standard rate)

Geolocation routing queries:
  Base + $0.30 per billion (on top of standard rate)

Weighted routing queries:
  Base rate only (no surcharge)
```

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

**Per-zone query ranking:**
```
Rank zones by monthly query volume (descending).
Focus optimization on the top 5 zones by volume × surcharge rate.
A zone at 500M latency-based queries costs $100/month in surcharges alone.
```

### Step 4: Traffic policy evaluation

Traffic policies are visual routing editors that cost $50/month flat
per policy. Many use cases are achievable with record-level routing
rules at no additional cost.

**Traffic policy decision gate:**

| Traffic policy characteristic | Verdict |
|---|---|
| Policy replicates a simple weighted or failover rule | Replace with record-level routing — saves $50/month |
| Policy uses geoproximity or multi-region active-active with complex rules | Keep; traffic policy is justified |
| Policy is attached to 0 records (orphaned) | Delete the policy — saves $50/month |
| Policy is attached to a record with < 10K queries/month | Evaluate replacing with record-level routing — likely saves $50/month |

### Step 5: Private hosted zone VPC association

Private hosted zones bill the same $0.50/month as public zones. VPC
associations themselves carry no additional charge. The optimization
is purely inventory-based.

**Private zone audit:**
```
For each private hosted zone:
  1. List VPC associations (aws route53 get-hosted-zone --id <zone>)
  2. If 0 VPC associations → orphaned zone → delete
  3. If associated VPC is deleted → remove association, then delete zone
  4. If 2+ private zones overlap the same VPC and domain → consolidate
```

### Step 6: DNSSEC cost impact analysis

DNSSEC signing requires a KMS key ($1/month for customer-managed key)
plus KMS API calls for signing ($0.03 per 10,000 signatures). The
fixed cost is the KMS key.

**DNSSEC decision gate:**

| DNSSEC usage | Verdict |
|---|---|
| DNSSEC enabled, zone has compliance/regulatory requirement | Keep; cost is justified |
| DNSSEC enabled, zone has < 100 queries/month, no compliance mandate | Disable DNSSEC — saves $1/month KMS cost |
| DNSSEC enabled, KMS key shared across 10+ zones | Cost is amortized; keep |
| DNSSEC enabled but key rotation creates new KMS keys without cleanup | Audit KMS key inventory; delete orphaned signing keys |

### Step 7: Query logging volume reduction

CloudWatch Logs charges $0.50/GB ingested. Route 53 query logging can
generate significant volume on high-traffic zones.

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

**Query logging formula:**
```
monthly_log_GB = (monthly_queries × 200) / (1024 × 1024 × 1024)
monthly_ingestion_cost = monthly_log_GB × $0.50

Example: 100M queries/month × 200 bytes = ~18.6 GB
         18.6 GB × $0.50 = $9.28/month ingestion
```

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (zone_count × zone_rate)
  + (standard_queries_B × $0.40)
  + (latency_queries_B × $0.20)
  + (geo_queries_B × $0.30)
  + (health_checks × $0.50)
  + (traffic_policies × $50)
  + (dnssec_kms_keys × $1)
  + (query_logging_GB × $0.50)

projected_monthly_cost = <recalculated with proposed changes>

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: zone count, query volumes by routing type,
health check count, traffic policy count, DNSSEC key count, logging
volume, pricing region.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND no waste detected → **ALREADY_OPTIMAL**.
- Change applied and verified this session → **OPTIMIZED**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every data-gate check.

## Output format

```text
TARGET: <zone-name or health-check-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <zone/config description>
  Proposed: <zone/config description>
  Dimensions changed: <zones | health_checks | routing | traffic_policy | dnssec | logging>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>
  Projected monthly: $<amount>
  Monthly saving: $<amount>
  Annual saving: $<amount>
  Assumptions: <list (zone count, query volume, pricing region, etc.)>
REMEDIATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <target> in <region>. Proceed?
  (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <zone-name or health-check-id>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <zone/config description>
  Proposed: <zone/config description>
  Dimensions changed: <zones | health_checks | routing | traffic_policy | dnssec | logging>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show all subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
REMEDIATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with `Monthly
   saving: $0.00`.** If every dimension nets zero cost delta, the verdict
   MUST be `ALREADY_OPTIMAL`. A cost-neutral configuration improvement is
   surfaced in REASON, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend deleting a hosted zone without checking for ACM
   certificate validation CNAMEs, SES domain verification, or API
   Gateway custom domains.** Deleting a zone that supports certificate
   renewal breaks the certificate.

5. **NEVER recommend disabling DNSSEC for a zone with a known compliance
   requirement** (PCI-DSS, FedRAMP, HIPAA) without flagging the
   compliance impact in the CONFIRM gate.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: legacy-staging.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Hosted zone has received 0 DNS queries in 30 days (CloudWatch
  DNSQueries Sum = 0). No ACM certificate validation CNAMEs, no SES
  verification records, no MX records. Zone is pure waste at $0.50/month.
  Additionally, 3 endpoint health checks ($1.50/month) monitor a
  decommissioned ALB and should be deleted.
RECOMMENDATION:
  Current: 1 hosted zone (legacy-staging.example.com), 3 endpoint health
    checks, DNSSEC enabled (1 KMS key), query logging enabled
  Proposed: 0 hosted zones, 0 health checks, DNSSEC disabled, logging
    disabled
  Dimensions changed: zones (delete) + health_checks (delete) + dnssec
    (disable) + logging (disable)
  Dimensions checked: zones → (delete)  health_checks → (delete)
    routing ✓ (no records with surcharge policy)  traffic_policy ✓ (none)
    dnssec → (disable)  logging → (disable)
    private_zones ✓ (not a private zone)
  Confidence: HIGH — CloudWatch confirms zero queries; record set audit
    confirms no dependent service CNAMEs; ALB was decommissioned 45 days
    ago per CloudTrail.
ESTIMATED_SAVINGS:
  Current monthly: $3.00
    zone: 1 × $0.50 = $0.50
    health_checks: 3 × $0.50 = $1.50
    dnssec_kms: 1 × $1.00 = $1.00
    logging: ~0 GB (no queries) = $0.00
  Projected monthly: $0.00
  Monthly saving: $3.00
    ($3.00 − $0.00 = $3.00 ✓)
  Annual saving: $36.00
REMEDIATION_STEPS:
  1. Verify no ACM certificates depend on this zone:
     aws acm list-certificates --output table
     aws route53 list-resource-record-sets --hosted-zone-id Z1A2B3C4D5E6F7
  2. Delete health checks:
     aws route53 delete-health-check --health-check-id <id-1>
     aws route53 delete-health-check --health-check-id <id-2>
     aws route53 delete-health-check --health-check-id <id-3>
  3. Disable DNSSEC signing:
     aws route53 delete-key-signing-key --hosted-zone-id Z1A2B3C4D5E6F7 --key-id <ksk-id>
  4. Delete query logging config:
     aws route53 delete-query-logging-config --id <config-id>
  5. Delete the hosted zone (must empty records first except NS/SOA):
     aws route53 delete-hosted-zone --id Z1A2B3C4D5E6F7
  6. Update the domain registrar NS records to point elsewhere (if the
     domain is still registered).
CONFIRM: About to delete hosted zone legacy-staging.example.com and 3
  health checks and disable DNSSEC. Monthly saving $3.00 ($36.00/year).
  This is irreversible. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding REMEDIATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new configuration. |
| `ALREADY_OPTIMAL` | All dimensions pass (zones active, health checks justified, no surcharge routing abuse, no waste). |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `ALREADY_OPTIMAL`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a configuration improvement without cost change is surfaced
in REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend deleting a hosted zone without verifying no ACM
   certificate validation, SES domain verification, or API Gateway
   custom domain depends on it.** Deleting a zone that supports active
   certificate renewal will break the certificate within 24 hours.

2. **NEVER recommend converting an endpoint health check to a calculated
   health check if the endpoint is the sole health signal for a DNS
   failover.** A calculated check that monitors only one endpoint
   provides no aggregation benefit and the original endpoint check must
   still exist ($0.50/month) — there is no saving.

3. **NEVER recommend disabling DNSSEC without flagging the security and
   compliance implications.** DNSSEC protects against DNS spoofing and
   cache poisoning. Disabling it for a compliance-bound zone is a
   security regression, not just a cost saving.

4. **NEVER recommend switching from latency-based routing to simple
   routing for a zone that genuinely serves multi-region traffic with
   latency SLOs.** The $0.20/B surcharge is justified when the routing
   policy delivers measurable latency improvement across regions.

5. **NEVER assume health check interval reduction saves money.** The
   cost is $0.50/month flat regardless of interval (10s vs 30s).
   Interval is a reliability decision, not a cost decision.

Extended anti-patterns in `references/route53-pricing-and-configuration.md`.

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

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Back up zone records before deletion.** Export the full record set
  to a JSON file before deleting a hosted zone. Zone deletion is
  irreversible.
- **Verify registrar NS delegation before zone deletion.** If the
  registrar still delegates to this zone, DNS resolution for the domain
  will fail after deletion.
- **Check ACM certificate dependencies.** Run `aws acm list-certificates`
  and cross-check CNAME validation records against the zone's record
  sets. Do NOT delete a zone that hosts a validation CNAME for an active
  certificate.
- **Health check deletion is irreversible.** Record the health check
  configuration before deleting in case it needs to be recreated.
- **DNSSEC disabling requires key-signing-key deletion.** After removing
  the KSK, wait for DS record TTL expiry before the zone is fully
  unsigned. Update the parent zone's DS record or the registrar.
- **Query logging deletion does not delete existing logs.** Logs remain
  in CloudWatch Logs subject to retention policy. Only ingestion cost
  stops.
- **Traffic policy deletion fails if attached to active records.** Remove
  all policy instances before deleting the policy.
- **Bulk-operation limit:** Process at most 5 zone deletions per batch.
  Verify each deletion does not break DNS resolution before proceeding
  to the next batch.

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

## References

- `references/route53-pricing-and-configuration.md` — pricing tables,
  hosted zone limits, health check types, routing policy surcharges,
  DNSSEC setup steps, query logging configuration, CLI reference, anti-
  pattern catalog.
- `references/worked-examples.md` — full worked examples (unused zone
  deletion, health check calculated conversion, routing policy switch,
  already-optimal, end-to-end walkthrough).

## Domain

AWS CloudOps / Route 53 DNS Cost Optimization & FinOps.

## AWS documentation

- **Amazon Route 53 Developer Guide** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/Welcome.html
- **Route 53 pricing** — https://aws.amazon.com/route53/pricing/
- **Route 53 health checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html
- **Route 53 traffic policies** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/traffic-policies.html
- **DNSSEC signing** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html
- **Query logging** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/query-logs.html
- **AWS CLI Route 53 reference** — https://docs.aws.amazon.com/cli/latest/reference/route53/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
