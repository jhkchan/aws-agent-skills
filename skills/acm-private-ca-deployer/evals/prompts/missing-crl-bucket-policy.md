# Eval: missing-crl-bucket-policy

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — S3 bucket exists but no policy granting acm-pca.amazonaws.com write access; CRL publication would silently fail

## Prompt

Create a private root CA in us-east-1, account 123456789012.
Key algorithm RSA_2048, signing algorithm SHA256withRSA.
Subject: CN=Example Root CA, O=Example Org, C=US. Enable CRL
revocation with S3 bucket acm-pca-crl-123456789012-us-east-1.
The S3 bucket exists but does NOT have a bucket policy granting
acm-pca.amazonaws.com write access.
