# Eval prompt: ses-domain-stuck-pending-dkim

Diagnose why a domain identity is stuck in `PENDING` because the
DKIM CNAME records were never published. Walk the pre-flight
checks and emit the standard VERDICT block.

## Scenario

An operator created the domain identity `example.com` in
`us-east-1` via `create-email-identity`. However, the DKIM tokens
were never published as CNAME records in Route 53.

## Known facts

- **Domain identity:** `example.com` (created in us-east-1).
- **`get-email-identity` output:**
  `VerificationStatus=PENDING`,
  `DkimSigningAttributes.Status=NOTSTARTD`.
- **Route 53:** hosted zone `Z2ABCDEF12345` has no
  `*_._domainkey.example.com` CNAME records.
- **DKIM tokens returned at creation:**
  `abc123examplecom`, `def456examplecom`, `ghi789examplecom`.
- **Operator action:** tries to send a test email and expects
  success.

## Symptom

The operator tries to send a test email and it fails because the
domain identity is not verified. The cause is unpublished DKIM
CNAME records.
