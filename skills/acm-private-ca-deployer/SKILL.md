---
name: acm-private-ca-deployer
description: >-
  Provisions AWS Private Certificate Authority (ACM PCA) with production
  defaults: CA creation (root vs subordinate), key algorithm (RSA_2048,
  EC_prime256v1), signing algorithm (SHA256withRSA, SHA256withECDSA),
  CRL configuration (S3 bucket, expiration, CNAME), certificate template
  selection, CA certificate issuance (self-signed root vs parent-signed
  subordinate), certificate revocation, audit via CloudTrail, CA deletion
  (7-30 day mandatory waiting period), CA permissions for ACM integration,
  and OCSP support. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating a private CA, issuing private certificates,
  configuring CRL revocation, setting up subordinate CA hierarchies,
  integrating ACM PCA with ACM, or deleting a private CA. Triggers: create
  private certificate authority, acm pca root ca, acm pca subordinate ca,
  issue private certificate, crl configuration s3, revoke certificate acm
  pca, ca deletion waiting period, acm pca permissions, acm managed
  private cert.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with acm-pca and acm
  access. Works with Terraform aws_acmpca_certificate_authority /
  aws_acmpca_certificate / aws_acmpca_certificate_authority_certificate
  resources and CloudFormation AWS::ACMPCA::CertificateAuthority /
  AWS::ACMPCA::Certificate templates.
keywords:
  - aws
  - acm
  - acm pca
  - private certificate authority
  - private ca
  - cloudops
  - deploy
  - provisioning
  - root ca
  - subordinate ca
  - certificate
  - crl
  - ocsp
  - revocation
  - pki
tags:
  - aws
  - acm-pca
  - private-ca
  - cloudops
  - deploy
  - security
  - provisioning
  - pki
  - certificates
  - crl
  - revocation
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - acm-pca
    - private-ca
    - cloudops
    - deploy
    - security
    - provisioning
    - pki
    - certificates
    - crl
    - revocation
  dependencies:
    - aws-orchestrator
  keywords:
    - create private certificate authority
    - acm pca root ca
    - acm pca subordinate ca
    - issue private certificate
    - crl configuration s3
    - revoke certificate acm pca
    - ca deletion waiting period
    - acm pca permissions
    - acm managed private cert
  when_to_use: >-
    Invoke when the user wants to create a private certificate authority
    (root or subordinate), issue private certificates, configure CRL
    revocation, set up a subordinate CA hierarchy, integrate ACM PCA
    with ACM for managed certificate lifecycle, delete a private CA,
    or revoke certificates. Do NOT invoke for public TLS certificates
    (use ACM public certificate skills), AWS Certificate Manager public
    issuance, or AWS Secrets Manager certificate storage.
---

# ACM Private CA Deployer

An AWS CloudOps agent skill that provisions AWS Private Certificate
Authority (ACM PCA) with correct defaults. The skill walks the operator
through root vs subordinate CA creation, key and signing algorithm
selection, CRL configuration, certificate issuance, CA permissions for
ACM integration, certificate revocation, and the mandatory CA deletion
waiting period. It captures hierarchy decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create private certificate authority, ACM PCA root CA, ACM PCA
subordinate CA, issue private certificate, CRL configuration S3, revoke
certificate ACM PCA, CA deletion waiting period, ACM PCA permissions,
ACM managed private cert.

## STRICT output contract

When this skill is invoked with an ACM PCA provisioning request (create
a private CA, issue a certificate, configure CRL, set up a subordinate
hierarchy, delete a CA, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `ACM_PCA:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — CA type: root vs subordinate | Core CA model |
| Step 2 — Key and signing algorithm selection | Cryptographic choice |
| Step 3 — CRL configuration (S3 bucket) | Revocation infrastructure |
| Step 4 — Create the CA and issue CA certificate | Provisioning step |
| Step 5 — Certificate templates and end-entity issuance | Certificate issuance |
| Step 6 — CA permissions for ACM integration | Cross-account / ACM managed certs |
| Step 7 — Certificate revocation and OCSP | Revocation lifecycle |
| Step 8 — CA deletion (mandatory waiting period) | Decommissioning |
| Step 9 — Audit via CloudTrail | Compliance |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/ca-hierarchy-and-signing.md | Root/subordinate detail |
| references/crl-and-revocation.md | CRL + revocation detail |

## Mindset

**One-line takeaway:** ACM PCA provides managed private CAs. A root CA
is self-signed; a subordinate CA is signed by its parent CA and MUST
have the parent's permission to issue. CRL revocation requires an S3
bucket with a policy granting the ACM PCA service principal write
access. CA deletion is NOT immediate — it enters a mandatory 7-30 day
waiting period before permanent deletion.

Three misconceptions dominate ACM PCA misdesign at provisioning time:

- **"Creating the CA is enough to issue certificates."** It is not. A
  newly created CA is in `PENDING_CERTIFICATE` status. For a root CA,
  you must issue and import a self-signed certificate. For a
  subordinate CA, you must request a certificate from the parent CA,
  then import it. Until the CA is `ACTIVE`, no certificates can be
  issued from it.

- **"CRL works automatically without an S3 bucket policy."** It does
  not. The CRL distribution point requires an S3 bucket where ACM PCA
  publishes the CRL. The bucket MUST have a policy granting the
  `acm-pca.amazonaws.com` service principal `s3:PutObject` permission.
  Without this policy, CRL publication silently fails and clients
  cannot check revocation status.

- **"CA deletion is instant."** It is NOT. Deleting a CA initiates a
  mandatory waiting period of 7 to 30 days (you choose the duration).
  During this period the CA is in `DELETED` status but can be restored.
  After the period expires, the CA and all its data are permanently
  destroyed. This waiting period exists because certificates issued
  by the CA may still be in use.

## Configuration dependency graph (novel heuristic)

ACM PCA configurations are NOT independent. The CA must be ACTIVE
before issuing certificates. CRL requires an S3 bucket with the correct
policy. Subordinate CAs require parent CA permission. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| CA creation (root) | Key alg, signing alg, subject DN | CA is `CREATING` then `PENDING_CERTIFICATE`; NOT usable until `ACTIVE` | the CA ARN |
| CA creation (subordinate) | Key alg, signing alg, subject DN, parent CA ARN | CA is `PENDING_CERTIFICATE` until parent signs it; parent MUST have `create-permission` | subordinate CA |
| CA certificate (root) | CA created; CSR obtained | Root CA cert is self-signed; must issue then import | `ACTIVE` status |
| CA certificate (subordinate) | Subordinate CA created; CSR obtained; parent CA `ACTIVE` | Parent CA must issue subordinate cert; then import into subordinate | subordinate `ACTIVE` status |
| CRL configuration | S3 bucket exists | Bucket MUST have policy granting `acm-pca.amazonaws.com` `s3:PutObject`; without it CRL publication silently fails | revocation checking |
| End-entity certificate | CA `ACTIVE`; certificate template ARN | Template determines key usage, path length, validity; wrong template = wrong certificate | private TLS certificate |
| ACM integration | CA `ACTIVE`; `create-permission` granting ACM service principal | Without permission, ACM cannot request/renew certs from the CA | managed private cert lifecycle |
| CA deletion | CA exists | 7-30 day mandatory waiting period; restorable until period expires | decommissioning |

**The subordinate-parent-permission row is the one a baseline model
misses.** Creating a subordinate CA is not enough — the parent CA must
have a permission entry (`create-permission`) granting the requesting
principal the right to issue. Without it, the subordinate CA cannot be
signed by the parent and stays in `PENDING_CERTIFICATE` forever.

**Cross-dependency gotchas:**
- A subordinate CA requires the parent CA to be `ACTIVE` AND to have a
  `create-permission` entry. Both conditions must be met.
- CRL publication requires the S3 bucket policy to grant
  `acm-pca.amazonaws.com` write access. Missing the policy is a silent
  failure — the CA appears to work, but CRL is never published.
- ACM integration requires BOTH the CA to be `ACTIVE` AND a
  `create-permission` granting the ACM service principal access.
- CA deletion is reversible during the waiting period via
  `restore-certificate-authority`. After the period, it is permanent.

## Expert heuristic: root vs subordinate CA hierarchy

A baseline model says "create a CA." The correct heuristic recognizes
that the CA type determines the entire provisioning flow.

```text
PKI Hierarchy Decision:
  ├── Need a self-signed trust anchor?
  │     → Create ROOT CA
  │       1. create-certificate-authority --certificate-authority-configuration ...
  │       2. get-certificate-authority-csr → get CSR
  │       3. issue-certificate (self-signed, template: RootCACertificate/V1)
  │       4. get-certificate → get the certificate
  │       5. import-certificate-authority-certificate → activate root CA
  │
  ├── Need a CA signed by an existing parent CA?
  │     → Create SUBORDINATE CA
  │       PREREQUISITE: parent CA must be ACTIVE and have create-permission
  │       1. create-certificate-authority --certificate-authority-configuration ...
  │       2. get-certificate-authority-csr → get subordinate CSR
  │       3. issue-certificate on PARENT CA with subordinate's CSR
  │          (template: SubordinateCACertificate_PathLen0/V1)
  │       4. get-certificate on parent → get the signed subordinate cert
  │       5. import-certificate-authority-certificate on subordinate CA
  │
  └── Need to issue end-entity (TLS) certificates?
        → CA (root or subordinate) must be ACTIVE
        → issue-certificate with template:
          arn:aws:acm-pca:::template/EndEntityCertificate/CertPassedPathLen/0
```

**Key implication:** the root CA requires self-signing (using the
`RootCACertificate/V1` template). The subordinate CA requires parent
signing (using a `SubordinateCACertificate` template). End-entity
certificates use `EndEntityCertificate` templates. Using the wrong
template produces a certificate with the wrong extensions.

## Expert heuristic: CRL S3 bucket policy

CRL revocation is only as good as the S3 bucket that distributes the
CRL. A baseline model configures the CRL but forgets the bucket policy.

```text
CRL requires:
  1. S3 bucket exists (acm-pca-crl-<account>-<region>)
  2. CRL configuration on the CA:
     S3BucketName, ExpirationInDays (default 7), CustomCname (optional)
  3. S3 bucket policy granting acm-pca.amazonaws.com:
     s3:PutObject, s3:PutObjectAcl, s3:GetBucketAcl, s3:GetBucketLocation

  WITHOUT the bucket policy → CRL publication SILENTLY FAILS
  Clients cannot check revocation → revoked certs still trusted
```

## Expert heuristic: CA deletion waiting period

```text
CA Deletion Flow:
  1. delete-certificate-authority --permanent-deletion-time-in-days 7..30
     → CA status: DELETED (disabled; no new certs can be issued)
     → Existing certs remain valid (they carry the CA's signature)
  2. Waiting period (7-30 days):
     → CA can be restored: restore-certificate-authority
  3. After expiration:
     → CA permanently deleted; all data destroyed
     → Existing certs remain valid but CANNOT be revoked
       (the CA no longer exists to publish CRL updates)
```

**Key implication:** always set the waiting period to 30 days unless
there is an urgent security reason. After expiration, revocation of
existing certificates becomes impossible.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Key algorithm chosen | Determines CA key type | Confirm in plan |
| Signing algorithm chosen | Must be compatible with key algorithm | Confirm in plan |
| Subject distinguished name (DN) | Required for CA creation | Confirm subject |
| S3 bucket for CRL (if CRL enabled) | CRL publication requires a writable bucket | `aws s3api head-bucket --bucket <name>` |
| CRL bucket policy grants PCA access | Without it CRL publication silently fails | `aws s3api get-bucket-policy --bucket <name>` |
| Parent CA ACTIVE (for subordinate) | Subordinate CA requires parent signing | `aws acm-pca describe-certificate-authority --certificate-authority-arn <parent-arn>` |
| Parent CA create-permission (for subordinate) | Parent must grant permission to issue | `aws acm-pca list-permissions --certificate-authority-arn <parent-arn>` |
| Certificate template identified | Template determines cert type, key usage, path length | Confirm template ARN |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — CA type: root vs subordinate

| Feature | Root CA | Subordinate CA |
|---|---|---|
| Certificate source | Self-signed | Signed by parent CA |
| Template for CA cert | `RootCACertificate/V1` | `SubordinateCACertificate/PathLen0/V1` |
| Trust anchor | Yes (clients trust directly) | No (clients trust root above it) |
| Requires parent CA | No | Yes (parent ACTIVE + permission) |
| Typical use | Offline root, trust anchor | Intermediate CA for daily cert issuance |

**Best practice:** use a root CA as the offline trust anchor and
subordinate CAs for active certificate issuance. This limits root CA
exposure.

## Step 2 — Key and signing algorithm selection

| Key algorithm | Valid signing algorithms | Notes |
|---|---|---|
| `RSA_2048` | `SHA256withRSA`, `SHA384withRSA`, `SHA512withRSA` | Default for most CAs |
| `RSA_4096` | `SHA256withRSA`, `SHA384withRSA`, `SHA512withRSA` | Root CAs requiring extra margin |
| `EC_prime256v1` | `SHA256withECDSA`, `SHA384withECDSA`, `SHA512withECDSA` | High-throughput subordinate CAs |
| `EC_secp384r1` | `SHA256withECDSA`, `SHA384withECDSA`, `SHA512withECDSA` | Stronger EC |

**Default:** `SHA256withRSA` for RSA keys, `SHA256withECDSA` for EC
keys. These have the broadest client compatibility.

## Step 3 — CRL configuration (S3 bucket)

**Create the CRL S3 bucket:**

```bash
aws s3api create-bucket \
  --bucket acm-pca-crl-123456789012-us-east-1 \
  --region us-east-1
```

**Apply the bucket policy granting ACM PCA write access:**

```bash
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

**Critical:** without this policy, CRL publication silently fails.

## Step 4 — Create the CA and issue CA certificate

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

**Verify CA is ACTIVE:**

```bash
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$ROOT_CA_ARN" \
  --query 'CertificateAuthority.Status' --region us-east-1
# Expected: ACTIVE
```

**Common mistake:** assuming the CA is immediately usable. After
creation, the CA is in `PENDING_CERTIFICATE`. It must receive its CA
certificate to become `ACTIVE`.

## Step 5 — Certificate templates and end-entity issuance

| Template ARN suffix | Purpose | Path length |
|---|---|---|
| `RootCACertificate/V1` | Self-signed root CA certificate | N/A |
| `SubordinateCACertificate_PathLen0/V1` | Subordinate CA (cannot issue further CA certs) | 0 |
| `SubordinateCACertificate_PathLen1/V1` | Subordinate CA (can issue one more level) | 1 |
| `EndEntityCertificate/CertPassedPathLen/0` | End-entity TLS certificate | N/A |
| `EndEntityCertificate/V1` | Basic end-entity certificate | N/A |
| `CodeSigningCertificate/V1` | Code signing certificate | N/A |
| `OCSPSigningCertificate/V1` | OCSP responder signing | N/A |

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

## Step 6 — CA permissions for ACM integration

To let AWS Certificate Manager (ACM) request, issue, and renew private
certificates from a PCA, grant the ACM service principal permission.

```bash
aws acm-pca create-permission \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --principal acm.amazonaws.com \
  --actions IssueCertificate GetCertificate ListPermissions \
  --region us-east-1
```

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

## Step 7 — Certificate revocation and OCSP

**Revoke a certificate:**

```bash
aws acm-pca revoke-certificate \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --certificate-serial 1234567890ABCDEF \
  --revocation-reason "KEY_COMPROMISE" \
  --region us-east-1
```

Revocation reasons: `UNSPECIFIED`, `KEY_COMPROMISE`,
`CERTIFICATE_AUTHORITY_COMPROMISE`, `AFFILIATION_CHANGED`,
`SUPERCEDED`, `CESSATION_OF_OPERATION`, `PRIVILEGE_WITHDRAWN`,
`A_A_COMPROMISE`.

**Enable OCSP on a CA:**

```bash
aws acm-pca update-certificate-authority \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --revocation-configuration \
    "OcspConfiguration={Enabled=true},CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-xxx,ExpirationInDays=7}" \
  --region us-east-1
```

OCSP and CRL can both be enabled simultaneously. OCSP provides real-time
status; CRL provides a cached list. Enable both for maximum client
compatibility.

## Step 8 — CA deletion (mandatory waiting period)

```bash
aws acm-pca delete-certificate-authority \
  --certificate-authority-arn "$SUB_CA_ARN" \
  --permanent-deletion-time-in-days 30 \
  --region us-east-1
```

**Restore during the waiting period:**

```bash
aws acm-pca restore-certificate-authority \
  --certificate-authority-arn "$SUB_CA_ARN" --region us-east-1
```

**Critical:** the waiting period is mandatory (7-30 days). After
expiration, the CA is permanently deleted and CANNOT be recovered.
Existing certificates remain valid but can no longer be revoked.

## Step 9 — Audit via CloudTrail

All ACM PCA API calls are logged to CloudTrail, providing a full audit
trail.

| Event | Security significance |
|---|---|
| `CreateCertificateAuthority` | New CA created |
| `IssueCertificate` | Certificate issued (who, what, template) |
| `ImportCertificateAuthorityCertificate` | CA activated |
| `RevokeCertificate` | Certificate revoked (who, why, serial) |
| `DeleteCertificateAuthority` | CA deletion initiated (waiting period started) |
| `CreatePermission` | Permission granted |
| `DeletePermission` | Permission revoked |

## Step 10 — Recent features

- **OCSP support (2023-2024):** Native OCSP responder support for
  real-time certificate status checking alongside CRL.
- **EC key algorithm expansion (2023-2024):** Full `EC_prime256v1`
  and `EC_secp384r1` support with all signing algorithm combinations.
- **Report generation API (2023-2024):** Detailed compliance reports
  of certificate issuance, revocation, and CA usage.
- **Quota increases (2024-2025):** Up to 10,000 CAs per account in
  most regions; higher per-second certificate issuance rates.
- **CRL distribution point customization (2024-2025):** Enhanced CRL
  CNAME and frequency controls.
- **Terraform provider (2023-2024):** Full CRL/OCSP config, templates,
  and permission management in `aws_acmpca_certificate_authority`.

## NEVER do these things

1. **NEVER assume the CA is usable immediately after creation.** The
   CA starts in `PENDING_CERTIFICATE`. It must receive its CA
   certificate to become `ACTIVE`.

2. **NEVER create a subordinate CA without verifying the parent CA is
   ACTIVE and has `create-permission`.** Without permission, the
   subordinate stays `PENDING_CERTIFICATE` indefinitely.

3. **NEVER configure CRL without the S3 bucket policy.** CRL
   publication silently fails without the policy granting
   `acm-pca.amazonaws.com` write access. Revoked certs appear valid.

4. **NEVER delete a CA without understanding the waiting period.**
   Deletion enters a mandatory 7-30 day period. After expiration, the
   CA is permanently destroyed and existing certs cannot be revoked.

5. **NEVER use the wrong certificate template.** Templates define key
   usage, extended key usage, and path length. Wrong template = wrong
   certificate extensions.

6. **NEVER forget to set up ACM permissions for managed cert lifecycle.**
   Without `create-permission` for `acm.amazonaws.com`, ACM cannot
   request or renew private certificates.

7. **NEVER assume OCSP replaces CRL.** Some clients only support CRL.
   Enable both for maximum client compatibility.

8. **NEVER issue certificates from a root CA for daily operations.**
   Use subordinate CAs for active issuance. Root CAs should be the
   offline trust anchor.

9. **NEVER revoke a certificate without recording the serial.** The
   certificate serial is required for revocation. Always record issued
   certificate serials in an asset inventory.

10. **NEVER assume CA deletion is instant.** The mandatory waiting
    period is 7-30 days. Plan decommissioning timelines accordingly.

## Output format (STRICT output contract)

When this skill is invoked with an ACM PCA provisioning request, the
agent MUST respond with the block below using the literal all-caps
labels `ACM_PCA:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### Decision tree — CA provisioning flow

```text
Need a private CA?
├── Need a self-signed trust anchor?
│     → ROOT CA
│       ├── Key: RSA_2048 (default) | RSA_4096 | EC_prime256v1 | EC_secp384r1
│       ├── Signing: SHA256withRSA (RSA) | SHA256withECDSA (EC)
│       ├── Template: RootCACertificate/V1
│       ├── CRL? → YES: create S3 bucket + policy → configure CrlConfiguration
│       │          NO: skip (OCSP only or none)
│       ├── ACM integration? → YES: create-permission for acm.amazonaws.com
│       └── Activate: self-sign → import-certificate-authority-certificate
│
├── Need a CA signed by an existing parent?
│     → SUBORDINATE CA
│       ├── PREREQUISITE: parent CA ACTIVE + has create-permission
│       ├── Template: SubordinateCACertificate_PathLen0/V1
│       └── Activate: parent signs CSR → import into subordinate
│
└── Need to issue end-entity certs (TLS)?
      → CA (root or subordinate) must be ACTIVE
      → Template: EndEntityCertificate/CertPassedPathLen/0
      → For ACM-managed lifecycle: create-permission for acm.amazonaws.com
```

### Output template

```text
ACM_PCA: <ca-name> (<ROOT|SUBORDINATE>, <key-algorithm>, <signing-algorithm>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] CA type: ROOT | SUBORDINATE
  [✓|✗] Key algorithm: RSA_2048 | RSA_4096 | EC_prime256v1 | EC_secp384r1
  [✓|✗] Signing algorithm: SHA256withRSA | SHA256withECDSA | ...
  [✓|✗] Subject DN: CN=<cn>, O=<org>, C=<country>
  [✓|✗] CRL S3 bucket: <bucket-name> — exists
  [✓|✗] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject
  [✓|✗] CRL expiration: <days> days, CustomCname: <cname|none>
  [✓|✗] OCSP: enabled | disabled
  [✓|✗] CA status: CREATING | PENDING_CERTIFICATE | ACTIVE
  [✓|✗] CA certificate: self-signed (root) | parent-signed (subordinate, parent <parent-arn>)
  [✓|✗] Certificate template: <template-arn-suffix>
  [✓|✗] ACM integration: create-permission for acm.amazonaws.com (IssueCertificate, GetCertificate, ListPermissions)
  [✓|✗] Parent CA permission: create-permission granted (for subordinate only)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws acm-pca describe-certificate-authority --certificate-authority-arn <ca-arn> --region <region>
  aws acm-pca list-permissions --certificate-authority-arn <ca-arn> --region <region>
  aws s3api get-bucket-policy --bucket <crl-bucket>
```

### FORBIDDEN NEVER patterns (output contract)

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without confirming CA status
   is `ACTIVE`.** A CA in `PENDING_CERTIFICATE` cannot issue
   certificates. The checklist MUST show `CA status: ACTIVE` with `[✓]`.

2. **NEVER mark CRL as `[✓]` without confirming the S3 bucket policy.**
   CRL publication silently fails without the policy granting
   `acm-pca.amazonaws.com` `s3:PutObject`. The checklist MUST show both
   the bucket name AND the policy status as verified.

3. **NEVER mark ACM integration as `[✓]` without confirming
   `create-permission` for `acm.amazonaws.com`.** Without this
   permission, ACM cannot request or renew private certificates. The
   verification MUST include `list-permissions` output.

4. **NEVER show a subordinate CA as `READY_TO_DEPLOY` without confirming
   the parent CA is `ACTIVE` and has `create-permission`.** A
   subordinate without parent signing stays `PENDING_CERTIFICATE`
   indefinitely. Both conditions (parent ACTIVE AND permission granted)
   must be met.

5. **NEVER omit the certificate template from the checklist.** The
   template determines key usage, extended key usage, and path length.
   A missing or wrong template produces a certificate with incorrect
   extensions that may be rejected by clients.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason citing
   what is missing and how to fix it. A bare `[✗]` with no explanation
   is non-compliant.

### Perfect worked example — root CA with RSA_2048, CRL, and ACM end-entity issuance

```text
ACM_PCA: Example Root CA (ROOT, RSA_2048, SHA256withRSA)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] CA type: ROOT
  [✓] Key algorithm: RSA_2048
  [✓] Signing algorithm: SHA256withRSA
  [✓] Subject DN: CN=Example Root CA, O=Example Org, C=US
  [✓] CRL S3 bucket: acm-pca-crl-123456789012-us-east-1 — exists
  [✓] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject, s3:PutObjectAcl, s3:GetBucketAcl, s3:GetBucketLocation
  [✓] CRL expiration: 7 days, CustomCname: crl.example.com
  [✓] OCSP: enabled (OCSP + CRL both active for maximum client compatibility)
  [✓] CA status: ACTIVE
  [✓] CA certificate: self-signed (RootCACertificate/V1 template, validity 10 years)
  [✓] Certificate template: RootCACertificate/V1 (CA cert); EndEntityCertificate/CertPassedPathLen/0 (end-entity issuance)
  [✓] ACM integration: create-permission for acm.amazonaws.com — IssueCertificate, GetCertificate, ListPermissions granted
  [✓] Tags: Environment=production, Purpose=trust-anchor, Owner=platform-team
VERIFICATION_COMMANDS:
  aws acm-pca describe-certificate-authority --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws acm-pca list-permissions --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
  aws s3api get-bucket-policy --bucket acm-pca-crl-123456789012-us-east-1
  aws acm-pca get-certificate-authority-certificate --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc --region us-east-1
```

**How this example maps to provisioning steps:**

1. Created S3 bucket `acm-pca-crl-123456789012-us-east-1` for CRL.
2. Applied bucket policy granting `acm-pca.amazonaws.com` write access.
3. Created ROOT CA with `RSA_2048` / `SHA256withRSA`, CRL enabled (7-day
   expiration, CNAME `crl.example.com`), OCSP enabled.
4. Obtained CSR, issued self-signed certificate using
   `RootCACertificate/V1` template (10-year validity).
5. Imported the certificate to activate the CA (`ACTIVE` status).
6. Granted `create-permission` to `acm.amazonaws.com` so ACM can request
   end-entity certificates using `EndEntityCertificate/CertPassedPathLen/0`
   template.

**Self-check before emit:**
- [ ] CA status confirmed ACTIVE (not PENDING_CERTIFICATE)?
- [ ] CRL bucket policy grants acm-pca.amazonaws.com s3:PutObject?
- [ ] ACM create-permission confirmed via list-permissions?
- [ ] Certificate template correct for the CA type?
- [ ] For subordinate: parent CA ACTIVE + create-permission confirmed?

## Error handling

### CA stuck in PENDING_CERTIFICATE
- The CA has not received its CA certificate. For root, issue a self-
  signed cert and import. For subordinate, request from parent and
  import. Check with `describe-certificate-authority`.

### Subordinate CA cannot be signed by parent
- The parent CA lacks `create-permission`. Use `create-permission` on
  the parent CA to grant `IssueCertificate` and `GetCertificate`.

### CRL not publishing to S3
- The bucket policy does not grant `acm-pca.amazonaws.com`
  `s3:PutObject`. Verify with `get-bucket-policy` and add the policy.

### ACM cannot request private certificates
- The PCA lacks `create-permission` for `acm.amazonaws.com`. Grant
  `IssueCertificate`, `GetCertificate`, `ListPermissions`.

### CA deletion did not take effect immediately
- CA deletion has a mandatory 7-30 day waiting period. This is by
  design, not an error. Use `restore-certificate-authority` to undo.

## Domain

AWS CloudOps / AWS Private Certificate Authority (ACM PCA) Provisioning
& PKI Management.

## AWS documentation

- **ACM PCA User Guide** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaWelcome.html
- **Create a CA** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaCreateCa.html
- **Issue a certificate** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaIssueCert.html
- **CRL configuration** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaPlanDistribution.html
- **OCSP configuration** — https://docs.aws.amazon.com/privateca/latest/userguide/ocsp.html
- **CA permissions** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaCreatePerms.html
- **Certificate templates** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaTemplates.html
- **CA deletion** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaDeleteCa.html
- **ACM integration** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaIntegration.html
- **Revocation** — https://docs.aws.amazon.com/privateca/latest/userguide/PcaRevoke.html
