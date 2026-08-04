# End-to-end usage scenario: route53-record-auditor

A walkthrough showing the skill auditing a production Route 53 zone that
has a failover PRIMARY without a health check (CRITICAL) and a separate
dangling ALIAS to a deleted ELB (HIGH), demonstrating severity
aggregation, the failover-disabled concept, and the assume-takeover
remediation workflow.

## Input (user prompt)

> Review our Route 53 configuration before the Black Friday traffic
> surge. We have a failover setup for api.shop.example.com and a legacy
> record we think might be stale.

Hosted zone: Z999PRODZONE (public, shop.example.com)
DNSSEC: not enabled (no KSK configured)

Record set 1:
```json
{
  "Name": "api.shop.example.com.",
  "Type": "A",
  "SetIdentifier": "primary",
  "Failover": "PRIMARY",
  "TTL": 60,
  "ResourceRecords": [{"Value": "203.0.113.100"}]
}
```
(No HealthCheckId on the PRIMARY)

Record set 2:
```json
{
  "Name": "api.shop.example.com.",
  "Type": "A",
  "SetIdentifier": "secondary",
  "Failover": "SECONDARY",
  "TTL": 60,
  "ResourceRecords": [{"Value": "203.0.113.200"}]
}
```
(No HealthCheckId on the SECONDARY)

Record set 3:
```json
{
  "Name": "old-cdn.shop.example.com.",
  "Type": "A",
  "AliasTarget": {
    "DNSName": "d111abcdef9.cloudfront.net",
    "EvaluateTargetHealth": false
  }
}
```
(CloudFront distribution d111abcdef9 was deleted 3 months ago)

## Skill output

```text
RECORD: api.shop.example.com (A, failover)
VERDICT: NO_HEALTH_CHECK
REASON: Failover PRIMARY record has no HealthCheckId — Route 53 cannot
detect primary failure and will never serve the secondary (Step 2a).
RISK: CRITICAL
FINDINGS:
  - [CRITICAL] Failover PRIMARY with no HealthCheckId (Step 2a) — failover
    is functionally disabled; a dead primary receives all traffic forever
  - [LOW] Failover SECONDARY with no HealthCheckId (Step 2 note) —
    secondary is served when primary fails; health check is recommended
    for fail-closed behaviour but not required
  - [HIGH] DNSSEC signing is not enabled on this public hosted zone
    (Step 3a) — cache-poisoning susceptibility
  - [OK] No dangling ALIAS detected on this record (Step 1)
  - [OK] TTL 60 is consistent across the failover group (Step 5)
REMEDIATION:
  1. CRITICAL — Create a health check for the PRIMARY endpoint:
     aws route53 create-health-check --caller-reference hc-api-primary
     --health-check-config '{"Type":"HTTPS","FullyQualifiedDomainName":
     "api.shop.example.com","ResourcePath":"/health","RequestInterval":30,
     "FailureThreshold":3}'
  2. CRITICAL — Associate the HealthCheckId with the PRIMARY record via
     a change-resource-record-sets UPSERT batch.
  3. HIGH — Enable DNSSEC signing:
     aws route53 enable-hosted-zone-dnssec --hosted-zone-id Z999PRODZONE
     Then create a KSK and publish the DS record at the registrar.
  4. Back up records before changes:
     aws route53 list-resource-record-sets --hosted-zone-id Z999PRODZONE
     --output json > /tmp/z999-backup-$(date +%s).json
```

```text
RECORD: old-cdn.shop.example.com (A, simple)
VERDICT: DANGLING
REASON: ALIAS target d111abcdef9.cloudfront.net points to a deleted
CloudFront distribution — NXDOMAIN for all queries to this record
(Step 1b).
RISK: HIGH
FINDINGS:
  - [HIGH] ALIAS to deleted CloudFront distribution d111abcdef9 (Step 1b)
    — DNS name returns NXDOMAIN; immediate outage for any client
    resolving this record
  - [HIGH] DNSSEC signing is not enabled on this public hosted zone
    (Step 3a) — cache-poisoning susceptibility
REMEDIATION:
  1. Verify the distribution is deleted:
     aws cloudfront list-distributions --query
     "DistributionList.Items[?Id=='d111abcdef9']"
  2. If confirmed deleted, delete or update the record:
     aws route53 change-resource-record-sets --hosted-zone-id Z999PRODZONE
     --change-batch '{"Changes":[{"Action":"DELETE",
     "ResourceRecordSet":{"Name":"old-cdn.shop.example.com.","Type":"A",
     "AliasTarget":{"DNSName":"d111abcdef9.cloudfront.net",
     "EvaluateTargetHealth":false}}}]}'
  3. CloudFront distribution IDs are globally unique — takeover is not
     possible, but the NXDOMAIN outage persists until the record is
     removed or redirected.
```

## What the skill caught that a generic assistant misses

1. **Failover is functionally disabled.** A generic assistant says "add a
   health check." The skill explains that without a health check on the
   PRIMARY, Route 53 has no failure signal — the PRIMARY is always
   considered healthy, and the SECONDARY is never served. The entire
   failover configuration is a no-op. This is CRITICAL, not just a
   recommendation.

2. **Failover SECONDARY without health check is NOT flagged.** The skill
   recognises that a SECONDARY without a health check is a valid fail-open
   pattern (always serve something when the primary fails), not a defect.
   A naive auditor flags both records equally.

3. **DNSSEC gap is additive.** Even though the worst finding is
   NO_HEALTH_CHECK/CRITICAL, the DNSSEC gap (HIGH) is also surfaced. The
   operator can triage both: fix failover first (CRITICAL), then enable
   DNSSEC (HIGH).

4. **CloudFront takeover risk is correctly assessed as LOW.** The skill
   notes that CloudFront distribution IDs are globally unique, so
   subdomain takeover is not possible — only NXDOMAIN. This distinguishes
   it from S3 website / API Gateway dangling records where takeover IS
   possible and the risk would be CRITICAL.

## Slash-command invocation

```
/aws:audit-route53-records
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Route 53 zone before Black Friday"
```

The orchestrator emits
`[Phase: Audit | Skills routed: route53-record-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit my Route 53 DNS failover"
# [Phase: Audit | Skills routed: route53-record-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the health check and DNSSEC, validate the posture:

```bash
# Verify the health check was created and is passing
aws route53 get-health-check-status --health-check-id <new-id> \
  --profile default

# Confirm DNSSEC signing is active
aws route53 get-dnssec --hosted-zone-id Z999PRODZONE --profile default

# Verify the dangling record was removed
aws route53 list-resource-record-sets --hosted-zone-id Z999PRODZONE \
  --profile default --output json | \
  jq '.ResourceRecordSets[] | select(.Name == "old-cdn.shop.example.com.")'

# Test failover by stopping the primary endpoint and confirming
# Route 53 serves the secondary within 30-90 seconds
dig api.shop.example.com +short
```

Then monitor CloudWatch metrics for `HealthCheckPercentHealthy` and Route
53 query volume for 1-2 weeks.
