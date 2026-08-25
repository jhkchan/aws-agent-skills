# CA Hierarchy and Signing — ACM Private CA Deployer

Deep reference on root vs subordinate CA provisioning, certificate
hierarchy design, the self-signed root activation workflow, the
parent-signed subordinate activation workflow, certificate template
selection, and the create-permission model for cross-account and ACM
integration. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Root CA provisioning

### Why root CAs need self-signing

A root CA is the trust anchor. No higher authority signs it. The root
CA's own certificate is self-signed — the CA signs its own certificate
using its own private key. This is the PKI equivalent of a root of
trust.

```text
Root CA activation flow:
  1. create-certificate-authority → CA status: PENDING_CERTIFICATE
  2. get-certificate-authority-csr → get the CA's CSR
  3. issue-certificate (self-signed, template: RootCACertificate/V1)
     → the CA issues a certificate to itself
  4. wait for ISSUED status
  5. get-certificate → get the self-signed certificate
  6. import-certificate-authority-certificate → CA status: ACTIVE
```

### Root CA activation commands

```bash
# 1. Get the CSR
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > root-ca.csr

# 2. Issue self-signed root certificate
ROOT_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://root-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/RootCACertificate/V1 \
  --validity Value=10,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

# 3. Wait for issuance
aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1

# 4. Get and import the certificate
aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > root-ca-cert.pem

aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate fileb://root-ca-cert.pem \
  --region us-east-1
```

### RootCACertificate/V1 template

The `RootCACertificate/V1` template applies the correct X.509
extensions for a root CA certificate:
- `BasicConstraints: CA=true` (no path length constraint — root can
  sign unlimited levels of subordinate CAs)
- `KeyUsage: digitalSignature, certSign, crlSign` (CA key usage)
- `SubjectKeyIdentifier` and `AuthorityKeyIdentifier` are the same
  (self-signed)

## Subordinate CA provisioning

### Why subordinate CAs need parent signing

A subordinate CA is NOT self-signed. It must be signed by its parent
CA. This creates the chain of trust: root CA signs subordinate CA,
subordinate CA signs end-entity certificates. Clients verify the chain
from the end-entity cert up to the trusted root.

### The create-permission requirement

Before the parent CA can sign the subordinate CA's CSR, the parent CA
must have a `create-permission` entry granting the requesting principal
the right to issue certificates. Without this permission, the
`issue-certificate` API call on the parent CA fails with access denied.

```bash
# Grant permission on the parent CA for the requesting account
aws acm-pca create-permission \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --principal 123456789012 \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

**Critical:** this permission is on the PARENT CA, not the subordinate.
A common mistake is to create the permission on the wrong CA.

### Subordinate CA activation commands

```bash
# PREREQUISITE: Parent CA is ACTIVE and has create-permission

# 1. Get the subordinate CA's CSR
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > sub-ca.csr

# 2. Issue certificate from the PARENT CA
SUB_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://sub-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1 \
  --validity Value=5,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

# 3. Wait for the parent to issue
aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1

# 4. Get the certificate and chain from the parent
aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > sub-ca-cert.pem

aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1 | \
  jq -r '.CertificateChain' > sub-ca-chain.pem

# 5. Import into the subordinate CA to activate it
aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate fileb://sub-ca-cert.pem \
  --certificate-chain fileb://sub-ca-chain.pem \
  --region us-east-1
```

### SubordinateCACertificate templates

| Template | Path length | Meaning |
|---|---|---|
| `SubordinateCACertificate_PathLen0/V1` | 0 | Can issue end-entity certs but NOT further subordinate CAs |
| `SubordinateCACertificate_PathLen1/V1` | 1 | Can issue one more level of subordinate CA below it |

**Path length 0** is the most common choice for issuing CAs. It
prevents the subordinate from creating further sub-CAs, limiting the
PKI depth.

### The certificate chain

When importing the subordinate CA certificate, you must provide both
the subordinate certificate AND the certificate chain (the root CA
certificate above it). This allows clients to verify the full chain.

```text
Certificate chain:
  End-entity cert → signed by Subordinate CA
  Subordinate CA cert → signed by Root CA
  Root CA cert → self-signed (trust anchor)
```

## End-entity certificate issuance

### Template selection

| Template | Purpose |
|---|---|
| `EndEntityCertificate/CertPassedPathLen/0` | TLS server certificate (most common) |
| `EndEntityCertificate/V1` | Basic end-entity certificate |
| `CodeSigningCertificate/V1` | Code signing |
| `OCSPSigningCertificate/V1` | OCSP responder |

The `EndEntityCertificate_CertPassedPathLen_0` template asserts that
the issuing CA has a path length of at least 0 (can issue end-entity
but not further sub-CAs). This is the standard TLS server certificate
template.

### Issuing an end-entity certificate

```bash
EE_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --csr fileb://server.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/EndEntityCertificate/CertPassedPathLen/0 \
  --validity Value=365,Type=DAYS \
  --region us-east-1 --query 'CertificateArn' --output text)

aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate-arn "$EE_CERT_ARN" --region us-east-1

aws acm-pca get-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate-arn "$EE_CERT_ARN" --region us-east-1
```

## ACM integration

### Granting ACM service principal permission

To enable ACM to request, issue, and renew private certificates from
the PCA:

```bash
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal acm.amazonaws.com \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

### Cross-account ACM access

To allow ACM in account B to use a PCA in account A:

```bash
# In account A (PCA owner)
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal 999999999999 \
  --source-account 123456789012 \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

Then in account B, ACM can request private certificates by referencing
the PCA ARN from account A.

## CA status lifecycle

```text
CREATING → PENDING_CERTIFICATE → ACTIVE → DISABLED → DELETED → (permanent deletion)
                ↑                    ↑         ↑          ↑
          needs CA cert        can issue   disabled   waiting period
                              certificates             (7-30 days)
```

- **CREATING:** The CA is being provisioned (key generation in HSMs).
- **PENDING_CERTIFICATE:** The CA exists but has no CA certificate.
  Cannot issue certificates.
- **ACTIVE:** The CA has its certificate and can issue end-entity certs.
- **DISABLED:** The CA is manually disabled (cannot issue). Can be
  re-enabled by importing a new certificate.
- **DELETED:** Deletion initiated. 7-30 day waiting period. Can be
  restored. After the period, permanently deleted.

## Terraform examples

```hcl
# Root CA
resource "aws_acmpca_certificate_authority" "root" {
  certificate_authority_configuration {
    key_algorithm     = "RSA_2048"
    signing_algorithm = "SHA256withRSA"
    subject {
      common_name = "Example Root CA"
      organization = "Example Org"
      country      = "US"
    }
  }

  revocation_configuration {
    crl_configuration {
      enabled              = true
      s3_bucket_name       = aws_s3_bucket.crl.id
      expiration_in_days   = 7
      custom_cname         = "crl.example.com"
    }
  }

  type = "ROOT"
  tags = { Environment = "production", Purpose = "trust-anchor" }
}

# CRL S3 bucket with policy
resource "aws_s3_bucket" "crl" {
  bucket = "acm-pca-crl-123456789012-us-east-1"
}

resource "aws_s3_bucket_policy" "crl" {
  bucket = aws_s3_bucket.crl.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "acm-pca.amazonaws.com" }
      Action    = ["s3:PutObject", "s3:PutObjectAcl", "s3:GetBucketAcl", "s3:GetBucketLocation"]
      Resource  = [
        aws_s3_bucket.crl.arn,
        "${aws_s3_bucket.crl.arn}/*"
      ]
    }]
  })
}

# ACM permission on the subordinate CA
resource "aws_acmpca_permission" "acm" {
  certificate_authority_arn = aws_acmpca_certificate_authority.sub.arn
  principal                 = "acm.amazonaws.com"
  actions                   = ["IssueCertificate", "GetCertificate", "ListPermissions"]
}
```

## Common hierarchy pitfalls

1. **Forgetting the parent create-permission.** The parent CA must
   grant `create-permission` before the subordinate CSR can be signed.
   This is on the parent, not the subordinate.

2. **Using the wrong template.** Root uses `RootCACertificate/V1`;
   subordinate uses `SubordinateCACertificate_PathLen0/V1`; end-entity
   uses `EndEntityCertificate_CertPassedPathLen_0`. Wrong template =
   wrong X.509 extensions.

3. **Not importing the certificate chain for subordinate.** The
   subordinate CA import must include the certificate chain (root CA
   cert). Without it, the chain is incomplete.

4. **Issuing directly from the root CA.** Best practice: keep the root
   CA offline (or disabled) and use subordinate CAs for daily issuance.
   This limits root CA key exposure.

5. **Not waiting for certificate issuance.** The `issue-certificate`
   call is asynchronous. You must wait for ISSUED status before
   getting the certificate. Use `wait certificate-issued`.

---

## Create the CA — root and subordinate (moved from SKILL.md Step 4)

**Create a root CA:**

```bash
ROOT_CA_ARN=$(aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Root CA,O=Example Org,C=US}" \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-123456789012-us-east-1,ExpirationInDays=7,CustomCname=crl.example.com}" \
  --certificate-authority-type ROOT \
  --region us-east-1 \
  --query 'CertificateAuthorityArn' --output text)
```

**Create a subordinate CA:**

```bash
SUB_CA_ARN=$(aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Subordinate CA,O=Example Org,C=US}" \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-123456789012-us-east-1,ExpirationInDays=7}" \
  --certificate-authority-type SUBORDINATE \
  --region us-east-1 \
  --query 'CertificateAuthorityArn' --output text)
```

## Activate the root CA (moved from SKILL.md Step 4)

**Activate the root CA (self-signed certificate):**

```bash
# 1. Get CSR
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > root-ca.csr

# 2. Issue self-signed cert using RootCACertificate/V1 template
ROOT_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://root-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/RootCACertificate/V1 \
  --validity Value=10,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

# 3. Wait for issuance, then get cert and import
aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1

aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > root-ca-cert.pem

aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate fileb://root-ca-cert.pem --region us-east-1
```

## Activate the subordinate CA (moved from SKILL.md Step 4)

**Activate the subordinate CA (signed by parent):**

```bash
# PREREQUISITE: Parent CA must be ACTIVE and have create-permission
# 1. Get subordinate CSR
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > sub-ca.csr

# 2. Issue certificate from PARENT CA
SUB_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://sub-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1 \
  --validity Value=5,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

# 3. Wait, get cert + chain, import into subordinate
aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1

aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > sub-ca-cert.pem

aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$SUB_CERT_ARN" --region us-east-1 | \
  jq -r '.CertificateChain' > sub-ca-chain.pem

aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate fileb://sub-ca-cert.pem \
  --certificate-chain fileb://sub-ca-chain.pem --region us-east-1
```

## End-entity issuance command (moved from SKILL.md Step 5)

**Issue an end-entity certificate:**

```bash
EE_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --csr fileb://server.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/EndEntityCertificate/CertPassedPathLen/0 \
  --validity Value=365,Type=DAYS \
  --region us-east-1 --query 'CertificateArn' --output text)
```

## Cross-account ACM permission (moved from SKILL.md Step 6)

**For cross-account ACM access:**

```bash
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal 999999999999 \
  --source-account 123456789012 \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

**Critical:** without this permission, ACM cannot request private
certificates. Certificate requests through ACM will fail with access
denied.
