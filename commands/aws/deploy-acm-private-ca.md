---
description: Provision an AWS Private Certificate Authority (ACM PCA) with production-grade defaults (root vs subordinate, key/signing algorithm, CRL with S3 bucket policy, OCSP, certificate templates, ACM integration permissions, CA deletion waiting period). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create private certificate authority"
  - "create private ca"
  - "acm pca root ca"
  - "acm pca subordinate ca"
  - "issue private certificate"
  - "crl configuration s3"
  - "revoke certificate acm pca"
  - "ca deletion waiting period"
  - "acm pca permissions"
  - "acm managed private cert"
  - "private ca"
  - "pki deployment"
routes_to: acm-private-ca-deployer
---

# /aws:deploy-acm-private-ca

Activate the `acm-private-ca-deployer` skill and provision an AWS
Private Certificate Authority with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. CA type: root vs subordinate
2. Key and signing algorithm selection (RSA_2048, EC_prime256v1, etc.)
3. CRL configuration (S3 bucket, bucket policy, expiration)
4. Create the CA and issue CA certificate (self-signed root or parent-signed subordinate)
5. Certificate templates and end-entity issuance
6. CA permissions for ACM integration
7. Certificate revocation and OCSP
8. CA deletion (mandatory 7-30 day waiting period)
9. Audit via CloudTrail

## When to use

- You need to create a private certificate authority (root or subordinate).
- You need to issue private certificates for internal TLS.
- You need to configure CRL or OCSP revocation.
- You need to set up a subordinate CA hierarchy.
- You need to integrate ACM PCA with ACM for managed cert lifecycle.
- You need to delete or restore a private CA.
- You need to revoke a certificate.

## When NOT to use

- **Public TLS certificates** — use ACM public certificate issuance.
- **AWS Secrets Manager** — for storing third-party certificates.
- **AWS KMS** — for encryption key management (different from PKI).

## How to invoke

### Slash command

```
/aws:deploy-acm-private-ca
```

Then provide: CA type (root/subordinate), key algorithm, signing
algorithm, subject DN, CRL configuration (bucket, expiration),
OCSP preference, certificate template, ACM integration needs, tags.

### Natural language

Any of these routes to the same skill:

- "create a private root CA with CRL revocation"
- "set up a subordinate CA signed by my root CA"
- "issue a private TLS certificate from my PCA"
- "configure ACM PCA permissions for ACM integration"
- "delete a private certificate authority"

### CLI routing

```bash
node cli/bin/cli.js route "create a private certificate authority"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create private
CAs or issue private certificates. The output checklist feeds into
verification pipelines and downstream security audit skills.

## Example

```
You: /aws:deploy-acm-private-ca

     Create a private root CA in us-east-1. RSA_2048,
     SHA256withRSA. Subject CN=Example Root CA. Enable CRL with
     bucket acm-pca-crl-123456789012-us-east-1.

Skill:
  ACM_PCA: arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc (ROOT, RSA_2048, SHA256withRSA)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] CA type: ROOT
    [✓] Key algorithm: RSA_2048
    [✓] Signing algorithm: SHA256withRSA
    [✓] CRL bucket policy: grants acm-pca.amazonaws.com s3:PutObject
    [✓] CA status: ACTIVE
    [✓] CA certificate: self-signed (RootCACertificate/V1)
  VERIFICATION_COMMANDS:
    aws acm-pca describe-certificate-authority --certificate-authority-arn <ca-arn> --region us-east-1
```

## References

- Skill definition: `skills/acm-private-ca-deployer/SKILL.md`
- CA hierarchy and signing guide: `skills/acm-private-ca-deployer/references/ca-hierarchy-and-signing.md`
- CRL and revocation guide: `skills/acm-private-ca-deployer/references/crl-and-revocation.md`
- Eval suite: `skills/acm-private-ca-deployer/evals/evals.json`
