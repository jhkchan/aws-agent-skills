# End-to-End Example: ACM Private CA Deployment

A walkthrough showing how to use the `acm-private-ca-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a root CA with CRL revocation, then a subordinate
CA signed by the root, with ACM integration for managed private
certificate lifecycle. The deployment needs:

- Root CA: RSA_2048, SHA256withRSA, CN=Example Root CA
- CRL: S3 bucket acm-pca-crl-123456789012-us-east-1, expiration 7 days
- Subordinate CA: RSA_2048, signed by root, SubordinateCACertificate_PathLen0
- ACM integration: create-permission for acm.amazonaws.com
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-acm-private-ca
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a private root CA with CRL and a subordinate CA
      signed by the root. Enable ACM integration."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a private certificate authority"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACM_PCA: arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc (ROOT, RSA_2048, SHA256withRSA)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] CA type: ROOT
  [✓] Key algorithm: RSA_2048
  [✓] Signing algorithm: SHA256withRSA
  [✓] Subject DN: CN=Example Root CA, O=Example Org, C=US
  [✓] Revocation: CRL (bucket acm-pca-crl-123456789012-us-east-1, expiration 7 days)
  [✓] CRL S3 bucket: acm-pca-crl-123456789012-us-east-1 — exists
  [✓] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject
  [✓] CA status: ACTIVE
  [✓] CA certificate: self-signed (RootCACertificate/V1 template, validity 10 years)
  [✓] Certificate template: RootCACertificate/V1
  [✓] Tags: Environment=production, Purpose=trust-anchor
VERIFICATION_COMMANDS:
  aws acm-pca describe-certificate-authority --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws acm-pca list-permissions --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws s3api get-bucket-policy --bucket acm-pca-crl-123456789012-us-east-1
```

---

## Step 3 — Provisioning commands

### 3a. Create CRL S3 bucket and policy

```bash
# Create bucket
aws s3api create-bucket \
  --bucket acm-pca-crl-123456789012-us-east-1 \
  --region us-east-1

# Apply bucket policy
aws s3api put-bucket-policy \
  --bucket acm-pca-crl-123456789012-us-east-1 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "Service": "acm-pca.amazonaws.com" },
        "Action": ["s3:PutObject", "s3:PutObjectAcl", "s3:GetBucketAcl", "s3:GetBucketLocation"],
        "Resource": [
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1",
          "arn:aws:s3:::acm-pca-crl-123456789012-us-east-1/*"
        ]
      }
    ]
  }'
```

### 3b. Create and activate the root CA

```bash
# Create root CA
ROOT_CA_ARN=$(aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Root CA,O=Example Org,C=US}" \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-123456789012-us-east-1,ExpirationInDays=7,CustomCname=crl.example.com}" \
  --certificate-authority-type ROOT \
  --region us-east-1 \
  --query 'CertificateAuthorityArn' --output text)

# Get CSR and self-sign
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > root-ca.csr

ROOT_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://root-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/RootCACertificate/V1 \
  --validity Value=10,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

aws acm-pca wait certificate-issued \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1

aws acm-pca get-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate-arn "$ROOT_CERT_ARN" --region us-east-1 | \
  jq -r '.Certificate' > root-ca-cert.pem

aws acm-pca import-certificate-authority-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --certificate fileb://root-ca-cert.pem \
  --region us-east-1
```

### 3c. Create and activate the subordinate CA

```bash
# Grant permission on parent CA
aws acm-pca create-permission \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --principal 123456789012 \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1

# Create subordinate CA
SUB_CA_ARN=$(aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Subordinate CA,O=Example Org,C=US}" \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-123456789012-us-east-1,ExpirationInDays=7},OcspConfiguration={Enabled=true}" \
  --certificate-authority-type SUBORDINATE \
  --region us-east-1 \
  --query 'CertificateAuthorityArn' --output text)

# Get CSR and sign with parent
aws acm-pca get-certificate-authority-csr \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --region us-east-1 --query 'Csr' --output text > sub-ca.csr

SUB_CERT_ARN=$(aws acm-pca issue-certificate \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --csr fileb://sub-ca.csr \
  --signing-algorithm SHA256withRSA \
  --template-arn arn:aws:acm-pca:::template/SubordinateCACertificate_PathLen0/V1 \
  --validity Value=5,Type=YEARS \
  --region us-east-1 --query 'CertificateArn' --output text)

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
  --certificate-chain fileb://sub-ca-chain.pem \
  --region us-east-1
```

### 3d. Grant ACM integration permission

```bash
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal acm.amazonaws.com \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Root CA status — should be ACTIVE
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --query 'CertificateAuthority.{Status:Status,Type:Type}' --region us-east-1

# Subordinate CA status — should be ACTIVE
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --query 'CertificateAuthority.{Status:Status,Type:Type}' --region us-east-1

# Verify ACM permission on subordinate CA
aws acm-pca list-permissions \
  --certificate-authority-arn "$SUB_CA_ARN" --region us-east-1

# Verify CRL bucket policy
aws s3api get-bucket-policy --bucket acm-pca-crl-123456789012-us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| CRL bucket policy | Not configured | Explicit bucket policy granting acm-pca.amazonaws.com | Without policy, CRL publication silently fails |
| Root CA activation | Assumes CA is ready after creation | Self-signed cert issuance + import | CA starts in PENDING_CERTIFICATE; must be activated |
| Subordinate permission | Skips parent permission | create-permission on parent CA | Parent must grant permission before signing subordinate |
| ACM integration | Not configured | create-permission for acm.amazonaws.com | Without it, ACM cannot request/renew private certs |
| Template selection | Uses default or wrong template | Correct template per cert type | Wrong template = wrong X.509 extensions |
| CA deletion | Assumes instant | Documents 7-30 day waiting period | Mandatory period; permanent after expiry |

---

## Related artifacts

- **Skill definition:** `skills/acm-private-ca-deployer/SKILL.md`
- **CA hierarchy and signing guide:** `skills/acm-private-ca-deployer/references/ca-hierarchy-and-signing.md`
- **CRL and revocation guide:** `skills/acm-private-ca-deployer/references/crl-and-revocation.md`
- **Slash command:** `commands/aws/deploy-acm-private-ca.md`
- **Eval suite:** `skills/acm-private-ca-deployer/evals/evals.json`
- **Legacy test cases:** `skills/acm-private-ca-deployer/eval/test-cases.yaml`
