# Trust Relationships and LDAPS — Directory Service Deployer

Deep reference on trust relationships (forest trust vs external
trust, one-way vs two-way direction semantics, DNS prerequisites)
and LDAPS (secure LDAP with certificate authority lifecycle, AWS
PCA integration, expiry monitoring). Loaded on demand by the
skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Trust relationship fundamentals

### Trust type: Forest vs External

| Trust type | Scope | Use case | Direction options |
|---|---|---|---|
| Forest trust | Between two entire AD forests (all domains) | Enterprise-wide trust between AWS Managed AD and on-prem forest | One-Way or Two-Way |
| External trust | Between two specific domains | Limited trust between individual domains only | One-Way or Two-Way |

Forest trusts are broader — they allow authentication across all
domains in both forests. External trusts are narrower — they only
apply to the specific domains involved.

### Trust direction semantics

The direction is from the perspective of the LOCAL directory being
configured:

```text
One-Way: Incoming
  Local domain TRUSTS the remote domain
  → Remote domain users CAN access local domain resources
  → Local domain users CANNOT access remote domain resources
  Use when: you want external users to access YOUR resources

One-Way: Outgoing
  Local domain IS TRUSTED BY the remote domain
  → Local domain users CAN access remote domain resources
  → Remote domain users CANNOT access local domain resources
  Use when: you want YOUR users to access external resources

Two-Way
  Bidirectional trust
  → Both domains' users CAN access both domains' resources
  Use when: mutual resource access is needed
```

**Direction CANNOT be changed after creation.** To change direction,
you must delete the trust and recreate it with the new direction.

### DNS prerequisites for trust

Trust relationships require DNS resolution between the two domains.
Conditional forwarders must be configured on BOTH sides:

```bash
# Side A: forward from AWS Managed AD to on-prem domain
aws ds create-conditional-forwarder \
  --directory-id d-aaa111222 \
  --remote-domain-name onprem.example.com \
  --dns-ip-addrs 10.0.1.53 10.0.2.53 \
  --region us-east-1

# Side B: forward from on-prem AD to AWS Managed AD
# (done on the on-prem DNS server, pointing to AWS Managed AD IPs)
# AWS Managed AD DNS IPs are available via:
aws ds describe-directories \
  --directory-ids d-aaa111222 \
  --query 'DirectoryDescriptions[0].DnsIpAddrs' \
  --region us-east-1 --output text
```

Without bidirectional DNS resolution, the trust creates but
authentication requests fail because the domain controllers cannot
find each other.

### Creating and verifying a trust

```bash
# Create the trust
aws ds create-trust \
  --directory-id d-aaa111222 \
  --remote-domain-name onprem.example.com \
  --trust-direction Two-Way \
  --trust-type Forest \
  --trust-password 'SecureTrustP@ss!' \
  --region us-east-1

# Check trust status
aws ds describe-trusts \
  --directory-id d-aaa111222 \
  --region us-east-1 --output table

# Trust states: Creating → Verified | Failed → Deleting → Deleted
# Only "Verified" means the trust is functioning correctly
```

### Common trust pitfalls

1. **DNS not resolving between domains.** The trust creates but
   stays in "Creating" or transitions to "Failed" because domain
   controllers cannot resolve each other's names.

2. **Wrong trust direction.** A one-way incoming trust when the user
   wanted outgoing (or vice versa). Direction CANNOT be changed —
   must delete and recreate.

3. **Network connectivity blocked.** The two directories cannot
   reach each other over required AD ports (53, 88, 389, 445, 3268,
   49152-65535). Verify security groups and network routing.

4. **Trust password mismatch.** Both sides must use the same trust
   password. If the passwords do not match, the trust fails
   verification.

## LDAPS (Secure LDAP) fundamentals

### Certificate requirements

LDAPS requires a server authentication certificate that:
- Is issued by a trusted Certificate Authority
- Has a Subject Alternative Name (SAN) or Subject matching the
  directory's FQDN
- Is valid (not expired)
- Uses RSA or ECDSA key type
- Has a minimum 2048-bit key for RSA

### Using AWS Private Certificate Authority (PCA)

```bash
# Step 1: Create a PCA (if not already existing)
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256WITHRSA,Subject={CommonName=corp-CA} \
  --certificate-authority-type SUBORDINATE \
  --region us-east-1

# Step 2: Issue a certificate for the directory's FQDN
aws acm-pca issue-certificate \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxx \
  --csr file://directory-csr.pem \
  --signing-algorithm SHA256WITHRSA \
  --validity Value=395,Type=DAYS \
  --region us-east-1

# Step 3: Get the issued certificate
aws acm-pca get-certificate \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxx \
  --certificate-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/xxx/certificate/xxx \
  --region us-east-1
```

### Registering and enabling LDAPS

```bash
# Register the certificate with the directory
aws ds register-certificate \
  --directory-id d-aaa111222 \
  --certificate-data file://certificate.pem \
  --region us-east-1

# Enable LDAPS for client LDAP queries
aws ds enable-ldaps \
  --directory-id d-aaa111222 \
  --type Client \
  --region us-east-1

# Optionally enable LDAPS for domain controller replication
aws ds enable-ldaps \
  --directory-id d-aaa111222 \
  --type DomainController \
  --region us-east-1
```

### Monitoring certificate expiry

```bash
# List registered certificates
aws ds list-certificates \
  --directory-id d-aaa111222 \
  --region us-east-1

# Check ACM certificate details
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --query 'Certificate.{Domain:DomainName,Expiry:NotAfter,Status:Status,DaysLeft:RenewalSummary}' \
  --region us-east-1
```

**CloudWatch alarm for certificate expiry:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "LDAPS-Cert-Expiry-d-aaa111222" \
  --metric-name DaysToExpiry \
  --namespace AWS/CertificateManager \
  --statistic Minimum \
  --period 86400 \
  --threshold 30 \
  --comparison-operator LessThanThreshold \
  --dimensions Name=CertificateArn,Value=arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cert-expiry-alerts \
  --region us-east-1
```

### Common LDAPS pitfalls

1. **Certificate expiry.** The #1 cause of LDAPS breakage. When the
   certificate expires, clients get TLS handshake errors but the
   directory appears healthy in the console. Set up CloudWatch
   alarms.

2. **Untrusted CA.** If the issuing CA is not in the client's
   trusted root certificate store, TLS validation fails even if the
   certificate is valid.

3. **Wrong certificate SAN.** The certificate's SAN or Subject must
   match the directory's FQDN. A mismatch causes TLS hostname
   verification failure.

4. **LDAPS on Simple AD or AD Connector.** These types do NOT
   support LDAPS. Only Managed Microsoft AD supports LDAPS.

## Terraform examples

```hcl
# Managed Microsoft AD with trust
resource "aws_directory_service_directory" "managed_ad" {
  name     = "corp.example.com"
  short_name = "corp"
  password = var.ad_password
  edition  = "Enterprise"
  type     = "MicrosoftAD"

  vpc_settings {
    vpc_id     = aws_vpc.main.id
    subnet_ids = [aws_subnet.az1.id, aws_subnet.az2.id]
  }

  tags = {
    Environment = "production"
  }
}

# Conditional forwarder
resource "aws_directory_service_conditional_forwarder" "onprem" {
  directory_id       = aws_directory_service_directory.managed_ad.id
  remote_domain_name = "onprem.example.com"
  dns_ips           = ["10.0.1.53", "10.0.2.53"]
}

# Trust relationship (requires the forwarder to be in place first)
resource "aws_directory_service_trust" "onprem_trust" {
  directory_id       = aws_directory_service_directory.managed_ad.id
  remote_domain_name = "onprem.example.com"
  trust_direction    = "Two-Way"
  trust_type         = "Forest"
  trust_password     = var.trust_password

  depends_on = [aws_directory_service_conditional_forwarder.onprem]
}
```

---

## Expert heuristic: trust direction (one-way vs two-way) (moved from SKILL.md)

Trust direction determines which domain's users can access which
domain's resources. Getting the direction wrong is a silent failure.

```text
One-Way Incoming (local trusts remote):
  Remote users → CAN access → Local resources
  Local users  → CANNOT access → Remote resources

One-Way Outgoing (local is trusted by remote):
  Local users  → CAN access → Remote resources
  Remote users → CANNOT access → Local resources

Two-Way (bidirectional):
  Both domains' users → CAN access → Both domains' resources

Trust scope:
  External trust — between two domains in DIFFERENT forests
  Forest trust   — between two entire forests (all domains)
```

**Key implication:** "Incoming" and "Outgoing" are from the
perspective of the local directory. Incoming = external users access
YOUR resources. Outgoing = YOUR users access external resources.
Direction CANNOT be changed after creation.

---

## Expert heuristic: LDAPS certificate authority lifecycle (moved from SKILL.md)

LDAPS requires a certificate from a trusted CA with a full lifecycle.

```text
1. Obtain cert from trusted CA:
   ├── AWS Private CA (PCA) — issue cert for directory FQDN
   └── External CA — generate CSR, get signed, import

2. Register cert with directory:
   aws ds register-certificate --directory-id d-xxx --certificate-data file://cert.pem

3. Enable LDAPS:
   aws ds enable-ldaps --directory-id d-xxx --type Client

4. Monitor expiry:
   ├── PCA-issued certs get automatic ACM renewal
   ├── External CA certs must be manually renewed
   └── Set CloudWatch alarm on DaysToExpiry

5. On expiry (if not renewed):
   LDAPS silently breaks → TLS errors → authentication failures
```

**Key implication:** LDAPS is not "set and forget." Plan the CA
lifecycle from day one. Use AWS PCA for auto-renewal.

---

## Step 5 — Trust creation and verification commands (moved from SKILL.md)

```bash
# Create a two-way forest trust
aws ds create-trust \
  --directory-id d-aaa111222 \
  --remote-domain-name corp.example.com \
  --trust-direction Two-Way \
  --trust-type Forest \
  --trust-password 'TrustP@ssw0rd!' \
  --region us-east-1

# Verify trust status
aws ds describe-trusts \
  --directory-id d-aaa111222 \
  --region us-east-1
# Expected: TrustState: Verified
```

---

## Step 6 — LDAPS enablement and monitoring commands (moved from SKILL.md)

```bash
# Step 1: Register certificate with the directory
aws ds register-certificate \
  --directory-id d-aaa111222 \
  --certificate-data file://certificate.pem \
  --region us-east-1

# Step 2: Enable LDAPS for client connections
aws ds enable-ldaps \
  --directory-id d-aaa111222 \
  --type Client \
  --region us-east-1

# Step 3: Monitor certificate expiry
aws ds list-certificates \
  --directory-id d-aaa111222 \
  --region us-east-1

aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/xxx \
  --query 'Certificate.{Domain:DomainName,Expiry:NotAfter,Status:Status}' \
  --region us-east-1
```
