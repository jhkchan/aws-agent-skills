# Baseline (no-skill) response: cross-account-kms-key-policy

This file captures what a generic assistant produces WITHOUT the
ssm-session-manager-troubleshooter skill loaded - the contrast
that proves the skill adds structure (4-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The cross-account session failed because of a KMS key permission
error. Your assumed role can't generate a data key using the
target account's KMS key. You need to update the KMS key policy
in the target account to allow your source account to use it.

Add `kms:GenerateDataKey` and `kms:Decrypt` permissions for your
source account principal in the target account's key policy.
