# Baseline (no-skill) response: rotation-disabled-same-account-high

This file captures what a generic assistant produces WITHOUT the
kms-key-policy-auditor skill loaded.

---

The key policy grants access to same-account principals only, which is
good. The root account has full access and the application role has
encrypt, decrypt, and data key generation permissions.

However, key rotation is disabled. You should enable automatic key
rotation so the key material is rotated annually. You can do this with
`aws kms enable-key-rotation`.

Otherwise the policy looks fine — no wildcard principals or
cross-account access.
