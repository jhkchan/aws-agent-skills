# Baseline (no-skill) response: wildcard-kms-all-no-condition

This file captures what a generic assistant produces WITHOUT the
kms-key-policy-auditor skill loaded.

---

This key policy grants `kms:*` to `Principal: "*"`, which means any AWS
account can use this key for any operation including decrypt, encrypt,
and key management actions. This is very permissive.

You should restrict the principal to specific accounts or roles. Also,
key rotation is disabled, which you may want to enable.

This is a significant security risk because anyone with an AWS account
could decrypt your data.
