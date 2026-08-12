# Eval: end-entity-certificate-issuance

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — end-entity cert from ACTIVE subordinate CA, EndEntityCertificate_CertPassedPathLen_0 template, 365-day validity

## Prompt

Issue an end-entity certificate from subordinate CA
arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/dddd-eeee-ffff
in us-east-1. The subordinate CA is ACTIVE. CSR is ready at
server.csr. Signing algorithm SHA256withRSA. Use template
EndEntityCertificate/CertPassedPathLen/0. Validity 365 days.
Tags: Environment=production, Service=api.
