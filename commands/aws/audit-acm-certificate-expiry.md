---
description: Audit an ACM certificate for expiry risk, renewal status, validation method, and key-algorithm strength. Classifies into EXPIRED, EXPIRING_SOON, RENEWAL_FAILED, or OK.
nl_triggers:
  - "audit this ACM certificate"
  - "check certificate expiry"
  - "is my certificate expiring"
  - "why did ACM renewal fail"
  - "certificate renewal failed"
  - "imported certificate expiring"
  - "CAA_ERROR renewal"
  - "DNS validation renewal"
  - "TLS certificate health"
  - "RSA_1024 compliance"
  - "CloudFront certificate region"
  - "FAILED_AUTORENEWAL"
  - "certificate NotAfter"
  - "ACM certificate audit"
routes_to: acm-certificate-expiry-auditor
---

# /aws:audit-acm-certificate-expiry

Activate the `acm-certificate-expiry-auditor` skill and audit one or more ACM
certificate configurations for expiry risk, renewal health, and key-algorithm
compliance.

## What it does

Reads an ACM certificate configuration (Type, Status, NotAfter,
RenewalEligibility, RenewalSummary, KeyAlgorithm, DomainValidationOptions) and
applies the ordered classification logic:

1. Terminal expiry -- Status EXPIRED or NotAfter in the past is CRITICAL.
2. Renewal failure -- RenewalStatus FAILED_AUTORENEWAL with root-cause
   diagnosis (CAA_ERROR, DOMAIN_VALIDATION_DENIED, NO_AVAILABLE_CONTACTS,
   PCA_* errors).
3. Time-to-expiry threshold -- 30 days for AMAZON_ISSUED (ACM manages
   renewal), 60 days for IMPORTED (no auto-renewal safety net).
4. Key algorithm advisory -- RSA_1024 flagged as deprecated regardless of
   verdict.
5. Aggregation -- worst verdict wins (EXPIRED > RENEWAL_FAILED >
   EXPIRING_SOON > OK).

Emits a deterministic VERDICT block per certificate:

```text
CERTIFICATE: <domain-name> (<certificate-arn>)
VERDICT: EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | OK
REASON: NotAfter <date>, days_until_expiry=<N>, Type <type>, RenewalEligibility <eligibility>, KeyAlgorithm <algo>. <explanation.>
RISK: CRITICAL | HIGH | MODERATE | LOW
REMEDIATION: <specific action, or "None required.">
```

## When to invoke

Paste an ACM certificate configuration and ask any of:

- "audit this ACM certificate"
- "is my certificate expiring?"
- "why did ACM renewal fail?"
- "check certificate expiry and renewal"
- "is my imported cert about to expire?"
- "fix CAA_ERROR renewal failure"

A certificate ARN or domain name plus any audit verb ("check this cert",
"audit TLS") also routes here via the orchestrator.

## Inputs

- An ACM certificate configuration: Type (AMAZON_ISSUED or IMPORTED), Status,
  NotAfter, RenewalEligibility, RenewalSummary (RenewalStatus,
  RenewalStatusReason), KeyAlgorithm, DomainValidationOptions. These fields
  drive the classification.
- For live-account audits: a certificate ARN (requires AWS CLI credentials).

## Outputs

- One VERDICT block per certificate.
- Risk level (CRITICAL / HIGH / MODERATE / LOW) based on verdict and days
  remaining.
- Specific remediation per verdict with CLI commands: add CAA records,
  re-create DNS validation CNAME, re-import with preserved ARN, re-request,
  or enable proactive monitoring via EventBridge.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for ACM certificate and TLS compliance).
- `/aws:audit-kms-key-policy` for encryption key policy audits (related
  certificate/key lifecycle domain).
