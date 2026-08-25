# Error Handling — Roles Anywhere Trust Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


## Error handling

### AccessDenied when assuming a role
- The IAM role's trust policy does not allow
  `rolesanywhere.amazonaws.com`. Verify the trust policy. Also verify
  the profile's `roleArns` includes the requested role ARN.

### Certificate rejected: not signed by trusted CA
- The certificate is not signed by the CA bound to the trust anchor.
  Verify the chain: `openssl verify -CAfile ca-cert.pem client-cert.pem`.
  Also verify the trust anchor's CA cert matches.

### Certificate rejected: expired or revoked
- The certificate has passed its expiration date (generate a new one)
  or is on the CRL (remove from the CRL and update if accidental).

### Credential helper not found
- The `aws_signing_helper` binary is not on the client machine.
  Download it from the AWS Roles Anywhere helper tool S3 bucket.

### Session expires too quickly
- The session duration is too short. Update the profile's
  `durationSeconds` (max: 43200 seconds = 12 hours). The credential
  helper re-runs automatically if configured as a credential process.
