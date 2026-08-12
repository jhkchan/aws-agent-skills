# Eval: subordinate-ca-signed-by-root

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — subordinate CA, parent CA ACTIVE + create-permission, parent-signed cert, ACM service principal permission for managed lifecycle

## Prompt

Create a subordinate CA in us-east-1, account 123456789012.
Parent root CA ARN: arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/aaaa-bbbb-cccc.
The parent CA is ACTIVE and has create-permission granted.
Key algorithm RSA_2048, signing algorithm SHA256withRSA.
Subject: CN=Example Subordinate CA, O=Example Org, C=US.
Enable CRL with bucket acm-pca-crl-123456789012-us-east-1,
expiration 7 days. Also enable OCSP. Subordinate certificate
valid 5 years using SubordinateCACertificate_PathLen0/V1 template.
Grant ACM service principal permission for managed cert lifecycle.
Tags: Environment=production, Purpose=issuing-ca.
