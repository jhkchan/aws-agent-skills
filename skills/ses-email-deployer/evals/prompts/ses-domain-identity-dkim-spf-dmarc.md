# Eval prompt: ses-domain-identity-dkim-spf-dmarc

Create a domain identity, publish DKIM CNAME records, configure a
custom MAIL FROM domain with MX + SPF, and publish a DMARC
quarantine policy. Walk the pre-flight checks and emit the
standard VERDICT block (DOMAIN, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

## Scenario

An operator wants to provision SES for the domain `example.com`
in `us-east-1`.

## Known facts

- **Domain:** `example.com` (hosted zone `Z2ABCDEF12345` in Route 53).
- **Account status:** production access granted
  (`EnforcementStatus` = `PRODUCTION`).
- **DKIM:** signing enabled; 3 tokens to be published as CNAME.
- **MAIL FROM domain:** `mail.example.com`.
- **SPF policy:** `v=spf1 include:amazonses.com ~all` (soft fail).
- **DMARC policy:** `p=quarantine` with `rua=mailto:dmarc@example.com`,
  `adkim=s`, `aspf=s`.
- **Region:** us-east-1 (MX endpoint:
  `feedback-smtp.us-east-1.amazonses.com`).

## Symptom

The operator needs the `create-email-identity` CLI, the Route 53
record publication for DKIM CNAME / MAIL FROM MX + SPF / DMARC
TXT, and verification that the identity flips to `Success`.
