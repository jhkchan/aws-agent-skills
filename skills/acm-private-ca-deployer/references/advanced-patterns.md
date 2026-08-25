# Advanced Patterns — ACM Private CA Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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
