# Advanced Patterns — ACM Certificate Monitor Operator

Load-on-demand deep dives moved verbatim from SKILL.md: mindset misconceptions, dependency graph, alarm-model heuristic, and recent features.

## Mindset — three operating-time misconceptions

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

## Expert heuristic — the DaysToExpiry tiered alarm model

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

## Recent AWS features (2023-2026)

**Recent AWS features (2023-2026):**

- **ACM multi-region certificates (2023-2024):** Managed across
  multiple regions for global applications using Route53 latency-based
  routing.
- **Enhanced renewal visibility (2023-2024):** API renewal summary now
  includes detailed failure reasons.
- **PCA short-lived certificate support (2023-2024):** Short-lived
  certs (hours to days) requiring more frequent renewal automation.
- **CloudTrail certificate events (2023-2024):** Enhanced events for
  lifecycle changes, renewal attempts, and CAA conflict detection.
- **EventBridge renewal failure events (2024-2025):** ACM emits
  EventBridge events on renewal failure for automated response.
- **Cross-account certificate sharing via RAM (2025-2026):**
  Certificates shared across accounts with monitoring for usage and
  renewal status.
