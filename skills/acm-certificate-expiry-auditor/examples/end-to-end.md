# End-to-end usage scenario: acm-certificate-expiry-auditor

A walkthrough showing the skill auditing a three-certificate account batch
that exercises the decision tree's three highest-severity paths: a
FAILED_AUTORENEWAL renewal failure (CRITICAL), an EXPIRING_SOON +
AMAZON_ISSUED stall (HIGH), and an IMPORTED cert inside the re-import window
(MODERATE). Demonstrates verdict aggregation into a single POSTURE SUMMARY.

## Input (user prompt)

> Audit these three ACM certificates before tomorrow's production freeze. I
> need to know which ones need action tonight.

```yaml
certificate_1:
  ARN: arn:aws:acm:us-east-1:111111111111:certificate/prod-api-cert
  DomainName: api.prod.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-08-24T23:59:59Z
  RenewalEligibility: ELIGIBLE
  RenewalSummary:
    RenewalStatus: FAILED_AUTORENEWAL
    RenewalStatusReason: CAA_ERROR
    UpdatedAt: 2026-08-01T12:00:00Z
  KeyAlgorithm: RSA_2048
  InUseBy:
    - arn:aws:cloudfront::111111111111:distribution/EABC123

certificate_2:
  ARN: arn:aws:acm:us-east-1:111111111111:certificate/staging-web-cert
  DomainName: web.staging.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-08-19T23:59:59Z
  RenewalEligibility: ELIGIBLE
  RenewalSummary:
    RenewalStatus: PENDING_AUTORENEWAL
    UpdatedAt: 2026-08-01T12:00:00Z
  KeyAlgorithm: RSA_2048
  InUseBy: []

certificate_3:
  ARN: arn:aws:acm:us-east-1:111111111111:certificate/imported-portal-cert
  DomainName: portal.example.com
  Type: IMPORTED
  Status: ISSUED
  NotAfter: 2026-09-18T23:59:59Z
  RenewalEligibility: INELIGIBLE
  KeyAlgorithm: EC_prime256v1
  InUseBy:
    - arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/portal-alb/abc

today: 2026-08-04
```

## Skill output

```text
CERTIFICATE: api.prod.example.com (arn:aws:acm:us-east-1:111111111111:certificate/prod-api-cert)
VERDICT: RENEWAL_FAILED
RISK: CRITICAL
REASON: NotAfter 2026-08-24, days_until_expiry=20, Type AMAZON_ISSUED, Status ISSUED,
RenewalSummary.Status FAILED_AUTORENEWAL with RenewalStatusReason CAA_ERROR. ACM attempted
renewal and it failed because the domain's CAA record does not authorize ACM's issuer
(Step 2). With 20 days to expiry, this is inside the 30-day hard stop => CRITICAL.
CloudFront distribution EABC123 depends on this cert; a TLS outage at the edge is imminent
without intervention.
REMEDIATION: 1. Add or correct the CAA record: `prod.example.com. CAA 0 issue "amazon.com"`.
Wait for DNS propagation (TTL-dependent) and let ACM retry (up to 11 attempts before NotAfter).
2. If renewal does not complete within 7 days, re-request the certificate with DNS validation
as a fallback: `aws acm request-certificate --domain-name api.prod.example.com --validation-method DNS --region us-east-1`.
3. Verify CloudFront still serves the cert after renewal — CloudFront references certs by ARN,
so in-place renewal preserves the distribution config.

CERTIFICATE: web.staging.example.com (arn:aws:acm:us-east-1:111111111111:certificate/staging-web-cert)
VERDICT: EXPIRING_SOON
RISK: HIGH
REASON: NotAfter 2026-08-19, days_until_expiry=15, Type AMAZON_ISSUED, Status ISSUED,
RenewalEligibility ELIGIBLE, RenewalSummary.Status PENDING_AUTORENEWAL. Inside the 60-day
managed-renewal window and not yet renewed (Step 3: EXPIRING_SOON + AMAZON_ISSUED => HIGH).
ACM should have completed renewal by now — the managed-renewal contract is at risk.
REMEDIATION: 1. Diagnose the stall — verify the validation CNAME is resolvable and no CAA
record blocks ACM issuers. 2. If the CNAME is gone, re-add it from `DomainValidationOptions`;
ACM retries renewal automatically. 3. Monitor EventBridge for AWS Certificate Manager
Renewal events. 4. Do NOT wait past the 30-day hard stop — re-request with DNS validation
if renewal does not complete within 7 days.

CERTIFICATE: portal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/imported-portal-cert)
VERDICT: EXPIRING_SOON
RISK: MODERATE
REASON: NotAfter 2026-09-18, days_until_expiry=45, Type IMPORTED, Status ISSUED,
RenewalEligibility INELIGIBLE. Inside the 60-day re-import window for imported certs;
30 < 45 <= 60 => MODERATE (Step 3, IMPORTED branch). IMPORTED certs have no auto-renewal —
the operator must re-import before NotAfter.
REMEDIATION: Schedule re-import within the next 2 weeks. Source a new cert from the external
CA pipeline and re-import in place to preserve the ARN:
`aws acm import-certificate --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/imported-portal-cert \
--certificate file://new.pem --private-key file://new.key --certificate-chain file://chain.pem`.
Verify the chain includes all intermediates and that the SAN list matches the existing cert.

POSTURE SUMMARY
  certificates_audited: 3
  expired: 0
  renewal_failed: 1
  expiring_soon: 2
  ok: 0
  error: 0
  overall_risk: CRITICAL
  next_action: Fix the CAA record for prod.example.com NOW (certificate_1) — the cert is 20 days from expiry and renewal has already failed; the CloudFront distribution depends on it.
```

## What the skill caught that a generic assistant misses

1. **CAA_ERROR root-cause diagnosis.** A generic assistant says "renewal
   failed, check your DNS." The skill pinpoints the exact remediation: add a
   CAA record authorizing ACM's issuer (`amazon.com`), names the retry window
   (up to 11 attempts before NotAfter), and flags that CloudFront depends on
   the cert — an edge TLS outage is imminent.

2. **EXPIRING_SOON + AMAZON_ISSUED => HIGH rule.** The staging cert is still
   PENDING_AUTORENEWAL (not FAILED), so a naive auditor might say "it's
   pending, just wait." The skill classifies it EXPIRING_SOON/HIGH because
   the managed-renewal contract should have completed inside the 60-day
   window — waiting is the wrong action.

3. **IMPORTED re-import ARN preservation.** The baseline response suggests a
   plain `import-certificate` (which creates a NEW ARN and silently breaks
   the ALB listener). The skill's remediation uses `--certificate-arn` for
   in-place re-import, preserving the listener reference.

4. **Single aggregated POSTURE SUMMARY.** Three certs produce three
   per-cert blocks then ONE summary with `overall_risk: CRITICAL` (worst of
   the three) and a single prioritized `next_action`. No per-cert summary
   spam.

## Slash-command invocation

```
/aws:audit-acm-certificate-expiry
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit these ACM certificates before the production freeze"
```

The orchestrator emits
`[Phase: Audit | Skills routed: acm-certificate-expiry-auditor]` and hands off
to this skill for the VERDICT blocks.

## CLI routing

```bash
node cli/bin/cli.js route "audit these ACM certificates for expiry"
# [Phase: Audit | Skills routed: acm-certificate-expiry-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the account-wide posture:

```bash
aws acm list-certificates --profile default --region us-east-1 --output json
aws acm describe-certificate --certificate-arn <arn> --profile default --region us-east-1
```

For renewal-failed certs, confirm the fix took effect by watching the
EventBridge event stream for `AWS Certificate Manager Renewal` status
`SUCCESS` within 24 hours of the CAA/DNS fix.
