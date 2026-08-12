# Eval: trust-anchor-certificate-authority

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — trust anchor binds self-managed CA cert (CERTIFICATE_BUNDLE) to AWS IAM, IAM role RolesAnywhereCIRunner with rolesanywhere.amazonaws.com trust policy and AmazonS3ReadOnlyAccess

## Prompt

Create a Roles Anywhere trust anchor in us-east-1 account
123456789012. Bind my external self-managed CA certificate
(ca-cert.pem, PEM-encoded) to AWS IAM. Name the trust anchor
prod-pki-trust-anchor. The IAM role RolesAnywhereCIRunner
should have a trust policy allowing
rolesanywhere.amazonaws.com to assume it. The role should have
AmazonS3ReadOnlyAccess attached. Region us-east-1.
