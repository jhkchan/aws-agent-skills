# Baseline (no-skill) response: cfn-hardcoded-secrets

This file captures what a generic assistant produces WITHOUT the
iac-template-automator skill loaded.

---

This CloudFormation template creates an RDS Aurora cluster with a Lambda
rotation role. The template looks reasonable — it has StorageEncrypted
and DeletionProtection enabled. You might want to tighten the IAM
permissions on the rotation role a bit, but it should work as-is for
development. For production, consider replacing the hardcoded password
with a parameter or Secrets Manager reference.
