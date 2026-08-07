# Baseline (no-skill) response: kms-decrypt-cmk-role-missing

---

Your Lambda can't decrypt its environment variables. The error
"Could not decrypt KMS" means KMS access is broken. Check that the
execution role has kms:Decrypt permission on the KMS key.

You migrated to a customer-managed key recently — that's probably
when this broke. Add kms:Decrypt to the role and redeploy.
