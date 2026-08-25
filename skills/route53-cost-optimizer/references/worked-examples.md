# Worked Examples — Route 53 Cost Optimizer

Full worked examples covering every verdict type and the major
optimization patterns. Each example shows the complete output block
with verified math.

## Example 1: Unused zone deletion (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: legacy-staging.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Hosted zone has received 0 DNS queries in 30 days (CloudWatch
  DNSQueries Sum = 0). No ACM certificate validation CNAMEs, no SES
  verification records, no MX records. Zone is pure waste at
  $0.50/month. 2 endpoint health checks ($1.00/month) monitor a
  decommissioned ALB and should be deleted.
RECOMMENDATION:
  Current: 1 hosted zone (legacy-staging.example.com), 2 endpoint
    health checks, DNSSEC enabled (1 KMS key), query logging enabled
  Proposed: 0 hosted zones, 0 health checks, DNSSEC disabled, logging
    disabled
  Dimensions changed: zones (delete) + health_checks (delete) + dnssec
    (disable) + logging (disable)
  Dimensions checked: zones → (delete)  health_checks → (delete)
    routing ✓ (no surcharge policy)  traffic_policy ✓ (none)
    dnssec → (disable)  logging → (disable)  private_zones ✓ (n/a)
  Confidence: HIGH — CloudWatch confirms zero queries; record set audit
    confirms no dependent service CNAMEs; ALB decommissioned 45 days ago.
ESTIMATED_SAVINGS:
  Current monthly: $2.50
    zone: 1 × $0.50 = $0.50
    health_checks: 2 × $0.50 = $1.00
    dnssec_kms: 1 × $1.00 = $1.00
    logging: $0.00 (no queries)
  Projected monthly: $0.00
  Monthly saving: $2.50
    ($2.50 − $0.00 = $2.50 ✓)
  Annual saving: $30.00
REMEDIATION_STEPS:
  1. Export zone records as backup:
     aws route53 list-resource-record-sets --hosted-zone-id Z-xxx > backup.json
  2. Delete health checks:
     aws route53 delete-health-check --health-check-id <id-1>
     aws route53 delete-health-check --health-check-id <id-2>
  3. Disable DNSSEC:
     aws route53 delete-key-signing-key --hosted-zone-id Z-xxx --key-id <ksk-id>
  4. Delete query logging config:
     aws route53 delete-query-logging-config --id <config-id>
  5. Delete the hosted zone:
     aws route53 delete-hosted-zone --id Z-xxx
CONFIRM: About to delete hosted zone legacy-staging.example.com, 2 health
  checks, and disable DNSSEC. Monthly saving $2.50 ($30.00/year).
  Irreversible. Proceed? (yes/no)
```

## Example 2: Health check calculated conversion (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: api.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: 3 of 12 endpoint health checks ($1.50/month) are redundant —
  they monitor the same ALB that has target group health checks. A
  calculated health check (free) can replace the composite monitoring
  for the DNS failover decision.
RECOMMENDATION:
  Current: 12 endpoint health checks ($6.00/month)
  Proposed: 9 endpoint health checks + 1 calculated check ($4.50/month)
  Dimensions changed: health_checks (convert 3 redundant to calculated)
  Dimensions checked: zones ✓ (active zone)  health_checks → (convert)
    routing ✓ (failover, no surcharge)  traffic_policy ✓ (none)
    dnssec ✓ (disabled)  logging ✓ (disabled)  private_zones ✓ (n/a)
  Confidence: HIGH — CloudTrail confirms ALB target group health checks
    are active; the 3 Route 53 checks duplicate the same monitoring.
ESTIMATED_SAVINGS:
  Current monthly: $6.00
    health_checks: 12 × $0.50 = $6.00
  Projected monthly: $4.50
    health_checks: 9 × $0.50 = $4.50
    calculated_checks: 1 × $0.00 = $0.00
  Monthly saving: $1.50
    ($6.00 − $4.50 = $1.50 ✓)
  Annual saving: $18.00
REMEDIATION_STEPS:
  1. Create a calculated health check monitoring the 3 redundant checks:
     aws route53 create-health-check --caller-reference calc-001 \
       --health-check-config '{"Type":"CALCULATED","HealthThreshold":1,
       "ChildHealthChecks":["<id-1>","<id-2>","<id-3>"]}'
  2. Update the DNS failover record to reference the calculated check.
  3. After verifying failover works, delete the 3 endpoint checks.
CONFIRM: About to convert 3 endpoint health checks to 1 calculated check.
  Monthly saving $1.50 ($18.00/year). Proceed? (yes/no)
```

## Example 3: Routing policy surcharge removal (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: single-region-app.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Latency-based routing is enabled but all traffic originates
  from us-east-1. The +$0.20/B surcharge costs $40/month on 200M
  queries for zero routing benefit. Switching to weighted routing
  (no surcharge) eliminates the cost.
RECOMMENDATION:
  Current: Latency-based routing, 200M queries/month at $0.60/B
  Proposed: Weighted routing, 200M queries/month at $0.40/B
  Dimensions changed: routing (latency → weighted)
  Dimensions checked: zones ✓ (active)  health_checks ✓ (justified)
    routing → (switch to weighted)  traffic_policy ✓ (none)
    dnssec ✓ (disabled)  logging ✓ (disabled)  private_zones ✓ (n/a)
  Confidence: HIGH — CloudWatch confirms 100% of queries from us-east-1.
ESTIMATED_SAVINGS:
  Current monthly: $0.12
    standard: 200M/1B × $0.40 = $0.08
    latency_surcharge: 200M/1B × $0.20 = $0.04
    total query cost: $0.12
  Projected monthly: $0.08
    standard: 200M/1B × $0.40 = $0.08
    surcharge: $0.00 (weighted has no surcharge)
  Monthly saving: $0.04
    ($0.12 − $0.08 = $0.04 ✓)
  Annual saving: $0.48
REMEDIATION_STEPS:
  1. Create weighted records to replace latency-based records.
  2. Delete the latency-based records.
  3. Verify DNS resolution from us-east-1 returns the correct endpoint.
CONFIRM: About to switch routing policy from latency-based to weighted
  on single-region-app.example.com. Annual saving $0.48. Proceed? (yes/no)
```

## Example 4: Already optimal (ALREADY_OPTIMAL)

```text
TARGET: production.example.com
VERDICT: ALREADY_OPTIMAL
REASON: Production zone with 500M queries/month, justified health checks
  for DNS failover, simple+weighted routing (no surcharge), DNSSEC
  required by PCI-DSS compliance. All seven dimensions pass — no
  optimization available without degrading compliance posture or
  reliability.
RECOMMENDATION:
  Current: 1 zone ($0.50), 3 health checks ($1.50), DNSSEC KMS ($1.00),
    simple+weighted routing ($0.20/B for 500M = $0.20), no logging
  Proposed: No changes
  Dimensions checked: zones ✓ (active, 500M queries)  health_checks ✓
    (3 unique endpoints)  routing ✓ (no surcharge)  traffic_policy ✓
    (none)  dnssec ✓ (PCI-DSS required)  logging ✓ (disabled)
    private_zones ✓ (n/a)
  Confidence: HIGH — all dimensions verified against 30-day data.
ESTIMATED_SAVINGS:
  Current monthly: $3.20
  Projected monthly: $3.20
  Monthly saving: $0.00
  Annual saving: $0.00
REMEDIATION_STEPS: None required.
CONFIRM: N/A — no changes recommended.
```

## Example 5: Traffic policy replacement (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: marketing-site.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Traffic policy ($50/month) replicates a simple 80/20 weighted
  split achievable with record-level weighted routing at $0. Zone has
  only 50K queries/month — the traffic policy cost dominates total DNS
  spend.
RECOMMENDATION:
  Current: 1 traffic policy at $50/month for 80/20 split
  Proposed: Weighted record-level routing at $0/month
  Dimensions changed: traffic_policy (replace with records)
  Dimensions checked: zones ✓ (active)  health_checks ✓ (none)
    routing ✓ (will use weighted)  traffic_policy → (delete)
    dnssec ✓ (disabled)  logging ✓ (disabled)  private_zones ✓ (n/a)
  Confidence: HIGH — traffic policy rule is a simple 80/20 split with
    no geoproximity or multi-region logic.
ESTIMATED_SAVINGS:
  Current monthly: $50.02
    zone: 1 × $0.50 = $0.50
    traffic_policy: 1 × $50.00 = $50.00
    queries: 50K/1B × $0.40 ≈ $0.00
  Projected monthly: $0.50
    zone: 1 × $0.50 = $0.50
    traffic_policy: 0 × $50.00 = $0.00
    queries: 50K/1B × $0.40 ≈ $0.00
  Monthly saving: $49.52
    ($50.02 − $0.50 = $49.52 ✓)
  Annual saving: $594.24
REMEDIATION_STEPS:
  1. Create weighted records replicating the 80/20 split:
     aws route53 change-resource-record-sets --hosted-zone-id Z-xxx \
       --change-batch '{"Changes":[{"Action":"CREATE",...Weight:80,...}]}'
     aws route53 change-resource-record-sets --hosted-zone-id Z-xxx \
       --change-batch '{"Changes":[{"Action":"CREATE",...Weight:20,...}]}'
  2. Remove the traffic policy instance from the record.
  3. Delete the traffic policy:
     aws route53 delete-traffic-policy --id <policy-id> --version 1
CONFIRM: About to replace traffic policy with weighted records on
  marketing-site.example.com. Annual saving $594.24. Proceed? (yes/no)
```

## Canonical output block template

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
