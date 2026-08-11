# Eval: missing-kms-key-policy-cross-account

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — cross-account access requested but KMS key policy does not grant the cross-account principal

## Prompt

Configure cross-account access for CodeCommit repository
shared-repo in us-east-1, account 123456789012, to grant access
to account 888888888888. The repository is encrypted with
customer-managed KMS key
arn:aws:kms:us-east-1:123456789012:key/efgh-5678. The KMS key
policy currently only grants the owning account root and does
NOT include the cross-account principal.
