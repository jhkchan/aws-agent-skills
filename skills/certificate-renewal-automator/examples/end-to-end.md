# End-to-end usage scenario: certificate-renewal-automator

A walkthrough showing the skill designing renewal pipelines for two
certificates in the same account: an AUTOMATION_DEPLOYED DNS-validated
ALB cert and a REVIEW_REQUIRED imported orphaned cert. Demonstrates
the classification matrix and the managed-vs-manual renewal decision.

## Input (user prompt)

> Design cert renewal automation for our fleet. We have a
> DNS-validated cert on the production ALB and an imported cert from
> DigiCert that we think is no longer in use.

```
Design reference: prod-cert-renewal-rollout
Account: 111111111111
Region: us-east-1

Certificate 1: www.example.com (arn:aws:acm:us-east-1:111111111111:certificate/abc-123)
  Validation method: DNS
  Status: ISSUED, RenewalEligibility: ELIGIBLE
  Attached to: ALB listener arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/prod-alb/xyz/lst-001
  SAN domains: www.example.com, example.com
  DaysToExpiry: 58
  Route 53 hosted zone: Z1ABCDEF23456

Certificate 2: api.internal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/def-456)
  Validation method: IMPORTED (private key from DigiCert)
  Status: ISSUED, RenewalEligibility: INELIGIBLE
  InUseBy: []
  DaysToExpiry: 18
```

## Skill output

```text
RENEWAL: prod-cert-renewal-rollout
CERTIFICATE: www.example.com (arn:aws:acm:us-east-1:111111111111:certificate/abc-123)
CLASSIFICATION:
  - Validation: DNS
  - Attached to: ALB
  - Renewal path: MANAGED (ACM auto-renewal for DNS-validated cert on supported service)
DETECTION:
  - CloudWatch alarm: DaysToExpiry < 45 with SNS action
  - EventBridge scan: rate(1 day) Lambda cert-scan
RENEWAL_FLOW:
  - ACM managed: Yes (RenewalEligibility: ELIGIBLE)
  - Custom Lambda: Not required — managed renewal active
VALIDATION:
  - Method: DNS
  - Route 53 CNAME: _abc123.www.example.com -> _xyz789.acm-validations.aws.
  - SAN domains: www.example.com, example.com (both CNAMEs must persist)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
AUDIT:
  - CloudTrail: acm.amazonaws.com event tracking
  - SNI verification: openssl s_client -servername www.example.com
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws cloudwatch put-metric-alarm --alarm-name acm-www-expiring-45 --namespace AWS/CertificateManager --metric-name DaysToExpiry --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:111111111111:certificate/abc-123 --statistic Minimum --period 86400 --threshold 45 --comparison-operator LessThanThreshold --evaluation-periods 1 --alarm-actions arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts

RENEWAL: prod-cert-renewal-rollout
CERTIFICATE: api.internal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/def-456)
CLASSIFICATION:
  - Validation: IMPORTED (private key from DigiCert)
  - Attached to: ORPHANED (InUseBy: [])
  - Renewal path: MANUAL (ACM cannot renew imported certs)
DETECTION:
  - CloudWatch alarm: DaysToExpiry < 30 (fires but no auto-remediation possible)
  - EventBridge scan: flagged as HIGH risk (18 days to expiry)
RENEWAL_FLOW:
  - ACM managed: No (INELIGIBLE — imported cert)
  - Custom Lambda: Requires external CA renewal + re-import flow
VALIDATION:
  - Method: IMPORTED (N/A)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:cert-expiry-alerts
AUDIT:
  - CloudTrail: acm.amazonaws.com event tracking
VERDICT: REVIEW_REQUIRED
GAP: Imported private-key certificate with no managed renewal path, 18 days to expiry, and not attached to any resource. ACM cannot renew imported certs. Required: (1) Renew cert at DigiCert immediately — only 18 days remain; (2) export new cert+key+chain; (3) import via acm import-certificate to same ARN; (4) re-associate to target resource if still needed. If the cert is truly unused (InUseBy: []), consider deleting it. Recommend migrating to DNS-validated ACM cert or PCA-issued cert for future managed renewal.
TEMPLATE: (manual import flow — see references/imported-cert-manual-renewal.md)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for the ALB cert
+ REVIEW_REQUIRED for the imported cert.** The ALB cert requires no
action (managed renewal active). The imported cert requires immediate
manual renewal (18 days) and should be evaluated for deletion or
migration to DNS-validated ACM.

## What the skill caught that a generic assistant misses

1. **The managed-renewal eligibility check.** A generic assistant
   says "ACM handles renewal." The skill checks `RenewalEligibility`
   and `InUseBy` — the ALB cert is ELIGIBLE and attached (managed
   renewal active), while the imported cert is INELIGIBLE and orphaned
   (no managed renewal possible).

2. **The SAN validation persistence requirement.** A generic assistant
   does not flag that DNS validation CNAMEs must persist. The skill
   notes both SAN domains' CNAMEs must remain in Route 53 for the
   cert's lifetime.

3. **The orphaned-cert trap.** A generic assistant overlooks the empty
   `InUseBy` on the imported cert. The skill flags it as orphaned,
   prompting the operator to decide whether the cert is still needed.

4. **The time-critical alert.** A generic assistant provides generic
   advice. The skill highlights that 18 days is urgent and recommends
   immediate action at DigiCert.

5. **The migration path.** A generic assistant does not suggest
   migrating imported certs to DNS-validated ACM. The skill recommends
   this as a permanent fix to eliminate future manual renewal.

## Slash-command invocation

```
/aws:automate-certificate-renewal
```

## CLI routing

```bash
node cli/bin/cli.js route "automate certificate renewal"
# [Phase: Automate | Skills routed: certificate-renewal-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# List all certificates with status
aws acm list-certificates --certificate-statuses ISSUED PENDING_VALIDATION \
  --region us-east-1 --profile default

# Detailed status for each cert
for arn in $(aws acm list-certificates --query 'CertificateSummaryList[].CertificateArn' --output text --region us-east-1); do
  aws acm describe-certificate --certificate-arn $arn \
    --query 'Certificate.{Domain:DomainName,Status:Status,Eligibility:RenewalEligibility,InUseBy:InUseBy,NotAfter:NotAfter}' \
    --region us-east-1 --profile default
done

# Check PCA CA health
aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[].{ARN:Arn,Status:Status,NotAfter:NotAfter}' \
  --region us-east-1 --profile default

# CloudTrail audit of cert API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=acm.amazonaws.com \
  --start-time $(date -v-1d +%Y-%m-%dT%H:%M:%S) \
  --region us-east-1 --profile default
```

Then paste the output into the skill for renewal pipeline design.
