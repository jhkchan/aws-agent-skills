---
name: acm-certificate-monitor-operator
description: >-
  Operates AWS ACM certificate monitoring and expiry tracking with
  production defaults: DaysToExpiry CloudWatch alarm creation
  (threshold <30 days warning, <7 days critical), multi-region
  certificate inventory, certificate renewal status tracking
  (PENDING_VALIDATION, ISSUED, EXPIRED), DNS validation record
  verification, CAA record conflict detection, multi-account
  certificate audit via Organizations, certificate-to-load-balancer
  mapping, automated renewal failure detection, SNS notification on
  expiry alarm, wildcard vs SAN coverage audit, and private
  certificate (ACM PCA) monitoring. Emits an OPERATION_COMPLETED
  report with verification commands. Use when auditing ACM
  certificate expiry, setting up expiry alarms, verifying renewal,
  detecting CAA conflicts, or mapping certificates to resources.
  Triggers acm certificate monitoring, certificate expiry alarm,
  days to expiry, caa record conflict, multi-account audit, acm pca.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live operations: AWS CLI v2 with acm, acm-pca,
  cloudwatch, elasticloadbalancingv2, cloudfront, apigateway, and
  organizations access. Works with Terraform
  aws_acm_certificate, aws_cloudwatch_metric_alarm, and
  aws_sns_topic resources and CloudFormation
  AWS::CertificateManager::Certificate templates.
keywords:
  - aws
  - acm
  - certificate
  - certificate manager
  - expiry
  - days to expiry
  - cloudops
  - operate
  - monitoring
  - renewal
  - caa record
  - dns validation
  - multi-account
  - wildcard
  - san
  - acm pca
tags:
  - aws
  - acm
  - certificate-manager
  - certificate-expiry
  - cloudops
  - operate
  - monitoring
  - renewal
  - caa-record
  - dns-validation
  - multi-account
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPERATION_COMPLETED | REVIEW_REQUIRED"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - acm
    - certificate-manager
    - certificate-expiry
    - cloudops
    - operate
    - monitoring
    - renewal
    - caa-record
    - dns-validation
    - multi-account
  dependencies:
    - aws-orchestrator
  keywords:
    - acm certificate monitoring
    - certificate expiry alarm
    - days to expiry
    - certificate renewal status
    - caa record conflict
    - multi-account certificate audit
    - certificate load balancer mapping
    - acm pca monitoring
  when_to_use: >-
    Invoke when the user wants to audit ACM certificate expiry, set up
    DaysToExpiry CloudWatch alarms, verify certificate renewal status,
    detect CAA record conflicts, perform multi-account or multi-region
    certificate inventory, map certificates to load balancers, monitor
    private certificates via ACM PCA, or verify DNS validation records.
    Do NOT invoke for issuing/provisioning new certificates (use ACM
    provisioning skills), IAM server certificates (non-ACM), or
    third-party CA certificate management.
---

# ACM Certificate Monitor Operator

An AWS CloudOps agent skill that operates ACM certificate monitoring
and expiry tracking with correct defaults. The skill walks the
operator through DaysToExpiry CloudWatch alarm creation, multi-region
and multi-account certificate inventory, renewal status verification,
DNS validation record checks, CAA record conflict detection,
certificate-to-resource mapping, renewal failure detection, SNS
notification configuration, and private certificate (ACM PCA)
monitoring. It captures all monitoring decisions, explains why each
check matters, and emits an OPERATION_COMPLETED report with copy-
pasteable verification commands.

## Activation keywords

ACM certificate monitoring, certificate expiry alarm, DaysToExpiry,
certificate renewal status, CAA record conflict, multi-account
certificate audit, certificate load balancer mapping, ACM PCA
monitoring.

## STRICT output contract

When this skill is invoked with an ACM certificate monitoring request
(audit expiry, set up alarms, verify renewal, detect conflicts,
inventory certificates, or a partial monitoring task), the agent MUST
respond with the OPERATION_COMPLETED report defined in the "Output
format" section using the literal all-caps labels `ACM_MONITORING:`,
`VERDICT:`, `FINDINGS:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the report with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is what
assertion-based evals and downstream monitoring pipelines rely on;
deviating from the literal labels breaks automation silently.

If any issue requires human review (CAA conflict, renewal failure,
validation record missing), the verdict is `REVIEW_REQUIRED` with a
specific issue citation in the findings, and `OPERATION_COMPLETED`
MUST NOT also appear unless the operational task itself succeeded but
issues were found during execution.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before operating |
| Step 1 — DaysToExpiry metric fundamentals | Core monitoring metric |
| Step 2 — Certificate expiry alarm tiers | Warning (<30d) and critical (<7d) |
| Step 3 — Multi-region certificate inventory | Region coverage |
| Step 4 — Certificate renewal status tracking | PENDING_VALIDATION / ISSUED / EXPIRED |
| Step 5 — DNS validation record verification | Validation health |
| Step 6 — CAA record conflict detection | Silent renewal blocker |
| Step 7 — Certificate-to-load-balancer mapping | Resource association |
| Step 8 — Multi-account audit via Organizations | Org-wide inventory |
| Step 9 — Automated renewal failure detection | Renewal health |
| Step 10 — SNS notification on expiry alarm | Alert routing |
| Step 11 — Wildcard vs SAN coverage audit | Coverage analysis |
| Step 12 — Private certificate (ACM PCA) monitoring | Private CA certs |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal report template |
| references/dns-and-caa-validation.md | DNS validation + CAA detail |
| references/multi-account-and-pca.md | Multi-account + PCA detail |

## Mindset

**One-line takeaway:** The `DaysToExpiry` metric is the primary
monitoring signal for ACM certificates. ACM auto-renews certificates
that are DNS-validated and attached to supported AWS services (ALB,
NLB, CloudFront, API Gateway, etc.), but renewal can silently fail if
CAA records conflict, DNS validation records are removed, or the
certificate is not attached to a supported service. Always monitor
DaysToExpiry with tiered alarms (warning <30 days, critical <7 days)
and verify renewal status proactively.

Three misconceptions dominate ACM certificate monitoring at operation
time:

- **"ACM auto-renews all certificates."** It does NOT. ACM auto-renews
  only certificates that meet ALL of these conditions: (1) DNS-
  validated (email-validated certs require manual action), (2) issued
  (not in PENDING_VALIDATION), (3) currently in use (attached to a
  supported AWS service like ALB, NLB, CloudFront, API Gateway), and
  (4) not blocked by CAA record conflicts. A certificate that is
  issued but not attached to any resource will NOT be auto-renewed.

- **"DaysToExpiry alarm is unnecessary because ACM renews
  automatically."** It IS necessary. Even with auto-renewal, CAA
  record changes, DNS configuration changes, or service detachment can
  silently block renewal. The certificate will continue approaching
  expiry without any visible error until the DaysToExpiry alarm fires.
  Without monitoring, the first sign of a problem is a production
  outage when the certificate expires.

- **"CAA records are set once and never cause issues."** CAA records
  can be added or modified by any party with DNS access (including
  DNS providers' automated processes). A CAA record that restricts
  certificate issuance to a specific CA (e.g., only Let's Encrypt)
  will silently block ACM renewal. CAA conflicts are the #1 cause of
  unexpected ACM renewal failures.

## Configuration dependency graph (novel heuristic)

ACM certificate monitoring is NOT a single check. The DaysToExpiry
metric is the primary signal, but renewal depends on DNS validation,
CAA records, service attachment, and certificate status. Use this
graph to sequence monitoring checks.

| Check | Hard dependencies (fails without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| DaysToExpiry alarm | certificate in ISSUED state; CloudWatch metric available for the certificate | DaysToExpiry = -1 if cert is not ISSUED or not eligible for renewal monitoring | expiry alerting |
| Certificate status | certificate exists in ACM | PENDING_VALIDATION certs do not have a valid DaysToExpiry; EXPIRED certs need re-issuance | renewal tracking |
| DNS validation record | certificate was DNS-validated; CNAME validation record exists in Route53 (or other DNS) | if the validation CNAME is deleted, renewal fails silently; ACM shows status as PENDING_VALIDATION or VALIDATION_TIMED_OUT | renewal eligibility |
| CAA record check | domain's DNS zone accessible; CAA record query possible | CAA records can be set at the zone apex or subdomain level; restrictive CAA blocks ACM silently | renewal unblocking |
| Service attachment | certificate attached to ALB/NLB/CloudFront/API Gateway/etc. | unattached certificates are NOT auto-renewed; ACM does not alert on detachment | auto-renewal eligibility |
| Renewal status | certificate eligible for renewal (60 days before expiry) | ACM attempts renewal starting 60 days before expiry; failures are not always immediately visible | renewal confirmation |
| Multi-region inventory | per-region API calls (list-certificates is region-scoped) | certificates are regional resources (except CloudFront which uses us-east-1); missing a region = missing certs | complete inventory |
| Multi-account audit | Organizations all-features enabled; assume-role access to member accounts | without Organizations access or cross-account roles, cannot inventory member account certs | org-wide visibility |
| Private cert (PCA) | ACM PCA private CA exists; private certificates issued | private cert renewal depends on PCA CA certificate health; PCA CA cert expiry is a separate alarm | private cert monitoring |

**The CAA-record row is the one a baseline model misses.** CAA
records are the #1 silent renewal blocker. The DaysToExpiry alarm
fires, the operator sees the cert approaching expiry, but the renewal
keeps failing because a CAA record was added (possibly by another
team or DNS provider automation) that restricts issuance to a
different CA. The procedure below forces an explicit CAA check.

**Cross-dependency gotchas:**
- DaysToExpiry monitoring requires the certificate to be ISSUED.
  PENDING_VALIDATION or EXPIRED certificates need different handling.
- Auto-renewal requires the certificate to be attached to a supported
  service. Detaching the certificate stops auto-renewal silently.
- DNS-validated certificates auto-renew; email-validated certificates
  require manual approval of the renewal email.
- CAA records can be set at the zone apex, affecting all subdomains.
  A wildcard cert (`*.example.com`) can be blocked by a CAA record on
  `example.com`.
- Private certificates (via ACM PCA) have a separate renewal cycle
  that depends on the PCA CA certificate health.

## Expert heuristic: the DaysToExpiry tiered alarm model

A baseline model says "set an alarm for certificate expiry." The
correct heuristic recognizes that DaysToExpiry needs tiered thresholds
for graduated response.

```text
DaysToExpiry timeline for a 1-year certificate (365 days):

  365 ──────────────────────────────────────────────────────── 0
       │                  │              │         │           │
       │                  │              │         │           └─ EXPIRED (outage)
       │                  │              │         │
       │                  │              │         └─ <7 days: CRITICAL alarm
       │                  │              │              (page on-call, escalate)
       │                  │              │
       │                  │              └─ <30 days: WARNING alarm
       │                  │                   (notify team, verify renewal)
       │                  │
       │                  └─ ~60 days: ACM begins auto-renewal attempts
       │                       (renewal should complete here for healthy certs)
       │
       └─ 365 days: certificate issued/renewed

Alarm tiers:
  WARNING (< 30 days)  → SNS topic: cert-warning-notifications
  CRITICAL (< 7 days)  → SNS topic: cert-critical-escalation
```

**Key implication:** the warning alarm at 30 days gives the team
ample time to investigate and fix renewal issues before the critical
alarm at 7 days forces emergency action. This two-tier approach
prevents certificate-expiry production outages.

## Expert heuristic: CAA record conflict detection

CAA (Certification Authority Authorization) DNS records specify which
CAs are allowed to issue certificates for a domain. ACM requires a CAA
record that permits Amazon (issuer: `amazon.com`) or no CAA record at
all. A CAA record that does NOT include `amazon.com` silently blocks
ACM renewal.

```text
CAA record scenarios:
  ├── No CAA records → Any CA can issue → ACM renewal OK
  ├── CAA record includes amazon.com → ACM can issue → renewal OK
  ├── CAA record includes only letsencrypt.org → ACM BLOCKED
  │     Issue: "amazon.com" not in CAA allowlist
  │     Symptom: renewal status stays PENDING_VALIDATION, DaysToExpiry keeps decreasing
  │     Fix: add CAA record for amazon.com OR remove restrictive CAA
  └── CAA record includes amazon.com + issuewild → wildcard renewal OK
        issuewild controls wildcard cert issuance specifically

Detection:
  dig caa example.com +short
  # Expected for ACM-compatible: 0 issue "amazon.com"
  # Or: no output (no CAA records)
```

**Key implication:** always check CAA records when renewal fails. The
DaysToExpiry alarm fires but the renewal does not complete because the
CAA record blocks ACM. This is the #1 renewal failure cause and is
invisible without an explicit DNS check.

## Expert heuristic: auto-renewal eligibility checklist

Not all certificates auto-renew. Use this checklist to determine
whether a certificate is eligible for ACM auto-renewal.

```text
Auto-renewal eligibility:
  ├── [1] Validation method = DNS-validated?
  │     ├── YES → continue
  │     └── NO (email-validated) → requires manual email approval for renewal
  │
  ├── [2] Certificate status = ISSUED?
  │     ├── YES → continue
  │     └── NO (PENDING_VALIDATION) → not yet issued, cannot renew
  │
  ├── [3] Certificate attached to a supported service?
  │     ├── YES (ALB, NLB, CloudFront, API Gateway, AppSync, etc.) → continue
  │     └── NO (not attached) → ACM does NOT auto-renew unattached certificates
  │
  ├── [4] DNS validation CNAME records still present?
  │     ├── YES → continue
  │     └── NO (records deleted) → renewal fails; ACM shows VALIDATION_TIMED_OUT
  │
  ├── [5] CAA records permit amazon.com?
  │     ├── YES (or no CAA records) → continue
  │     └── NO → renewal silently blocked
  │
  └── ALL YES → certificate auto-renews (ACM attempts ~60 days before expiry)
```

**Key implication:** a certificate that was auto-renewing can stop
renewing if any of these conditions change (service detachment, DNS
record deletion, CAA record addition). DaysToExpiry monitoring catches
this, but the root cause requires investigating each eligibility
factor.

## Prerequisites (verify before operating)

Before emitting monitoring commands, verify these prerequisites. If
any are missing, the verdict is **REVIEW_REQUIRED**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| ACM certificates exist in target region(s) | Need certs to monitor | `aws acm list-certificates --region <region>` |
| CloudWatch metrics available | DaysToExpiry is a CloudWatch metric | `aws cloudwatch get-metric-statistics --namespace AWS/CertificateManager --metric-name DaysToExpiry` |
| SNS topics for alarm notifications | Alarms need SNS topics to notify | `aws sns list-topics` |
| IAM permissions | Need acm:DescribeCertificate, cloudwatch:PutMetricAlarm, acm:ListCertificates | Verify IAM policy |
| DNS access for CAA checks | CAA record detection requires DNS query access | `dig` or `nslookup` available, or Route53 API access |
| Organizations access (for multi-account) | Multi-account audit requires Organizations or cross-account roles | `aws organizations describe-organization` |
| Region list identified | ACM is regional; must check each region individually | Identify active regions for the workload |

If any prerequisite is missing, output `VERDICT: REVIEW_REQUIRED`
and cite the specific gap.

## Step 1 — DaysToExpiry metric fundamentals

The `AWS/CertificateManager > DaysToExpiry` metric is the primary
monitoring signal for ACM certificates. It reports the number of days
until the certificate expires.

| Metric attribute | Value |
|---|---|
| Namespace | `AWS/CertificateManager` |
| MetricName | `DaysToExpiry` |
| Dimension | `CertificateArn` |
| Statistics | `Average` (or `Minimum` for worst case) |
| Period | `86400` (1 day — the metric updates daily) |
| Unit | `Count` (days) |
| Available for | ISSUED certificates only |

**Key behavior:** the metric reports `-1` when the certificate is not
eligible for DaysToExpiry monitoring (e.g., PENDING_VALIDATION, or
self-signed certs that are not managed by ACM for renewal).

**Verify the metric is available:**

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistics Average \
  --period 86400 \
  --start-time $(date -u -v-3d +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --region us-east-1
```

## Step 2 — Certificate expiry alarm tiers

Create tiered CloudWatch alarms on DaysToExpiry for graduated response.

### Warning alarm (< 30 days)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "acm-cert-warning-<cert-id>" \
  --alarm-description "ACM certificate expires in < 30 days" \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistic Average \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data "breaching" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-warning-notifications" \
  --region us-east-1
```

### Critical alarm (< 7 days)

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "acm-cert-critical-<cert-id>" \
  --alarm-description "ACM certificate expires in < 7 days — URGENT" \
  --namespace AWS/CertificateManager \
  --metric-name DaysToExpiry \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --statistic Average \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 7 \
  --comparison-operator LessThanThreshold \
  --treat-missing-data "breaching" \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
  --ok-actions "arn:aws:sns:us-east-1:123456789012:cert-critical-escalation" \
  --region us-east-1
```

**Alarm behavior:**

| Condition | Warning alarm | Critical alarm |
|---|---|---|
| DaysToExpiry > 30 | OK | OK |
| DaysToExpiry 8-30 | ALARM | OK |
| DaysToExpiry < 7 | ALARM | ALARM |
| DaysToExpiry = -1 (ineligible) | OK | OK |
| Missing data | ALARM (breaching) | ALARM (breaching) |

**Critical:** set `--treat-missing-data "breaching"` so that if the
metric stops reporting (e.g., certificate is deleted and re-created),
the alarm fires rather than going to INSUFFICIENT_DATA.

## Step 3 — Multi-region certificate inventory

ACM certificates are regional resources. CloudFront distributions use
certificates from us-east-1. To get a complete inventory, list
certificates in ALL active regions.

```bash
# List certificates across all enabled regions
for REGION in $(aws account get-contact-information \
  --query 'ContactInformation' --output text 2>/dev/null \
  || aws ec2 describe-regions --query 'Regions[*].RegionName' --output text | tr '\t' '\n'); do
  echo "=== Region: $REGION ==="
  aws acm list-certificates --region "$REGION" \
    --output table \
    --query 'CertificateSummaryList[*].{Domain:DomainName,Arn:CertificateArn,Type:Type}'
done
```

**Or for a specific set of regions:**

```bash
for REGION in us-east-1 us-west-2 eu-west-1 ap-southeast-1; do
  echo "=== Region: $REGION ==="
  aws acm list-certificates --region "$REGION" \
    --query 'CertificateSummaryList[*].{Domain:DomainName,Status:Status,Arn:CertificateArn}' \
    --output table
done
```

**Detail per certificate:**

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --query 'Certificate.{Domain:DomainName,Status:Status,Type:Type,Issuer:Issuer,NotAfter:NotAfter,NotBefore:NotBefore,KeyAlgorithm:KeyAlgorithm,ValidationMethod:DomainValidationOptions[0].ValidationMethod,RenewalEligibility:RenewalEligibility}' \
  --region us-east-1 --output table
```

## Step 4 — Certificate renewal status tracking

Each ACM certificate has a status and renewal eligibility that
indicates whether it will auto-renew.

| Status | Meaning | Action needed |
|---|---|---|
| `PENDING_VALIDATION` | Certificate requested but not yet validated/issued | Complete DNS or email validation |
| `ISSUED` | Certificate is active and valid | Monitor DaysToExpiry |
| `INACTIVE` | Certificate is not in use | Verify if still needed |
| `EXPIRED` | Certificate has passed its expiry date | Request a new certificate |
| `VALIDATION_TIMED_OUT` | Validation was not completed in time | Re-request and validate |
| `REVOKED` | Certificate has been revoked | Investigate and re-issue |
| `FAILED` | Certificate request failed | Re-request |

**Renewal eligibility:**

| RenewalEligibility | Meaning |
|---|---|
| `ELIGIBLE` | Certificate is within 60 days of expiry and eligible for auto-renewal |
| `INELIGIBLE` | Certificate is not yet in the renewal window (>60 days) or does not meet auto-renewal criteria |

**Check renewal status:**

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --query 'Certificate.{Status:Status,RenewalEligibility:RenewalEligibility,DomainValidation:DomainValidationOptions[*].{Domain:DomainName,ValidationStatus:ValidationStatus,ValidationMethod:ValidationMethod},RenewalSummary:RenewalSummary}' \
  --region us-east-1 --output table
```

**If `RenewalSummary` is present**, ACM has begun the renewal process.
Check `RenewalSummary.RenewalStatus` for `PENDING_AUTO_RENEWAL`,
`SUCCESS`, or `FAILED`.

## Step 5 — DNS validation record verification

DNS-validated certificates have CNAME records that ACM uses to verify
domain ownership. These records MUST remain in DNS for the certificate
to renew.

**Retrieve the validation CNAME records:**

```bash
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123-def456 \
  --query 'Certificate.DomainValidationOptions[*].{Domain:DomainName,ValidationStatus:ValidationStatus,CNAMEName:ResourceRecord.Name,CNAMEValue:ResourceRecord.Value}' \
  --region us-east-1 --output table
```

**Verify the CNAME exists in DNS:**

```bash
# Check if the validation CNAME resolves
dig _abc123.example.com.example.com CNAME +short
# Expected: the CNAME value from ACM

# Or using nslookup
nslookup -type=CNAME _abc123.example.com.example.com
```

**Verify via Route53 (if DNS is in Route53):**

```bash
# Check Route53 for the validation record
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name example.com \
  --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

aws route53 list-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --query "ResourceRecordSets[?Type=='CNAME' && starts_with(Name, '_acm-challenge')]" \
  --output table
```

**Critical:** if the validation CNAME is missing from DNS, renewal
will fail. The certificate status will show `PENDING_VALIDATION` or
the renewal summary will show `FAILED`.

## Step 6 — CAA record conflict detection

CAA records are the #1 silent blocker of ACM certificate renewal. A
CAA record that does not include `amazon.com` prevents ACM from
renewing the certificate.

**Check CAA records for the domain:**

```bash
# Query CAA records for the domain
dig example.com CAA +short

# Or for a specific subdomain
dig www.example.com CAA +short

# Using nslookup
nslookup -type=CAA example.com
```

**Interpret CAA results:**

| CAA record | Effect on ACM renewal |
|---|---|
| No CAA records (empty output) | No restriction — ACM renewal OK |
| `0 issue "amazon.com"` | ACM is authorized — renewal OK |
| `0 issue "amazon.com"; 0 issue "letsencrypt.org"` | ACM is authorized — renewal OK |
| `0 issue "letsencrypt.org"` (no amazon.com) | ACM BLOCKED — add amazon.com or remove restrictive CAA |
| `0 issuewild "amazon.com"` | Wildcard certs OK; non-wildcard needs separate `issue` record |
| `0 issue ";"` | No CA is authorized — ALL renewal blocked |

**Fix CAA conflict (Route53):**

```bash
# Add amazon.com to the CAA records
ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name example.com \
  --query 'HostedZones[0].Id' --output text | sed 's|/hostedzone/||')

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{
    "Changes": [
      {"Action":"UPSERT","ResourceRecordSet":{"Name":"example.com","Type":"CAA","TTL":300,"ResourceRecords":[{"Value":"0 issue \"amazon.com\""}]}}
    ]
  }'
```

**Key implication:** CAA records can be modified by anyone with DNS
access. A CAA conflict can appear at any time, even for certificates
that were previously renewing fine. Include CAA checks in periodic
certificate health audits.

## Step 7 — Certificate-to-load-balancer mapping

ACM certificates must be attached to supported services for auto-
renewal. The most common attachment is to load balancers (ALB/NLB).

**Find certificates attached to ALBs/NLBs:**

```bash
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].{Name:LoadBalancerName,ARN:LoadBalancerArn,DNS:DNSName}' \
  --region us-east-1 --output table

# Get listeners with certificate details
for LB_ARN in $(aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[*].LoadBalancerArn' --output text --region us-east-1); do
  echo "=== LB: $LB_ARN ==="
  aws elbv2 describe-listeners \
    --load-balancer-arn "$LB_ARN" \
    --query 'Listeners[*].{Protocol:Protocol,Port:Port,Certificates:Certificates[*].CertificateArn}' \
    --region us-east-1 --output table
done
```

**Find certificates attached to CloudFront distributions:**

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].{Domain:DomainName,ViewerCert:ViewerCertificate.ACMCertificateArn}' \
  --output table --region us-east-1
```

**Find certificates attached to API Gateway (custom domains):**

```bash
aws apigateway get-domain-names \
  --query 'items[*].{Domain:domainName,Cert:certificateName,Arn:certificateArn}' \
  --output table --region us-east-1
```

**Identify unattached certificates (at risk of not auto-renewing):**

```bash
# List all certs, then cross-reference with attached certs
ALL_CERTS=$(aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' \
  --output text --region us-east-1)

ATTACHED_CERTS=$(aws elbv2 describe-listeners \
  --query 'Listeners[*].Certificates[*].CertificateArn' \
  --output text --region us-east-1 | tr '\t' '\n' | sort -u)

# Also check CloudFront (uses us-east-1 certs)
CF_CERTS=$(aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].ViewerCertificate.ACMCertificateArn' \
  --output text --region us-east-1 | tr '\t' '\n' | sort -u)

echo "Unattached certificates (not on any ALB/NLB or CloudFront):"
for CERT in $ALL_CERTS; do
  if ! echo "$ATTACHED_CERTS $CF_CERTS" | grep -q "$CERT"; then
    echo "  $CERT"
  fi
done
```

**Critical:** unattached certificates are NOT auto-renewed by ACM.
Either re-attach them or delete them if no longer needed.

## Step 8 — Multi-account audit via Organizations

For organizations with multiple AWS accounts, use Organizations to
audit certificates across all member accounts.

**Prerequisites:**
- Organizations all-features enabled.
- A monitoring role in each member account with ACM read access.
- The audit account can assume the monitoring role in each member.

**List all accounts in the organization:**

```bash
aws organizations list-accounts \
  --query 'Accounts[*].{Id:Id,Name:Name,Status:Status}' \
  --output table
```

**Audit certificates in each account:**

```bash
for ACCT_ID in $(aws organizations list-accounts \
  --query 'Accounts[?Status==`ACTIVE`].Id' --output text | tr '\t' '\n'); do
  echo "=== Account: $ACCT_ID ==="

  # Assume the monitoring role in the member account
  CREDS=$(aws sts assume-role \
    --role-arn "arn:aws:iam::$ACCT_ID:role/ACMMonitoringRole" \
    --role-session-name "acm-audit" \
    --query 'Credentials' --output json)

  export AWS_ACCESS_KEY_ID=$(echo "$CREDS" | jq -r '.AccessKeyId')
  export AWS_SECRET_ACCESS_KEY=$(echo "$CREDS" | jq -r '.SecretAccessKey')
  export AWS_SESSION_TOKEN=$(echo "$CREDS" | jq -r '.SessionToken')

  for REGION in us-east-1 us-west-2 eu-west-1; do
    echo "  Region: $REGION"
    aws acm list-certificates --region "$REGION" \
      --query 'CertificateSummaryList[*].{Domain:DomainName,Status:Status}' \
      --output table
  done

  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
done
```

**Aggregate report:** collect all certificates across accounts and
regions into a single inventory with status, expiry, and renewal
eligibility.

## Step 9 — Automated renewal failure detection

ACM attempts auto-renewal starting 60 days before expiry. Renewal
failures are not always immediately visible in the console. Detect
them via API.

**Check renewal status for all ISSUED certificates:**

```bash
for CERT_ARN in $(aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' \
  --output text --region us-east-1); do

  RENEWAL_STATUS=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --query 'Certificate.RenewalSummary.RenewalStatus' \
    --output text --region us-east-1 2>/dev/null)

  if [ "$RENEWAL_STATUS" = "FAILED" ]; then
    echo "RENEWAL FAILED: $CERT_ARN"
    aws acm describe-certificate \
      --certificate-arn "$CERT_ARN" \
      --query 'Certificate.{Domain:DomainName,RenewalSummary:RenewalSummary}' \
      --output table --region us-east-1
  fi
done
```

**Renewal failure reasons:**

| Reason | Description | Fix |
|---|---|---|
| CAA record conflict | CAA does not permit amazon.com | Add CAA record for amazon.com |
| DNS validation record missing | Validation CNAME deleted from DNS | Re-add the CNAME record |
| Email validation not approved | Email-validated cert; approval email not actioned | Approve via email link |
| Certificate not in use | Not attached to a supported service | Attach to ALB/NLB/CloudFront/etc. |
| Domain ownership changed | Domain transferred or DNS changed | Re-validate domain ownership |

## Step 10 — SNS notification on expiry alarm

Each DaysToExpiry alarm should route to an SNS topic for notification.
Use different topics for warning vs critical severity.

**Create SNS topics:**

```bash
# Warning topic (30-day notifications)
WARNING_TOPIC=$(aws sns create-topic \
  --name "acm-cert-warning-notifications" \
  --query 'TopicArn' --output text --region us-east-1)

# Critical topic (7-day escalation)
CRITICAL_TOPIC=$(aws sns create-topic \
  --name "acm-cert-critical-escalation" \
  --query 'TopicArn' --output text --region us-east-1)

# Subscribe email endpoints
aws sns subscribe \
  --topic-arn "$WARNING_TOPIC" \
  --protocol email \
  --notification-endpoint "devops-team@example.com" \
  --region us-east-1

aws sns subscribe \
  --topic-arn "$CRITICAL_TOPIC" \
  --protocol email \
  --notification-endpoint "oncall@example.com" \
  --region us-east-1
```

**Slack integration via SNS + Lambda:**

```bash
# Create a Lambda that forwards SNS to Slack
# Subscribe the Lambda to the SNS topic
aws sns subscribe \
  --topic-arn "$CRITICAL_TOPIC" \
  --protocol lambda \
  --notification-endpoint "arn:aws:lambda:us-east-1:123456789012:function:sns-to-slack" \
  --region us-east-1
```

## Step 11 — Wildcard vs SAN coverage audit

ACM certificates can cover multiple domains via wildcard (`*.example.com`)
and Subject Alternative Names (SANs). Audit coverage to ensure all
subdomains are protected.

```bash
# List all domains covered by each certificate
for CERT_ARN in $(aws acm list-certificates \
  --certificate-statuses ISSUED \
  --query 'CertificateSummaryList[*].CertificateArn' \
  --output text --region us-east-1); do

  echo "=== Certificate: $(echo $CERT_ARN | cut -d'/' -f2) ==="
  aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --query 'Certificate.{PrimaryDomain:DomainName,SANs:SubjectAlternativeNames,Wildcard:DomainValidationOptions[0].ValidationMethod}' \
    --output table --region us-east-1
done
```

**Coverage analysis:**

| Certificate type | Coverage | Example |
|---|---|---|
| Wildcard | All first-level subdomains | `*.example.com` covers `www.example.com`, `api.example.com` |
| Wildcard (NOT multi-level) | Only first-level subdomains | `*.example.com` does NOT cover `a.b.example.com` |
| SAN | Explicitly listed domains | `example.com, www.example.com, api.example.com` |
| Wildcard + SAN | Both | `*.example.com, example.com` (covers apex + subdomains) |

**Key implication:** wildcard certs cover only ONE level of
subdomain. For deeper subdomain structures, add SANs or separate
wildcard certs.

## Step 12 — Private certificate (ACM PCA) monitoring

ACM Private Certificate Authority (ACM PCA) issues private
certificates for internal use. These have separate monitoring
considerations.

**Monitor PCA CA certificate expiry:**

```bash
# List private CAs
aws acm-pca list-certificate-authorities \
  --query 'CertificateAuthorities[*].{Arn:Arn,Status:Status,Type:Type,NotAfter:NotAfter,CommonName:CertificateAuthorityConfiguration.Subject.CommonName}' \
  --output table --region us-east-1

# Check PCA CA certificate details
aws acm-pa describe-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc123-def456 \
  --query 'CertificateAuthority.{Status:Status,NotBefore:NotBefore,NotAfter:NotAfter}' \
  --region us-east-1 --output table
```

**Create alarm on PCA CA certificate expiry (days to expiry computed from NotAfter):**

```bash
# PCA CA certs don't have a built-in DaysToExpiry metric.
# Compute days remaining and alarm via a custom metric or EventBridge rule.

# Get the CA cert NotAfter date and compute days remaining
NOT_AFTER=$(aws acm-pca describe-certificate-authority \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/abc123-def456 \
  --query 'CertificateAuthority.NotAfter' --output text --region us-east-1)

DAYS_REMAINING=$(( ( $(date -d "$NOT_AFTER" +%s) - $(date +%s) ) / 86400 ))
echo "PCA CA cert days remaining: $DAYS_REMAINING"
```

**Private cert monitoring considerations:**
- Private certificates issued by ACM PCA do NOT auto-renew via ACM.
- Private certificates must be renewed manually or via API calls.
- The PCA CA certificate itself has a long validity period (10 years
  by default) but must be monitored for eventual expiry.
- If the PCA CA certificate expires, all private certs issued by that
  CA become invalid.

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **ACM multi-region certificates (2023-2024):** ACM introduced
  multi-region certificates that are managed across multiple regions
  for global applications using Route53 latency-based routing. These
  certs appear in multiple regions simultaneously.

- **Enhanced renewal visibility (2023-2024):** ACM improved the
  renewal summary in the API to include detailed failure reasons,
  making it easier to diagnose why renewal failed without checking DNS
  or CAA separately.

- **PCA short-lived certificate support (2023-2024):** ACM PCA added
  support for short-lived certificates (hours to days), requiring more
  frequent monitoring and renewal automation.

- **CloudTrail integration for certificate events (2023-2024):**
  Enhanced CloudTrail events for ACM certificate lifecycle changes,
  including renewal attempts, validation status changes, and CAA
  conflict detection events.

- **EventBridge renewal failure events (2024-2025):** ACM now emits
  EventBridge events when renewal fails, enabling automated response
  (e.g., Lambda to fix CAA records or notify the team).

- **ACM certificate transparency logging controls (2024-2025):**
  Added support for disabling certificate transparency logging for
  private certificates, with monitoring for compliance.

- **Cross-account certificate sharing via RAM (2025-2026):** ACM
  certificates can now be shared across accounts via AWS RAM, with
  monitoring for shared certificate usage and renewal status in both
  the owning and consuming accounts.

## NEVER do these things

1. **NEVER assume ACM auto-renews all certificates.** Auto-renewal
   requires DNS validation, ISSUED status, service attachment, no CAA
   conflicts, and valid DNS validation records. Unattached or email-
   validated certs do NOT auto-renew.

2. **NEVER rely on a single alarm threshold.** Use tiered alarms:
   warning at 30 days and critical at 7 days. A single threshold
   either fires too early (noise) or too late (no time to fix).

3. **NEVER skip CAA record checks when renewal fails.** CAA records
   are the #1 silent renewal blocker. Always query CAA records for the
   domain when investigating renewal failures.

4. **NEVER set DaysToExpiry alarm with `treat-missing-data` as
   `notBreaching`.** If the metric stops reporting (cert deleted/
   re-created), the alarm should fire (breaching), not silently pass.

5. **NEVER forget multi-region inventory.** ACM is regional. A cert
   in us-west-2 is invisible when monitoring only us-east-1. Always
   check all active regions.

6. **NEVER assume wildcard certs cover all subdomain levels.**
   `*.example.com` covers only first-level subdomains.
   `a.b.example.com` is NOT covered by `*.example.com`.

7. **NEVER ignore unattached certificates.** Certificates not
   attached to a supported service are NOT auto-renewed. Either
   re-attach or delete them.

8. **NEVER monitor only the certificate expiry without monitoring the
   PCA CA certificate.** If the PCA CA cert expires, all private certs
   issued by it become invalid, even if they have not expired.

9. **NEVER delete DNS validation CNAME records after issuance.** The
   validation records MUST remain in DNS for renewal. Deleting them
   causes renewal failure.

10. **NEVER use email validation for production certificates.** Email
    validation requires manual action for every renewal, introducing
    human-dependent risk. Use DNS validation for all production certs.

## Output format

```text
ACM_MONITORING: <account-id> (<regions>) — <cert-count> certificates
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
FINDINGS:
  [<severity>] <finding-description>
CHECKLIST:
  [✓|✗] Certificate inventory: <count> certs across <regions> regions
  [✓|✗] DaysToExpiry alarms: warning (<30d) and critical (<7d) configured for <count> certs
  [✓|✗] SNS notification: warning → <sns-arn>, critical → <sns-arn>
  [✓|✗] Renewal status: <count> ELIGIBLE, <count> INELIGIBLE, <count> FAILED
  [✓|✗] DNS validation: <count> verified, <count> missing records
  [✓|✗] CAA records: <count> OK, <count> conflicts detected
  [✓|✗] Service attachment: <count> attached, <count> unattached (at risk)
  [✓|✗] Wildcard/SAN coverage: audited
  [✓|✗] PCA private certs: <count> monitored, <count> PCA CAs tracked
  [✓|✗] Multi-account audit: <count> accounts scanned (if applicable)
VERIFICATION_COMMANDS:
  aws acm list-certificates --certificate-statuses ISSUED --region <region>
  aws cloudwatch describe-alarms --alarm-name-prefix acm-cert- --region <region>
  aws acm describe-certificate --certificate-arn <cert-arn> --region <region>
  dig <domain> CAA +short
```

### Worked example — standard certificate expiry monitoring

```text
ACM_MONITORING: 123456789012 (us-east-1) — 5 certificates
VERDICT: OPERATION_COMPLETED
FINDINGS:
  [info] All 5 certificates have DaysToExpiry alarms configured (warning + critical)
  [info] All 5 certificates are DNS-validated and attached to supported services
  [info] No CAA conflicts detected
  [info] No renewal failures detected
CHECKLIST:
  [✓] Certificate inventory: 5 certs across us-east-1
  [✓] DaysToExpiry alarms: warning (<30d) and critical (<7d) configured for 5 certs
  [✓] SNS notification: warning → arn:aws:sns:us-east-1:123456789012:cert-warning-notifications, critical → arn:aws:sns:us-east-1:123456789012:cert-critical-escalation
  [✓] Renewal status: 3 ELIGIBLE, 2 INELIGIBLE (not yet in renewal window), 0 FAILED
  [✓] DNS validation: 5 verified, 0 missing records
  [✓] CAA records: 5 OK (amazon.com authorized or no CAA), 0 conflicts
  [✓] Service attachment: 5 attached (3 ALB, 1 CloudFront, 1 API Gateway), 0 unattached
  [✓] Wildcard/SAN coverage: audited (2 wildcard, 3 SAN)
  [✓] PCA private certs: 0 (no private CA in use)
  [✓] Multi-account audit: not applicable (single-account)
VERIFICATION_COMMANDS:
  aws acm list-certificates --certificate-statuses ISSUED --region us-east-1
  aws cloudwatch describe-alarms --alarm-name-prefix acm-cert- --region us-east-1
  aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 --region us-east-1
  dig example.com CAA +short
```

## Error handling

### DaysToExpiry metric reporting -1
- The certificate is not eligible for DaysToExpiry monitoring. Check
  certificate status (must be ISSUED). Imported certificates may not
  report DaysToExpiry correctly.

### Renewal status shows FAILED
- Check (in order): CAA records, DNS validation records, service
  attachment, domain ownership. The most common cause is a CAA record
  conflict, followed by missing DNS validation records.

### Certificate status is PENDING_VALIDATION for an extended period
- DNS validation CNAME may be missing or incorrect. Verify the CNAME
  record matches exactly what ACM specifies. Check for trailing dots
  in the DNS record name.

### Alarm stays in INSUFFICIENT_DATA
- The metric is not reporting. The certificate may be in a non-ISSUED
  state, or the alarm dimensions may not match the certificate ARN
  exactly. Verify with `describe-alarms` and `get-metric-statistics`.

### Multi-account audit fails for a member account
- The monitoring role may not exist in the member account, or the
  audit account does not have permission to assume it. Verify the
  trust policy on the member account's monitoring role.

## Domain

AWS CloudOps / ACM Certificate Monitoring, Expiry Tracking & Renewal
Operations.

## AWS documentation

- **ACM User Guide** — https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html
- **ACM managed renewal** — https://docs.aws.amazon.com/acm/latest/userguide/managed-renewal.html
- **ACM DNS validation** — https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html
- **ACM CAA records** — https://docs.aws.amazon.com/acm/latest/userguide/caa.html
- **CloudWatch DaysToExpiry metric** — https://docs.aws.amazon.com/acm/latest/userguide/cloudwatch-metrics.html
- **ACM PCA User Guide** — https://docs.aws.amazon.com/acm-pca/latest/userguide/PcaWelcome.html
- **ACM multi-account monitoring** — https://docs.aws.amazon.com/acm/latest/userguide/acm-best-practices.html
- **ACM pricing** — https://aws.amazon.com/certificate-manager/pricing/
