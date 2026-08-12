# Eval: root-ca-with-crl

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — root CA, RSA_2048, SHA256withRSA, CRL with S3 bucket + policy, self-signed RootCACertificate/V1, ACTIVE status

## Prompt

Create a private root CA in us-east-1, account 123456789012.
Key algorithm RSA_2048, signing algorithm SHA256withRSA.
Subject: CN=Example Root CA, O=Example Org, C=US. Enable CRL
revocation with S3 bucket acm-pca-crl-123456789012-us-east-1,
expiration 7 days, CNAME crl.example.com. Self-signed root
certificate valid 10 years using RootCACertificate/V1 template.
Tags: Environment=production, Purpose=trust-anchor.
