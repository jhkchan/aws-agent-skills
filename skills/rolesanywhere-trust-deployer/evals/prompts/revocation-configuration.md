# Eval: revocation-configuration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — CRL prod-pki-crl created from crl.pem and attached to trust anchor ta-aaa111222; create and update workflow shown; compromised certs rejected before expiration

## Prompt

Configure revocation for a Roles Anywhere trust anchor in
us-east-1 account 123456789012. Trust anchor ID ta-aaa111222.
Create a CRL named prod-pki-crl from crl.pem (base64-encoded).
The trust anchor should reject any certificate listed on the
CRL. Show the create and update CRL commands. Region us-east-1.
