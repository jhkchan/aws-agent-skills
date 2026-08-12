# ACM Renewal Paths Reference

Supplementary reference for the Certificate Renewal Automator skill.
Use when selecting a renewal path, designing a custom renewal Lambda,
or debugging a renewal failure.

## Renewal path classification

Every ACM certificate falls into exactly one renewal path. The path is
determined by two factors: validation method (DNS / email / imported)
and attachment status (attached to a supported service / orphaned).

## Path 1: ACM managed renewal (DNS-validated, attached)

**Conditions:**
- `DomainValidationOptions[].ValidationMethod = DNS`
- `InUseBy` is non-empty (cert is attached to ALB, NLB, CloudFront, or API Gateway)
- `RenewalEligibility = ELIGIBLE`

**Behavior:** ACM attempts renewal starting 60 days before expiry,
repeating daily. The renewed cert replaces the old one in place (ARN
does not change). No operator action required.

**Verification commands:**

```bash
# Check renewal eligibility
aws acm describe-certificate \
  --certificate-arn <arn> \
  --query 'Certificate.RenewalEligibility'

# Check managed renewal status
aws acm describe-certificate \
  --certificate-arn <arn> \
  --query 'Certificate.RenewalStatus'
```

**RenewalEligibility values:**

| Value | Meaning | Action |
|---|---|---|
| `ELIGIBLE` | ACM will attempt managed renewal | None — verify daily |
| `INELIGIBLE` | ACM will NOT renew | Investigate: CNAME deleted? SAN mismatch? Not attached? |

**RenewalStatus values (when ELIGIBLE):**

| Value | Meaning |
|---|---|
| `PENDING_AUTO_RENEWAL` | ACM is attempting renewal |
| `SUCCESS` | Renewal completed successfully |
| `FAILED` | Renewal attempt failed — check DNS CNAMEs |

## Path 2: Custom renewal pipeline (DNS-validated, orphaned)

**Conditions:**
- `DomainValidationOptions[].ValidationMethod = DNS`
- `InUseBy = []` (cert not attached to any resource)

**Behavior:** ACM does NOT renew orphaned certs. The custom pipeline
must: (1) request a new cert, (2) add DNS validation CNAME, (3) wait
for issuance, (4) attach to target resource, (5) delete old cert.

**Key CLI calls:**

```bash
# Request new cert
aws acm request-certificate \
  --domain-name www.example.com \
  --validation-method DNS \
  --idempotency-token renewal-$(date +%s)

# Get validation CNAME
aws acm describe-certificate \
  --certificate-arn <new-arn> \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord'

# Wait for issuance
aws acm wait certificate-validated --certificate-arn <new-arn>
```

## Path 3: Semi-manual (email-validated, attached)

**Conditions:**
- `DomainValidationOptions[].ValidationMethod = EMAIL`
- `InUseBy` is non-empty

**Behavior:** ACM sends renewal emails 45 days before expiry to the
registered domain contacts. Renewal requires clicking the approval
link in the email. ACM retries email delivery over 15 days.

**Migration to DNS validation (recommended):**

```bash
# Request new DNS-validated cert for the same domain
aws acm request-certificate \
  --domain-name www.example.com \
  --validation-method DNS

# After new cert is issued, update the listener/distribution
aws elbv2 modify-listener --listener-arn <arn> \
  --certificates CertificateArn=<new-dns-arn>

# Delete old email-validated cert after verification
aws acm delete-certificate --certificate-arn <old-email-arn>
```

## Path 4: Manual re-import (imported private key)

**Conditions:**
- Certificate was imported via `acm import-certificate` (has a private key)
- `RenewalEligibility = INELIGIBLE` (always for imported certs)

**Behavior:** ACM does NOT renew imported certs. The renewal flow:
(1) renew at external CA, (2) export new cert + key + chain,
(3) re-import via `import-certificate` (same ARN if not deleted).

**CLI flow:**

```bash
# Re-import renewed cert (creates new ARN)
aws acm import-certificate \
  --certificate fileb://new-cert.pem \
  --private-key fileb://new-key.pem \
  --certificate-chain fileb://new-chain.pem

# Or re-import to SAME ARN (must not be expired yet)
aws acm import-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111111111111:certificate/existing-arn \
  --certificate fileb://new-cert.pem \
  --private-key fileb://new-key.pem \
  --certificate-chain fileb://new-chain.pem
```

## Path 5: PCA pipeline (PCA-issued, DNS-validated, attached)

**Conditions:**
- Certificate was requested via `acm request-certificate` with `CertificateAuthorityArn`
- PCA CA is `ACTIVE`
- Cert is attached to a supported service

**Behavior:** ACM CAN managed-renew PCA-issued certs if the CA is
active and the cert is attached. However, end-cert validity periods
are typically shorter (1 year vs 13 months for public), requiring more
frequent renewals.

**PCA CA lifecycle:**

```bash
# Check CA validity
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn <ca-arn> \
  --query 'CertificateAuthority.{Status:Status,NotAfter:NotAfter,Type:Type}'

# Renew CA (for subordinate CAs)
aws acm-pca update-certificate-authority \
  --certificate-authority-arn <ca-arn> \
  --revocation-configuration CrlConfiguration={Enabled=false}
```

| CA type | Max validity | Renewal action |
|---|---|---|
| ROOT | 25 years | Rarely needs renewal; create new root and chain |
| SUBORDINATE | 10 years | Renew via root CA signing before expiry |

## Service-specific cert requirements

| Service | Region requirement | SNI support | Cert scope |
|---|---|---|---|
| ALB | Same region as load balancer | Yes (multiple certs per listener) | Per-listener |
| NLB | Same region as load balancer | Limited | Per-listener |
| CloudFront | **us-east-1 only** | Yes | Per-distribution |
| API Gateway REST (edge) | **us-east-1 only** | Yes | Per-custom-domain |
| API Gateway REST (regional) | Same region as API | Yes | Per-custom-domain |
| API Gateway HTTP (v2) | Same region as API | Yes | Per-custom-domain |

## DaysToExpiry metric reference

- **Namespace:** `AWS/CertificateManager`
- **Metric:** `DaysToExpiry`
- **Dimension:** `CertificateArn` (optional — omit for fleet-wide minimum)
- **Period:** Minimum 86400 seconds (1 day) — metric updates once daily
- **Applies to:** ISSUED certificates only (not PENDING_VALIDATION or EXPIRED)

## Common renewal failure signatures

| Symptom | Root cause | Diagnostic |
|---|---|---|
| RenewalEligibility: INELIGIBLE | DNS CNAME missing or cert not attached | Check `InUseBy` and Route 53 records |
| RenewalStatus: FAILED | DNS validation could not complete | Verify CNAME via `dig` or `nslookup` |
| Cert expired despite managed renewal | Cert was orphaned at renewal time | `InUseBy` was empty during 60-day window |
| SAN cert renewal blocked | One SAN domain validation CNAME missing | Check CNAME for each SAN domain individually |
| PCA cert renewal failed | CA is not ACTIVE or CA CRL/OCSP misconfigured | Verify CA status and CRL configuration |
