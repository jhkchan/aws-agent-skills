# Error handling - CodePipeline V2 Deployer (load on demand)

## Remediation guidance

**Ordering principle:** trigger scoping first (blast radius), then
cross-account KMS/IAM wiring (deploy failures), then artifact bucket
hardening (security), then variable validation (silent failures),
then optimization (lifecycle rules, approval timeouts).

- **CodeConnections PENDING:** open the CodeConnections console in
  us-east-1, click "Update pending connection," authorize via the
  GitHub OAuth flow, verify state changes to AVAILABLE.
- **KMS key policy missing cross-account grants:** update the key
  policy to grant the target role `kms:Decrypt` and
  `kms:GenerateDataKey`; verify with `aws kms get-key-policy`.
- **Artifact bucket allows public access:** apply
  `block-public-access` with all four sub-settings true, enable KMS
  encryption with the customer-managed CMK, enable versioning.
- **V2 with stale `PollForSourceChanges: true`:** set `DetectOptions:
  false` and add a trigger block with branch/path/tag filter.

