---
name: acm-certificate-expiry-auditor
description: >-
  Audits AWS Certificate Manager (ACM) certificates for expiry risk, renewal
  health, validation method, and key-algorithm strength. Emits a deterministic
  verdict (EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | ERROR | OK) per
  certificate with risk level and specific remediation. Use when reviewing
  ACM certificate expiry, diagnosing FAILED_AUTORENEWAL root causes (CAA_ERROR,
  DOMAIN_VALIDATION_DENIED, NO_AVAILABLE_CONTACTS, PCA_* errors), checking
  CloudFront certificate region placement, validating imported-certificate
  re-import windows, or auditing TLS posture before production deployment.
version: 0.2.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline certificate-doc classification.
  Live-account audits use aws acm describe-certificate and
  aws acm list-certificates (AWS CLI v2, SSO or key-based credentials).
keywords:
  - ACM
  - certificate expiry
  - TLS certificate
  - FAILED_AUTORENEWAL
  - CAA_ERROR
  - renewal failure
  - NotAfter
  - AMAZON_ISSUED
  - IMPORTED
  - DNS validation
  - CloudFront certificate
  - us-east-1
  - RSA_1024
  - EC_prime256v1
  - 397-day certificate
  - certificate transparency
  - private certificate authority
  - wildcard certificate
  - certificate audit
tags: [acm, security, certificate, tls, expiry, renewal, pki, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Security
  verdict_shape: "EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | ERROR | OK"
  when_to_use: >-
    Reviewing an ACM certificate before production deployment, diagnosing a
    FAILED_AUTORENEWAL event, checking whether an imported certificate is
    inside the 60-day re-import window, validating CloudFront certificate
    region placement, or auditing account-wide TLS certificate posture.
  activation_triggers:
    - "audit this ACM certificate"
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
  invocation_schema: >-
    Input: either (a) an ACM certificate configuration document (Type, Status,
    NotAfter, RenewalEligibility, RenewalSummary, KeyAlgorithm,
    DomainValidationOptions, InUseBy), OR (b) a certificate ARN for live-account
    audit. Output: deterministic CERTIFICATE/VERDICT/RISK/REASON/REMEDIATION
    block per certificate, where VERDICT is in {EXPIRED, EXPIRING_SOON,
    RENEWAL_FAILED, ERROR, OK}, followed by EXACTLY ONE POSTURE SUMMARY.
---

# ACM Certificate Expiry Auditor

## Quick start

- **Verdicts:** EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | ERROR | OK. Decided by the ordered decision tree below; first matching step wins.
- **Renewal start:** ACM-managed renewal (AMAZON_ISSUED) begins **60 days** before `NotAfter`. IMPORTED certificates have no auto-renewal — the operator must re-import.
- **Hard stop:** **30 days** before `NotAfter`, any non-renewed certificate is RISK: HIGH or worse. Inside this window a missed renewal is an incident, not a watch-item.
- **One POSTURE SUMMARY per audit:** emit per-certificate blocks first, then EXACTLY ONE aggregated `POSTURE SUMMARY` at the very end (never one summary per cert).

### Risk mapping — the ONLY valid verdict × risk pairs

| Verdict | Condition | RISK |
|---|---|---|
| EXPIRED | always | **CRITICAL** |
| RENEWAL_FAILED | days_until_expiry ≤ 30 | **CRITICAL** |
| RENEWAL_FAILED | days_until_expiry > 30 | **HIGH** |
| EXPIRING_SOON | Type == AMAZON_ISSUED (any days ≤ 60) | **HIGH** |
| EXPIRING_SOON | Type == IMPORTED + days ≤ 30 | **HIGH** |
| EXPIRING_SOON | Type == IMPORTED + **30 < days ≤ 60** | **MODERATE** |
| OK | always | **LOW** |
| ERROR | always | **N/A** |

**Common misread (D8 defect):** EXPIRING_SOON + IMPORTED + days > 30 is **MODERATE — NOT HIGH**. The re-import window is open but not yet urgent; conflating IMPORTED re-import lead-time with AMAZON_ISSUED managed-renewal urgency over-escalates the wrong cert and steals attention from the CRITICAL queue.

## Mindset

**One-line takeaway:** an ACM certificate is a **time-bombed dependency**. Every certificate has a hard expiry; the only question is whether the renewal mechanism (ACM-managed for AMAZON_ISSUED, manual re-import for IMPORTED) will complete before `NotAfter`. The audit asks, in order: has it already expired, has renewal failed, is it close enough to expiry to be at risk, or is it healthy?

Three domain truths drive every verdict:

- **AMAZON_ISSUED is a managed renewal contract.** ACM commits to renewing it automatically (starting 60 days out). If renewal has not completed inside that 60-day window, the contract is at risk — the cert is EXPIRING_SOON and the risk is HIGH because the mechanism that should have succeeded has not.
- **IMPORTED is a manual renewal contract.** ACM will NOT renew it. The 60-day window is the operator's re-import deadline. Inside 30 days, re-import is urgent.
- **CloudFront pins certificates to us-east-1.** A cert referenced by a CloudFront distribution in any other region is a misconfiguration that breaks TLS at the edge — flag it independently of the expiry verdict.

## Decision tree (apply in order — first match wins)

### Step 0: Input validation → ERROR

Emit `VERDICT: ERROR, RISK: N/A` when the input cannot be classified. ERROR conditions:

- **Malformed input** — `NotAfter` is missing, unparseable, or not an ISO-8601 timestamp.
- **PENDING_VALIDATION** — `Status: PENDING_VALIDATION` means the certificate has been requested but not yet issued; there is no `NotAfter` to audit.
- **Unsupported key algorithm** — `KeyAlgorithm` is not one of `RSA_2048`, `RSA_4096`, `EC_prime256v1`, `EC_secp384r1`, `EC_secp521r1`. (RSA_1024 IS classifiable — it is deprecated, not unsupported; see Remediation.)

ERROR output format:

```text
CERTIFICATE: <domain-name> (<certificate-arn>)
VERDICT: ERROR
RISK: N/A
REASON: <malformed input | PENDING_VALIDATION | unsupported KeyAlgorithm <algo>> — cannot classify.
REMEDIATION: <re-fetch with `aws acm describe-certificate --certificate-arn <arn>` | wait for issuance | re-request with a supported KeyAlgorithm.>
```

### Step 1: Terminal expiry → EXPIRED

If `Status: EXPIRED`, OR `NotAfter` is in the past (`days_until_expiry <= 0`):

- VERDICT: **EXPIRED**, RISK: **CRITICAL**.
- The certificate is no longer valid for TLS handshake. Any HTTPS endpoint terminating on this cert is failing or about to fail. This is a live outage, not a future risk.

### Step 2: Renewal failure → RENEWAL_FAILED

If `RenewalSummary.Status: FAILED_AUTORENEWAL` (AMAZON_ISSUED only — IMPORTED has no auto-renewal):

- VERDICT: **RENEWAL_FAILED**. ACM attempted renewal and it failed; without intervention the cert WILL expire.
- RISK: **CRITICAL** if `days_until_expiry <= 30`; **HIGH** if `days_until_expiry > 30`.
- Diagnose the root cause from `RenewalSummary.RenewalStatusReason` (see Reference table). Common: `CAA_ERROR` (missing/ambiguous CAA record), `DOMAIN_VALIDATION_DENIED` (validation CNAME deleted/overridden), `NO_AVAILABLE_CONTACTS` (email validation with no reachable contacts), `PCA_*` errors (private CA deleted, revoked, or permissions changed).

### Step 3: Expiring soon → EXPIRING_SOON

If `days_until_expiry <= 60` (and the cert is not EXPIRED or RENEWAL_FAILED):

- VERDICT: **EXPIRING_SOON**.
- RISK mapping (authoritative — see Quick start table):
  - **Type == AMAZON_ISSUED → RISK: HIGH.** This rule is mandatory. ACM should have renewed by now (renewal starts at 60 days). A non-renewed AMAZON_ISSUED cert inside the window means the managed-renewal contract is at risk. NEVER downgrade EXPIRING_SOON + AMAZON_ISSUED below HIGH.
  - **Type == IMPORTED + `days_until_expiry <= 30` → RISK: HIGH.** Re-import is overdue; the hard-stop has arrived.
  - **Type == IMPORTED + `30 < days_until_expiry <= 60` → RISK: MODERATE — NOT HIGH.** The re-import window is open but not yet urgent; the hard-stop is still weeks away. Do NOT conflate this with AMAZON_ISSUED urgency (managed renewal has failed there; here the operator simply has not yet acted). If you find yourself writing HIGH for an IMPORTED cert with > 30 days to expiry, STOP — re-check the table.

### Step 4: Healthy → OK

If none of the above matched (cert is issued, not expired, > 60 days to expiry, no renewal failure):

- VERDICT: **OK**, RISK: **LOW**.
- Still emit advisories for deprecated key algorithms (RSA_1024), CloudFront region mismatches, or missing CT logging — these do NOT change the verdict but appear in REMEDIATION as advisory notes.

### Aggregation note (multi-cert audit)

When auditing multiple certificates, emit one block per cert, then **EXACTLY ONE POSTURE SUMMARY** at the end (never per cert). The summary's `overall_risk` is the **worst** individual risk: CRITICAL > HIGH > MODERATE > LOW > N/A.

## Output format

### Per-certificate block

```text
CERTIFICATE: <domain-name> (<certificate-arn>)
VERDICT: EXPIRED | EXPIRING_SOON | RENEWAL_FAILED | ERROR | OK
RISK: CRITICAL | HIGH | MODERATE | LOW | N/A
REASON: NotAfter <date>, days_until_expiry=<N>, Type <AMAZON_ISSUED|IMPORTED>, Status <status>, RenewalEligibility <eligibility>, KeyAlgorithm <algo>. <1-2 sentence explanation referencing the decision-tree step.>
REMEDIATION: <specific action per verdict, or "None required." for OK. Advisory notes for deprecated algos / CloudFront region go here.>
```

### POSTURE SUMMARY (exactly one, at the very end of the audit)

```text
POSTURE SUMMARY
  certificates_audited: <N>
  expired: <count>
  renewal_failed: <count>
  expiring_soon: <count>
  ok: <count>
  error: <count>
  overall_risk: <worst individual RISK>
  next_action: <the single highest-priority remediation across all certs>
```

### Worked example — EXPIRING_SOON on AMAZON_ISSUED

```text
CERTIFICATE: api.example.com (arn:aws:acm:us-east-1:111111111111:certificate/abc-123)
VERDICT: EXPIRING_SOON
RISK: HIGH
REASON: NotAfter 2026-08-17, days_until_expiry=15, Type AMAZON_ISSUED, Status ISSUED,
RenewalEligibility ELIGIBLE, RenewalSummary.Status PENDING_AUTORENEWAL, KeyAlgorithm
RSA_2048. Inside the 60-day managed-renewal window and not yet renewed — ACM should
have completed renewal by now (Step 3: EXPIRING_SOON + AMAZON_ISSUED => HIGH).
REMEDIATION: 1. Diagnose the stalled renewal — check the validation CNAME is still
resolvable and no CAA record blocks ACM issuers. 2. If the CNAME is gone, re-add it;
ACM retries renewal automatically (up to 11 attempts before NotAfter). 3. Monitor
EventBridge for AWS Certificate Manager Renewal events. If renewal does not complete
within 7 days, re-request the certificate with DNS validation as a fallback.
```

### Worked example — EXPIRING_SOON on IMPORTED, 45 days (MODERATE — NOT HIGH)

```text
CERTIFICATE: portal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/imp-45d)
VERDICT: EXPIRING_SOON
RISK: MODERATE
REASON: NotAfter 2026-09-18, days_until_expiry=45, Type IMPORTED, Status ISSUED,
RenewalEligibility INELIGIBLE, KeyAlgorithm RSA_2048. Inside the 60-day re-import
window but outside the 30-day hard stop — operator-led re-import is open but not
urgent (Step 3: EXPIRING_SOON + IMPORTED + 30 < days <= 60 => MODERATE). NOT HIGH.
REMEDIATION: 1. Schedule re-import to the SAME ARN within the next 2 weeks, before
the 30-day hard stop. 2. Source the renewed cert+key+chain from the external CA;
diff the SAN list vs the existing cert to avoid silent TLS breaks. 3. In-place
re-import preserves the ARN: `aws acm import-certificate --certificate-arn <arn>
--certificate file://new.pem --private-key file://new.key --certificate-chain
file://chain.pem`. 4. Treat this as planning work, not an incident.
```

## Anti-Patterns — NEVER

- NEVER report a certificate as `OK` when `days_until_expiry <= 60` and it has not been renewed. Inside the 60-day window, an unrenewed cert is EXPIRING_SOON at minimum. The 60-day threshold is the renewal START, not a safe distance from expiry.

- NEVER downgrade an `EXPIRING_SOON + AMAZON_ISSUED` certificate below RISK: HIGH. The managed-renewal contract is failing — ACM started renewal 60 days out and it has not completed. "There is still time" is the wrong framing; the mechanism that should have renewed is at risk.

- NEVER assume the DNS validation CNAME persists after a hosted-zone migration, registrar transfer, or Route 53 record-set import. ACM writes the CNAME once at issuance; it does NOT re-create it. A zone migration that drops the validation record silently breaks future renewals. Always verify the CNAME is resolvable when diagnosing FAILED_AUTORENEWAL.

- NEVER skip client-side revocation checks. An unexpired, renewed certificate can still be revoked (CA compromise, key compromise, subscriber-requested revocation). This audit verdict is about expiry/renewal only — it does NOT certify revocation status. For production TLS posture, the caller MUST additionally check OCSP stapling or CRL availability at the serving endpoint. Flagging expiry without noting revocation is incomplete posture reporting.

- NEVER recommend deleting an EXPIRED certificate that is still `InUseBy` a load balancer, CloudFront distribution, or API Gateway custom domain. ACM will refuse deletion (`ResourceInUseException`); the correct fix is to request/re-import a replacement, swap the listener/distribution reference, THEN delete the expired cert.

- NEVER assume a wildcard certificate (`*.example.com`) covers subdomains deeper than one level. `*.example.com` covers `api.example.com` but NOT `v1.api.example.com`. A multi-level subdomain silently falls back to an untrusted or self-signed cert if the wildcard is the only one deployed.

- NEVER assume a certificate is region-portable. ACM certificates are regional resources — a cert issued in `us-east-1` cannot be referenced by an ALB in `ap-southeast-1`. Cross-region requires re-requesting in each consuming region.

- NEVER flag a certificate as failed just because `RenewalEligibility: INELIGIBLE`. INELIGIBLE on an IMPORTED cert is normal (imports do not auto-renew). INELIGIBLE on an AMAZON_ISSUED cert younger than ~11 months is also normal (ACM requires the cert to age before eligibility). Only `RenewalSummary.Status: FAILED_AUTORENEWAL` is a renewal failure.

- NEVER treat `PENDING_VALIDATION` as a healthy state. A cert that has never been issued has no expiry to audit — emit ERROR and direct the operator to complete validation. PENDING_VALIDATION is not OK and not EXPIRING_SOON.

- NEVER rely solely on `Status: ISSUED` to declare health. `ISSUED` means the cert was issued at some point; it says nothing about expiry or renewal. Always compute `days_until_expiry` from `NotAfter` and cross-check `RenewalSummary`.

- NEVER recommend re-importing an IMPORTED certificate without preserving the ARN. `aws acm import-certificate` to the SAME ARN (via `--certificate-arn`) is an in-place renewal — listeners and distributions keep working. Importing as a NEW cert requires swapping every reference and risks a missed-update outage.

- NEVER ignore CloudFront region placement. A certificate referenced by a CloudFront distribution MUST be in `us-east-1`. A cert in any other region causes CloudFront TLS failures. Flag this in REMEDIATION even when the expiry verdict is OK.

- NEVER treat an ACM certificate as region-portable for ANY consumer, not just CloudFront. ACM certs are pinned to the region of issue — a cert in `us-east-1` cannot be referenced by an ALB/NLB/API Gateway custom domain in `ap-southeast-1`. Multi-region TLS requires requesting the cert in EACH consuming region. Auditing one region's ACM and declaring "all TLS healthy" misses every other region's certs entirely.

- NEVER assume an IMPORTED public certificate has valid Certificate Transparency (CT) coverage just because it was accepted by `import-certificate`. ACM does NOT add SCTs (Signed Certificate Timestamps) to imported certs — it stores what you gave it. Chrome and other CT-enforcing clients require 1-3 embedded SCTs (count depends on validity period: 3 for <180 days, 2 for 181-359 days, 1 for 360+ days). An IMPORTED cert without the right SCT count is silently distrusted by browsers while `Status: ISSUED` reports success. Always verify embedded SCTs on the source cert BEFORE importing.

- NEVER share a single ACM certificate across AWS accounts. Unlike IAM roles or KMS key policies, ACM certificates CANNOT be shared cross-account — each account must request its own cert for the same domain. For shared domains across many accounts, use AWS Private Certificate Authority (PCA) so each account issues its own private cert from the shared CA.

## Remediation

### For EXPIRED (RISK: CRITICAL)

1. The certificate is dead — HTTPS endpoints are failing. Treat as a live incident.
2. If `InUseBy` is non-empty, identify every consumer (ALB, NLB, CloudFront, API Gateway) and route them to a replacement cert immediately.
3. Request a new certificate: `aws acm request-certificate --domain-name <domain> --validation-method DNS --region <region>`. Prefer DNS validation — it is automatable and survives email-contact changes.
4. Once the new cert is ISSUED, update each consumer's listener/distribution to reference the new ARN, verify TLS, THEN delete the expired cert (`aws acm delete-certificate --certificate-arn <expired-arn>`). ACM refuses deletion while `InUseBy` is non-empty.

### For RENEWAL_FAILED (RISK: CRITICAL or HIGH)

Diagnose from `RenewalSummary.RenewalStatusReason` (see Reference for the full mapping):

- **CAA_ERROR:** the domain's CAA record does not authorize ACM's issuer (`amazon.com`, `amazontrust.com`, `awstrust.com`, `sectigo.com`). Fix: add or correct the CAA record `example.com. CAA 0 issue "amazon.com"`. Wait for DNS propagation (TTL-dependent) — ACM retries renewal on the next attempt.
- **DOMAIN_VALIDATION_DENIED:** the DNS validation CNAME written at issuance has been deleted, overridden, or the hosted zone has changed. Fix: re-add the exact CNAME from `describe-certificate --certificate-arn <arn>` -> `DomainValidationOptions[].ResourceRecord`. Verify with `dig <name> CNAME`.
- **NO_AVAILABLE_CONTACTS:** email-validation cert where the registered contacts are unreachable. Fix: migrate to DNS validation (re-request with `--validation-method DNS`) — email validation is operationally fragile.
- **PCA_* errors:** private certificate authority issue — the PCA was deleted, revoked, or its permissions changed. Fix: verify the PCA exists and the cert's `CertificateAuthorityArn` is valid; re-issue from a healthy PCA.

If renewal does not complete within 7 days of the fix, re-request the certificate with DNS validation as a fallback (the old cert remains valid until `NotAfter`).

### For EXPIRING_SOON (RISK: HIGH or MODERATE)

- **AMAZON_ISSUED (HIGH):** renewal should have completed. Diagnose the stall — check the validation CNAME, CAA records, and EventBridge renewal events. If the stall persists, re-request with DNS validation. Do NOT wait past the 30-day hard stop.
- **IMPORTED, <= 30 days (HIGH):** re-import NOW. Use in-place re-import to preserve the ARN: `aws acm import-certificate --certificate-arn <arn> --certificate file://new.pem --private-key file://new.key --certificate-chain file://chain.pem`. Verify the chain includes all intermediates.
- **IMPORTED, 30-60 days (MODERATE):** schedule re-import within the next 2 weeks. Source the new cert from your external CA/IaC pipeline before the 30-day hard stop.

### For OK (RISK: LOW)

1. No urgent action. Confirm `RenewalEligibility: ELIGIBLE` (AMAZON_ISSUED) or that the re-import pipeline is wired (IMPORTED).
2. Advisory — deprecated key algorithm: if `KeyAlgorithm: RSA_1024`, plan migration to RSA_2048 or EC_prime256v1. RSA_1024 is deprecated by all modern browsers and will be distrusted. Re-request with a stronger algorithm before the next renewal cycle.
3. Advisory — CloudFront region: if the cert is `InUseBy` a CloudFront distribution and NOT in `us-east-1`, flag for immediate re-request in `us-east-1`.

### Pre-flight safety (before any destructive CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation (re-import, re-request, delete), emit: `CONFIRM: About to <action> on certificate <arn> in <region>. This affects <consequence>. Proceed? (yes/no)`. Do NOT execute until confirmed.
- Before deleting, confirm `InUseBy` is empty: `aws acm describe-certificate --certificate-arn <arn>` -> `InUseBy[]`.
- Before re-importing, verify the replacement cert+key+chain match the domain names on the existing cert (SAN mismatch breaks TLS silently).
- Prefer DNS validation over email validation for all new requests — email validation depends on reachable contacts and breaks under org/contact changes.

## Monitoring

Continuous certificate health requires monitoring, not point-in-time audits:

- **EventBridge rule** for `AWS Certificate Manager Renewal` events (status `SUCCESS`, `FAILED`, `PENDING`). Route `FAILED` to an alarm or ticket within minutes — renewal failures are the leading cause of expiry outages.
- **CloudWatch alarm** on the `DaysToExpiry` metric (ACM emits this per cert). Threshold: `< 30` days -> CRITICAL page; `< 60` days -> HIGH ticket. This catches both stalled AMAZON_ISSUED renewals and forgotten IMPORTED certs.
- **AWS Config rule** `acm-certificate-expiration-check` — evaluate managed-rule compliance at least daily; non-compliant = `< 14` days (configurable). Pair with automatic remediation (SSM) for AMAZON_ISSUED certs.
- **External CA pipeline monitoring (IMPORTED certs).** IMPORTED certs have no ACM renewal — the re-import pipeline MUST emit its own alarm when the source cert is within 60 days of expiry. A silent external-CA pipeline is the top cause of IMPORTED-cert outages.

## Reference — ACM certificate internals

### Non-obvious operational gotchas (senior-engineer knowledge)

These are NOT in the AWS ACM docs; they are operational surprises learned from production incidents. Audit against them explicitly:

- **`InUseBy[]` has a propagation lag.** ACM's resource scanner runs on a best-effort schedule (minutes to low hours). A cert just attached to an ALB can still show `InUseBy: []`. Conversely, a just-detached cert may show stale consumers for a while. When triaging deletion safety, do NOT rely on a single snapshot — re-fetch after ~5 minutes before acting on an empty list.
- **CAA is re-checked on every renewal attempt, not just at issuance.** Adding a CAA record that locks the domain to a different CA (e.g., `issue "letsencrypt.org"`) AFTER the cert was issued by ACM will silently break the next renewal — you only learn weeks later via `FAILED_AUTORENEWAL` + `CAA_ERROR`. Always re-audit CAA when changing DNS providers or registrars, not just at issuance time.
- **The 11 renewal retries are front-loaded.** ACM schedules most retry attempts in the first ~30 days of the 60-day window; attempts become sparse near `NotAfter`. A renewal stall discovered at day 35+ has far fewer natural recovery attempts left than the "11 retries" headline implies. Treat day-30-plus stalls as urgent regardless of `days_until_expiry`.
- **Renewal is all-or-nothing across SANs.** A cert with 5 SANs where 1 fails DNS validation will NOT be renewed, even though the other 4 validate cleanly. The renewal status reflects the worst SAN. When diagnosing a stall, audit EVERY SAN's `DomainValidationOptions[].ValidationStatus`, not just the primary domain.
- **`RenewalEligibility: INELIGIBLE` on a fresh AMAZON_ISSUED cert is NORMAL.** ACM requires the cert to age (~11 months) before it becomes ELIGIBLE. Newly-issued certs are INELIGIBLE — this is not a defect and does not block renewal when the cert enters its renewal window.
- **IMPORTED certs carry externally-generated keys; the FIPS/HSM guarantees do NOT apply.** Only AMAZON_ISSUED keys are generated in FIPS 140-2 Level 3 HSMs and are non-exportable. An IMPORTED cert's key is whatever you imported — if the source was a shared PEM on a CI runner, that key is already a blast-radius risk regardless of ACM storage.
- **Account quota is 2,500 certs per region (soft limit).** Large enterprises with centralized security accounts routinely hit this. A failed `request-certificate` with `LimitExceededException` is a quota hit, not a service outage — request a limit increase via Support or the Service Quotas console before re-trying.
- **`Status: ISSUED` is a one-shot historical flag, not a health signal.** A cert that was issued 11 months ago and is now 5 days from expiry still shows `ISSUED`. Health is `days_until_expiry` + `RenewalSummary`, never `Status` alone. Treat any "looks fine — `Status: ISSUED`" reasoning as a bug.
- **ACM events on EventBridge use specific status enums.** `AWS Certificate Manager Renewal` events emit `AWSAccountCertificateRenewal` detail-type with `RenewalStatus` of `SUCCESS`, `FAILED`, or `PENDING`. A common bug is to alarm only on `FAILED` — you also miss the silent "no event at all" failure mode (renewal never scheduled). Alarm on the absence of a `SUCCESS` event within the 60-day window, not just on `FAILED`.

### Renewal timeline (AMAZON_ISSUED)

ACM-managed renewal begins **60 days** before `NotAfter` and retries up to **11 times** before expiry. The 60-day start and the retry schedule mean an AMAZON_ISSUED cert inside the 60-day window with `RenewalSummary.Status: PENDING_AUTORENEWAL` is NORMAL early in the window but escalates to HIGH-risk as it approaches the 30-day hard stop without completing. The verdict (EXPIRING_SOON) is the same throughout the window; the risk escalation is encoded in the EXPIRING_SOON + AMAZON_ISSUED => HIGH rule.

### Public certificate constraints (CA/B Forum Baseline Requirements)

- **397-day maximum validity.** Public TLS certificates (AMAZON_ISSUED) are capped at 397 days by the CA/B Forum Baseline Requirements. ACM enforces this — requesting a longer validity is rejected. Plan certificate lifecycles around annual renewal.
- **Mandatory Certificate Transparency (CT) logging.** All public certs issued after April 2018 are logged to at least 2 CT logs. ACM handles CT submission automatically for AMAZON_ISSUED certs. IMPORTED public certs MUST already have embedded SCTs (Signed Certificate Timestamps) — an import without SCTs will be distrusted by Chrome and other CT-enforcing clients.
- **FIPS 140-2 Level 3, non-exportable private keys.** For AMAZON_ISSUED certs, ACM generates and stores the private key in FIPS 140-2 Level 3 validated HSMs. The private key is NEVER exportable. This is why AMAZON_ISSUED certs cannot be recovered if deleted — the key material is gone. IMPORTED certs hold externally-generated keys and the operator controls exportability.

### Renewal status reason mapping

| `RenewalStatusReason` | Meaning | Fix |
|---|---|---|
| `CAA_ERROR` | CAA record blocks or is ambiguous about ACM's issuer | Add `issue "amazon.com"` CAA record |
| `DOMAIN_VALIDATION_DENIED` | DNS validation CNAME deleted/overridden | Re-add the exact CNAME from `DomainValidationOptions` |
| `NO_AVAILABLE_CONTACTS` | Email-validation contacts unreachable | Migrate to DNS validation (re-request) |
| `PCA_RESOURCE_NOT_FOUND` | Private CA deleted | Re-issue from a healthy PCA |
| `PCA_INVALID_STATE` | Private CA disabled/deleted | Restore or recreate the PCA |
| `PCA_INVALID_ARGS` | Certificate/template mismatch | Correct the cert template / PCA config |
| `OTHER` | Unspecified — check CloudTrail `RenewCertificate` events | Open an AWS Support case if root cause is not evident |

### CloudFront + ACM region rule

CloudFront distributions can ONLY reference certificates in `us-east-1`. A cert in `eu-west-1` referenced by a CloudFront distribution will cause TLS failures at all edge locations. This is a hard constraint of the CloudFront-ACM integration, not a soft preference. When auditing, check every cert's `InUseBy[]` for CloudFront distribution ARNs and verify the cert's region is `us-east-1`. Flag mismatches in REMEDIATION independently of the expiry verdict.

### IMPORTED certificate re-import

IMPORTED certs do not auto-renew. The operator must re-import a new cert+key+chain to the SAME ARN before `NotAfter` to preserve listener/distribution references:

```bash
aws acm import-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --certificate file://new-cert.pem \
  --private-key file://new.key \
  --certificate-chain file://intermediate.pem
```

The re-import replaces the cert+key in place; the ARN, all references, and tags remain unchanged. A re-import with a SAN mismatch (different domain names) silently breaks TLS for the dropped domains — always diff the SAN list before re-importing.

### Wildcard scope

A wildcard certificate (`*.example.com`) covers exactly one DNS label: `api.example.com` is covered; `v1.api.example.com` is NOT. Multi-level wildcards (`*.*.example.com`) are not supported by any public CA. When auditing, cross-check the requested domain names against the actual subdomains the workload serves.

## Domain

AWS CloudOps / ACM TLS Certificate Lifecycle & Compliance.

## Recent AWS features (2024-2026)

- **ECDSA P-256 public certs (2024):** ACM issues ECDSA P-256 via Amazon Trust Services — smaller keys, faster TLS handshakes than RSA. Note the `KeyAlgorithm` field when auditing.
- Core audit surface (managed renewal, DNS/Email validation, PCA integration) is otherwise unchanged — no new fields or settings alter the decision tree above.

## AWS documentation

- **AWS Certificate Manager User Guide** — https://docs.aws.amazon.com/acm/latest/userguide/acm-overview.html
- **ACM Security** — https://docs.aws.amazon.com/acm/latest/userguide/security.html
- **ACM API Reference** — https://docs.aws.amazon.com/acm/latest/APIReference/
- **ACM CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/acm/
- **Managed renewal for ACM certificates** — https://docs.aws.amazon.com/acm/latest/userguide/acm-renewal.html
