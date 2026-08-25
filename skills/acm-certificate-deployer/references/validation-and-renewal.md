# Validation and Renewal Guide — ACM Certificate Deployer

Deep reference on ACM DNS validation internals, the CNAME lifecycle,
email validation mechanics, certificate renewal behavior, imported
certificate management, and the interaction between validation method
and renewal eligibility. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## DNS validation internals

ACM generates a unique CNAME record for each domain name on the
certificate. The CNAME proves domain ownership.

### CNAME format

```text
Name:  _<random-token>.example.com.
Type:  CNAME
Value: _<random-token>.acm-validations.aws.
```

Each domain name on the certificate gets its OWN unique CNAME. A
certificate with `example.com` and `*.example.com` gets TWO CNAMEs.

### Detection timeline

| Step | Typical time |
|---|---|
| ACM generates CNAMEs | Immediate (on `request-certificate`) |
| Operator adds CNAME to Route53 | Manual (or via API) |
| Route53 propagation | 30-60 seconds (Route53) / variable (third-party) |
| ACM detects CNAME | 5-30 minutes |
| Certificate status: ISSUED | Within minutes of detection |

### Re-validation

ACM re-validates periodically (opaque schedule) for the certificate's
entire lifetime. This is NOT a one-time check:
- If the CNAME is present: renewal proceeds.
- If the CNAME is absent: renewal fails, certificate eventually
  expires.

### Cross-account DNS validation

When the certificate is in Account A and the Route53 hosted zone is
in Account B:

**Option 1: Manual CNAME creation**
- Account A requests the certificate.
- Account A retrieves the CNAME via `describe-certificate`.
- Operator manually creates the CNAME in Account B's Route53.

**Option 2: Automated cross-account (IAM role assumption)**
- Account A assumes a role in Account B with `route53:ChangeResourceRecordSets`.
- Account A creates the CNAME programmatically.

**Option 3: Terraform cross-account provider**
- Use a Terraform `aws_route53_record` in Account B's provider block.

### Third-party DNS validation

ACM DNS validation works with ANY DNS provider (not just Route53):
- Retrieve the CNAME from `describe-certificate`.
- Add it to the third-party DNS provider's control panel.
- Ensure the record is a CNAME (not a TXT or ALIAS).
- The record must persist for the certificate's lifetime.

## Email validation mechanics (deprecated)

Email validation sends to the following addresses:
- Domain registrant (from WHOIS data)
- admin@domain.com
- administrator@domain.com
- webmaster@domain.com
- hostmaster@domain.com
- postmaster@domain.com

The email contains a validation link that must be clicked. ACM sends
a separate email for EACH domain name on the certificate.

### Why email validation is deprecated

| Issue | Impact |
|---|---|
| Manual click-through | Not automatable; requires human action |
| Renewal also requires click | Every renewal cycle needs manual intervention |
| Spam filters | Validation emails frequently filtered |
| Stale WHOIS | Wrong contact = no validation |
| Multiple domains | Each domain sends separate emails |

### Switching from email to DNS validation

You CANNOT change the validation method after request. To switch:
1. Request a NEW certificate with DNS validation.
2. Update CloudFront/ALB/API Gateway to reference the new ARN.
3. Delete the old email-validated certificate.

## Certificate renewal matrix

| Certificate source | Renewal | Operator action | Monitoring |
|---|---|---|---|
| ACM-issued (DNS) | Automatic (60 days before expiry) | Keep CNAME in DNS | Alert if status != ISSUED |
| ACM-issued (email) | Automatic but requires click | Click renewal email | Alert if status != ISSUED |
| Imported (third-party) | NOT automatic | Renew + re-import | Alert on DaysToExpiry < 30 |
| Private (via Private CA) | Automatic (ACM manages) | Keep PCA active | Alert if PCA CA cert expiring |

### Renewal timeline for ACM-managed certificates

```text
Day -60: ACM begins renewal process
         ├── DNS validation: checks CNAME present
         │   ├── CNAME found → renewed silently
         │   └── CNAME missing → retries, eventually fails
         └── Email validation: sends renewal email
             ├── Link clicked → renewed
             └── Not clicked → retries, eventually fails

Day -45: ACM sends event to EventBridge (renewal started)
Day -30: If still not renewed, ACM sends CloudWatch alarm
Day 0:   Certificate expires (if renewal never succeeded)
```

### CloudWatch monitoring for renewal

```bash
# Create a CloudWatch alarm for certificate expiry
aws cloudwatch put-metric-alarm \
  --alarm-name "ACM-Cert-Expiry-30days" \
  --metric-name DaysToExpiry \
  --namespace AWS/CertificateManager \
  --statistic Minimum \
  --period 86400 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=CertificateArn,Value=<cert-arn> \
  --evaluation-periods 1 \
  --alarm-actions <sns-topic-arn>
```

## Imported certificate lifecycle

Imported certificates have a fundamentally different lifecycle:

```text
External CA issues cert (e.g., DigiCert, Let's Encrypt)
  → Operator obtains PEM cert + key + chain
  → Import to ACM (import-certificate)
  → Certificate is active (same as ACM-issued for CloudFront/ALB)

Near expiry:
  → ACM does NOT auto-renew
  → Operator renews with external CA
  → Operator re-imports (same ARN or new ARN)
  → If not re-imported: certificate expires, TLS breaks
```

### Re-import with same ARN

```bash
aws acm import-certificate \
  --certificate-arn arn:aws:acm:us-east-1:<acct>:certificate/<uuid> \
  --certificate fileb://new-cert.pem \
  --private-key fileb://new-key.pem \
  --certificate-chain fileb://new-chain.pem
```

This updates the existing certificate in place (same ARN, new
validity period). CloudFront/ALB references remain valid.

## Private certificate renewal via AWS Private CA

Private certificates requested via ACM from a Private CA:

- ACM manages renewal automatically (same as public DNS-validated).
- The Private CA must remain `ACTIVE` for renewal to work.
- If the Private CA's own CA certificate expires, all certificates
  issued by it become invalid.

### Monitoring Private CA health

```bash
# Check PCA CA certificate status
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn <ca-arn> \
  --query 'CertificateAuthority.{Status:Status,NotAfter:NotAfter}'
```

## Common pitfalls

1. **Deleting the DNS validation CNAME after issuance.** The CNAME
   must remain for the certificate's lifetime. ACM re-validates.
2. **Requesting CloudFront cert outside us-east-1.** Hard requirement;
   re-request in us-east-1.
3. **Assuming imported certs auto-renew.** They do NOT. Monitor
   `DaysToExpiry`.
4. **Using email validation for production.** Deprecated; not
   automatable; use DNS validation.
5. **Wildcard covering apex or multi-level subdomains.** It does NOT.
   Add explicit SANs.
6. **Forgetting PCA CA cert expiry.** If PCA CA cert expires, all
   private certs become invalid.

## Expert heuristic — DNS validation CNAME lifecycle

ACM DNS validation is NOT a one-time check. ACM re-validates
periodically (and before each renewal). A baseline model says "add
the CNAME and forget"; this heuristic explains the full lifecycle.

```text
request-certificate
  → ACM generates a unique CNAME record per domain name
  → CNAME format: _<random>.example.com → _<random>.acm-validations.aws.

add CNAME to Route53 (or third-party DNS)
  → ACM detects the CNAME (typically 5-30 minutes)
  → certificate status: PENDING_VALIDATION → ISSUED

CNAME must REMAIN in DNS for the certificate's lifetime
  → ACM re-checks periodically (opaque schedule)
  → removing the CNAME blocks renewal
  → certificate enters " renewal eligibility" check before expiry

renewal (60 days before expiry for ACM-managed certs)
  → ACM checks the CNAME is still present
  → if present: auto-renews (no action needed)
  → if absent: renewal fails, certificate expires
```

**Key implication:** the DNS validation CNAME is a permanent
infrastructure dependency. Deleting it (e.g., during DNS cleanup or
migration) silently breaks certificate renewal. Always document the
CNAME as a permanent record.

**Cross-account DNS validation:** when the certificate is in Account
A but the Route53 hosted zone is in Account B, the CNAME must be
created in Account B's Route53. This requires cross-account IAM
permissions (Account A's ACM needs permission to write to Account B's
hosted zone, OR the operator manually creates the CNAME in Account B).

## Expert heuristic — ACM-managed vs imported renewal matrix

The renewal behavior depends on HOW the certificate was issued. A
baseline model conflates the two; this matrix separates them.

| Certificate source | Renewal | Operator action | Monitoring needed |
|---|---|---|---|
| ACM-issued (DNS validation) | **Automatic** (60 days before expiry) | None — keep the CNAME in DNS | Alert if status != ISSUED |
| ACM-issued (email validation) | **Automatic** but requires email click-through | Click the renewal email | Alert if status != ISSUED |
| Imported (third-party CA) | **NOT automatic** — must re-import | Renew with the CA, re-import the PEM | Alert on expiry < 30 days |
| Private (via AWS Private CA) | **Automatic** (ACM manages) if PCA is active | Keep PCA active; ensure PCA CA cert not expired | Alert if PCA CA cert nearing expiry |

**Key implication:** imported certificates are a manual renewal
burden. If your organization imports certificates from an external
CA, you MUST have a renewal process (calendar reminder, automated
monitoring, or a re-import pipeline). ACM will NOT remind you.

## Step 4 — email validation (deprecated, detail)

**Why email validation is problematic:**
- Requires manual click-through for initial validation AND each renewal.
- If the email is not received (spam filter, wrong contact), the
  certificate cannot be issued or renewed.
- Not automatable — no API to "click the link."
- Unreliable for domains with stale WHOIS data.

**If email validation is the only option:** verify WHOIS data is
current, check spam folders, use `aws acm resend-validation-email` to
re-send. **Recommendation:** always use DNS validation. If email
validation was used, re-request the certificate with DNS validation.

## Step 5 — renewal eligibility and monitoring

**Renewal eligibility:**
- The DNS validation CNAME must remain in DNS.
- For imported certificates: NO auto-renewal. Must re-import.

**Monitoring:**
- Alert on `CertificateStatus` != `ISSUED`.
- For imported certificates, alert on `NotAfter` < 30 days from now.
- CloudWatch metric: `AWS/CertificateManager DaysToExpiry`.

## Step 6 — renewal for imported certificates

- ACM does NOT auto-renew imported certificates.
- The operator must renew with the CA and re-import before expiry.
- Use `aws acm import-certificate` with the same ARN to update.
