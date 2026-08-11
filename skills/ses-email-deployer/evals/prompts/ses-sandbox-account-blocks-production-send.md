# Eval prompt: ses-sandbox-account-blocks-production-send

Diagnose why production sends fail because the account is still in
the SES sandbox. Walk the pre-flight checks and emit the standard
VERDICT block.

## Scenario

An operator has a fully configured SES domain identity
`example.com` in `us-east-1` (verified, DKIM signing, MAIL FROM,
DMARC, configuration set with event publishing, dedicated IP pool
with warmup). However, `aws sesv2 get-account` shows the account
is still in the sandbox.

## Known facts

- **Domain identity:** `example.com` (verified, DKIM, MAIL FROM,
  DMARC all configured).
- **Configuration set:** `transactional-cs` with event publishing.
- **Dedicated IP pool:** `transactional-pool` with warmup.
- **Account status:** `aws sesv2 get-account` returns
  `EnforcementStatus` indicating sandbox (NOT production).
- **Operator action:** tries to send 10,000 emails to unverified
  recipients and expects success.

## Symptom

The send call returns `ThrottlingException` or
`MessageRejected` because the account is in sandbox. The operator
needs to know the account is sandboxed and how to request
production access.
