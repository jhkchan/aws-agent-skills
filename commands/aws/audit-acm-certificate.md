---
description: Audit an ACM certificate for expiry risk, renewal status, validation method, and key-algorithm strength. Classifies into EXPIRED, EXPIRING_SOON, RENEWAL_FAILED, ERROR, or OK with risk level (CRITICAL/HIGH/MODERATE/LOW/N/A).
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
  - "PENDING_VALIDATION certificate"
routes_to: acm-certificate-expiry-auditor
---

# /aws:audit-acm-certificate-expiry

Activate the `acm-certificate-expiry-auditor` skill and audit one or more ACM
certificate configurations for expiry risk, renewal health, and key-algorithm
compliance.

## What it does

Reads an ACM certificate configuration (Type, Status, NotAfter,
RenewalEligibility, RenewalSummary, KeyAlgorithm, DomainValidationOptions,
InUseBy) and applies the ordered decision tree:

0. ERROR — malformed input / missing NotAfter / PENDING_VALIDATION /
   unsupported key algorithm (RISK: N/A).
1. Terminal expiry — Status EXPIRED or NotAfter in the past => EXPIRED
   (CRITICAL).
2. Renewal failure — RenewalSummary.Status FAILED_AUTORENEWAL with root-cause
   diagnosis (CAA_ERROR, DOMAIN_VALIDATION_DENIED, NO_AVAILABLE_CONTACTS,
   PCA_* errors). CRITICAL if <= 30 days to expiry, else HIGH.
3. Expiring soon — days_until_expiry <= 60. EXPIRING_SOON + AMAZON_ISSUED =>
   RISK: HIGH (mandatory — managed-renewal contract at risk). IMPORTED: HIGH
   if <= 30 days, MODERATE if 30-60 days.
4. Healthy — otherwise OK / LOW.

Emits a deterministic block per certificate, then EXACTLY ONE POSTURE
SUMMARY at the end (never per cert):

```text
CERTIFICATE: <domain-name> (<certificate-arn>)
VERDICT: EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | ERROR | OK
RISK: CRITICAL | HIGH | MODERATE | LOW | N/A
REASON: NotAfter <date>, days_until_expiry=<N>, Type <type>, Status <status>, RenewalEligibility <eligibility>, KeyAlgorithm <algo>. <explanation.>
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
- "why is my cert stuck in PENDING_VALIDATION?"

A certificate ARN or domain name plus any audit verb ("audit this cert",
"check TLS health") also routes here via the orchestrator.

## Inputs

- An ACM certificate configuration: Type (AMAZON_ISSUED or IMPORTED), Status,
  NotAfter, RenewalEligibility, RenewalSummary (RenewalStatus,
  RenewalStatusReason), KeyAlgorithm, DomainValidationOptions, InUseBy. These
  fields drive the classification.
- For live-account audits: a certificate ARN (requires AWS CLI credentials).

## Outputs

- One CERTIFICATE/VERDICT/RISK/REASON/REMEDIATION block per certificate.
- Risk level (CRITICAL / HIGH / MODERATE / LOW / N/A) from the decision tree.
- Specific remediation per verdict: add CAA records, re-create DNS validation
  CNAME, re-import with preserved ARN, re-request with DNS validation, or
  delete only after swapping references.
- EXACTLY ONE POSTURE SUMMARY at the end aggregating counts, overall risk
  (worst individual), and the single highest-priority next action.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for ACM certificate and TLS compliance).
- `/aws:audit-kms-key-policy` for encryption key policy audits (related
  certificate/key lifecycle domain).
