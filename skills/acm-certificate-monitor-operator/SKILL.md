---
name: acm-certificate-monitor-operator
description: 'Operates AWS ACM certificate monitoring and expiry tracking with production defaults: DaysToExpiry CloudWatch alarm creation (threshold <30 days warning, <7 days critical), multi-region certificate inventory, certificate renewal status tracking (PENDING_VALIDATION, ISSUED, EXPIRED), DNS validation record verification, CAA record conflict detection, multi-account certificate audit via Organizations, certificate-to-load-balancer mapping, automated renewal failure detection, SNS notification on expiry alarm, wildcard vs SAN coverage audit, and private certificate (ACM PCA) monitoring. Emits an OPERATION_COMPLETED report with verification commands. Use when auditing ACM certificate expiry, setting up expiry alarms, verifying renewal, detecting CAA conflicts, or mapping certificates to resources. Triggers acm certificate monitoring, certificate expiry alarm, days to expiry, caa record conflict, multi-account audit, acm pca.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live operations: AWS CLI v2 with acm, acm-pca, cloudwatch, elasticloadbalancingv2, cloudfront, apigateway, and organizations access. Works with Terraform aws_acm_certificate, aws_cloudwatch_metric_alarm, and aws_sns_topic resources and CloudFormation AWS::CertificateManager::Certificate templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, acm, certificate-manager, certificate-expiry, cloudops, operate, monitoring, renewal, caa-record, dns-validation, multi-account
  dependencies: aws-orchestrator
  keywords: aws, acm, certificate, certificate manager, expiry, days to expiry, cloudops, operate, monitoring, renewal, caa record, dns validation, multi-account, wildcard, san, acm pca
  when_to_use: Invoke when the user wants to audit ACM certificate expiry, set up DaysToExpiry CloudWatch alarms, verify certificate renewal status, detect CAA record conflicts, perform multi-account or multi-region certificate inventory, map certificates to load balancers, monitor private certificates via ACM PCA, or verify DNS validation records. Do NOT invoke for issuing/provisioning new certificates (use ACM provisioning skills), IAM server certificates (non-ACM), or third-party CA certificate management.
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
| references/advanced-patterns.md | Dependency graph + alarm model + recent features |
| references/error-handling.md | Monitoring failure remedies |
| references/diagnostic-commands.md | Alarm/inventory CLI detail |

## Mindset

**One-line takeaway:** The `DaysToExpiry` metric is the primary
monitoring signal for ACM certificates. ACM auto-renews certificates
that are DNS-validated and attached to supported AWS services (ALB,
NLB, CloudFront, API Gateway, etc.), but renewal can silently fail if
CAA records conflict, DNS validation records are removed, or the
certificate is not attached to a supported service. Always monitor
DaysToExpiry with tiered alarms (warning <30 days, critical <7 days)
and verify renewal status proactively.

Three misconceptions in full (ACM does NOT auto-renew all certs; the DaysToExpiry alarm IS necessary; CAA records can break renewal at any time): [Advanced patterns](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

ACM certificate monitoring is NOT a single check. The DaysToExpiry
metric is the primary signal, but renewal depends on DNS validation,
CAA records, service attachment, and certificate status. Use this
graph to sequence monitoring checks.

Full check-dependency table (alarm, status, DNS record, CAA, attachment, renewal, region/account coverage, PCA) and cross-dependency gotchas: [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic: the DaysToExpiry tiered alarm model

Tiered-alarm timeline diagram (365→60→30→7→0) and SNS tier routing: [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic: CAA record conflict detection

CAA scenario tree (no CAA / amazon.com / letsencrypt-only / issuewild) and the dig-based detection: [DNS and CAA validation](references/dns-and-caa-validation.md).

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

get-metric-statistics CLI for the metric check: [Diagnostic commands](references/diagnostic-commands.md).

## Step 2 — Certificate expiry alarm tiers

Create tiered CloudWatch alarms on DaysToExpiry for graduated response.

### Warning alarm (< 30 days)

put-metric-alarm CLI (threshold 30, cert-warning-notifications SNS): [Diagnostic commands](references/diagnostic-commands.md).

### Critical alarm (< 7 days)

put-metric-alarm CLI (threshold 7, cert-critical-escalation SNS): [Diagnostic commands](references/diagnostic-commands.md).

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

All-region and specific-region inventory loops plus per-certificate detail query: [Diagnostic commands](references/diagnostic-commands.md).

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

Renewal-status describe-certificate query: [Diagnostic commands](references/diagnostic-commands.md).

**If `RenewalSummary` is present**, ACM has begun the renewal process.
Check `RenewalSummary.RenewalStatus` for `PENDING_AUTO_RENEWAL`,
`SUCCESS`, or `FAILED`.

## Step 5 — DNS validation record verification

DNS-validated certificates have CNAME records that ACM uses to verify
domain ownership. These records MUST remain in DNS for the certificate
to renew.

CNAME retrieval and dig/nslookup verification CLI: [DNS and CAA validation](references/dns-and-caa-validation.md).

**Critical:** if the validation CNAME is missing from DNS, renewal
will fail. The certificate status will show `PENDING_VALIDATION` or
the renewal summary will show `FAILED`.

## Step 6 — CAA record conflict detection

CAA records are the #1 silent blocker of ACM certificate renewal. A
CAA record that does not include `amazon.com` prevents ACM from
renewing the certificate.

CAA query CLI, interpretation table, and the Route53 UPSERT fix: [DNS and CAA validation](references/dns-and-caa-validation.md).

**Key implication:** CAA records can be modified by anyone with DNS
access. A CAA conflict can appear at any time, even for certificates
that were previously renewing fine. Include CAA checks in periodic
certificate health audits.

## Step 7 — Certificate-to-load-balancer mapping

ACM certificates must be attached to supported services for auto-
renewal. The most common attachment is to load balancers (ALB/NLB).

ALB/NLB listener scan, CloudFront/API Gateway ARN queries, and the unattached-cert cross-reference: [Multi-account and PCA](references/multi-account-and-pca.md).

**Critical:** unattached certificates are NOT auto-renewed by ACM.
Either re-attach them or delete them if no longer needed.

## Step 8 — Multi-account audit via Organizations

For organizations with multiple AWS accounts, use Organizations to
audit certificates across all member accounts. Prerequisites:
Organizations all-features enabled, a monitoring role (e.g.
`ACMMonitoringRole`) in each member account with ACM read access,
and the audit account can assume the monitoring role in each member.

Assume-role audit loop across org accounts and regions: [Multi-account and PCA](references/multi-account-and-pca.md).

## Step 9 — Automated renewal failure detection

ACM attempts auto-renewal starting 60 days before expiry. Renewal
failures are not always immediately visible in the console. Detect
them via API by checking `RenewalSummary.RenewalStatus` for all
ISSUED certificates — if `FAILED`, investigate CAA records, DNS
validation records, and service attachment.

RenewalSummary.RenewalStatus scan across ISSUED certificates: [Diagnostic commands](references/diagnostic-commands.md).

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

**Create SNS topics:** use `aws sns create-topic` for
`acm-cert-warning-notifications` and `acm-cert-critical-escalation`,
then `aws sns subscribe` with `--protocol email` to register email
endpoints (e.g., devops-team@example.com for warnings,
oncall@example.com for critical).

**Slack integration:** subscribe a Lambda function
(`sns-to-slack`) to the critical SNS topic to forward alerts to Slack.

## Step 11 — Wildcard vs SAN coverage audit

ACM certificates can cover multiple domains via wildcard (`*.example.com`)
and Subject Alternative Names (SANs). Audit coverage to ensure all
subdomains are protected.

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
considerations: private certs do NOT auto-renew via ACM, must be
renewed manually or via API, and the PCA CA certificate itself
(10-year default validity) must be monitored for expiry — if the CA
cert expires, all private certs issued by it become invalid.

PCA CA listing and NotAfter days-remaining computation: [Multi-account and PCA](references/multi-account-and-pca.md).

## Step 13 — Recent features

2023-2026 features — multi-region certificates, renewal visibility, PCA short-lived certs, CloudTrail events, EventBridge renewal-failure events, RAM sharing: [Advanced patterns](references/advanced-patterns.md).

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

DaysToExpiry -1, renewal FAILED, stuck PENDING_VALIDATION, INSUFFICIENT_DATA alarms, member-account audit failures: [Error handling](references/error-handling.md).

## References (load on demand)

- [DNS and CAA validation](references/dns-and-caa-validation.md) — validation-record persistence, CAA resolution rules and fixes
- [Multi-account and PCA](references/multi-account-and-pca.md) — org audit architecture, PCA monitoring, certificate-to-resource mapping
- [Advanced patterns](references/advanced-patterns.md) — dependency graph, tiered alarm model, recent features
- [Error handling](references/error-handling.md) — metric, renewal, validation, alarm, and audit failure remedies
- [Diagnostic commands](references/diagnostic-commands.md) — alarm, inventory, and renewal-status CLI

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
