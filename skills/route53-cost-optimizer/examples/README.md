# Example usage: route53-cost-optimizer

A walkthrough showing the skill optimizing a decommissioned staging
hosted zone, demonstrating the zone inventory audit, the unused zone
detection, the DNSSEC cost impact, and the staged deletion with backup
safety checks.

## Input (user prompt)

> Review our Route 53 zones before our Q3 FinOps review. We have a
> staging zone that I think is unused. Help me optimize the DNS cost.

```text
HostedZoneId: Z-staging-legacy-example
DomainName: staging.legacy.example.com
ZoneType: Public
RecordCount: 4 (SOA, NS, 1 A record pointing at deleted ALB, 1 TXT)
HealthChecks: 2 (endpoint-based, 30s interval, monitoring deleted ALB)
QueryVolume: 0 queries (last 30 days, CloudWatch DNSQueries Sum = 0)
DNSSEC: Enabled (1 KMS key, $1/month)
QueryLogging: Enabled (CloudWatch Logs, ~0 GB due to no queries)
RoutingPolicy: Simple
TrafficPolicies: None
Region: us-east-1

ACM certificates referencing this zone: None
SES domain verification records: None
```

## Skill output

```text
TARGET: staging.legacy.example.com
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Hosted zone has received 0 DNS queries in 30 days (CloudWatch
  DNSQueries Sum = 0). No ACM certificate validation CNAMEs, no SES
  verification records, no MX records. Zone is pure waste at
  $0.50/month. 2 endpoint health checks ($1.00/month) monitor a
  decommissioned ALB. DNSSEC KMS key adds $1.00/month. Total waste:
  $2.50/month.
RECOMMENDATION:
  Current: 1 hosted zone (staging.legacy.example.com), 2 endpoint
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
     aws route53 list-resource-record-sets --hosted-zone-id Z-staging-legacy-example > backup.json
  2. Delete health checks:
     aws route53 delete-health-check --health-check-id <id-1>
     aws route53 delete-health-check --health-check-id <id-2>
  3. Disable DNSSEC:
     aws route53 delete-key-signing-key --hosted-zone-id Z-staging-legacy-example --key-id <ksk-id>
  4. Delete query logging config:
     aws route53 delete-query-logging-config --id <config-id>
  5. Delete the hosted zone:
     aws route53 delete-hosted-zone --id Z-staging-legacy-example
  6. Update the domain registrar NS records to point elsewhere.
CONFIRM: About to delete hosted zone staging.legacy.example.com, 2 health
  checks, disable DNSSEC, and remove query logging. Monthly saving $2.50
  ($30.00/year). Irreversible. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **DNSSEC KMS key cost attribution.** A generic assistant sees $0.50
   for the zone and misses the $1.00/month KMS key that DNSSEC creates.
   The skill attributes the full $2.50/month total cost.

2. **ACM certificate dependency check.** A generic assistant says "just
   delete it." The skill verifies no ACM validation CNAMEs exist in the
   zone before recommending deletion — preventing certificate renewal
   failures.

3. **Health check cleanup sequencing.** The skill deletes health checks
   BEFORE deleting the zone (health checks can outlive their zone and
   silently bill $0.50/month indefinitely). A generic assistant forgets
   this step.

4. **Zone record backup.** The skill exports the full record set to a
   backup file before deletion. Zone deletion is irreversible; a
   generic assistant does not suggest a backup.

5. **Registrar NS record update.** The skill flags that the domain
   registrar must be updated to point NS records elsewhere before the
   zone is deleted. A generic assistant goes straight to
   `delete-hosted-zone` without the registrar step.

6. **Seven-dimension check.** The skill explicitly checks all seven
   dimensions (zones, health checks, routing, traffic policies, DNSSEC,
   logging, private zones) and marks each as checked or finding. A
   generic assistant focuses only on the zone itself.

## Slash-command invocation

```
/aws:optimize-route53-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Route 53 zones for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: route53-cost-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate that no DNS resolution issues occurred:

```bash
# Verify the zone is deleted
aws route53 list-hosted-zones --query 'HostedZones[?Name==`staging.legacy.example.com.`]' --output table

# Check that no ACM certificates are failing renewal
aws acm list-certificates --output table
aws acm describe-certificate --certificate-arn <arn> --query 'Certificate.DomainValidationOptions'
```

If any certificate shows "PENDING_VALIDATION" after zone deletion, the
zone hosted a validation CNAME and must be recreated immediately.

## Fleet-wide extension

For a fleet of N Route 53 zones, run the skill in batch mode:

1. Pull all zones with `aws route53 list-hosted-zones`.
2. For each zone, pull `DNSQueries` metric over 30 days.
3. Filter to zones with 0 queries (unused zone candidates).
4. For each candidate, check ACM, SES, and record-set dependencies.
5. Sort by total monthly cost (zone + health checks + DNSSEC + logging).
6. Slice into batches of 5 zones.
7. For each batch: emit per-zone REMEDIATION_STEPS, then a single
   CONFIRM for the batch.
8. Verify each batch before proceeding to the next.
