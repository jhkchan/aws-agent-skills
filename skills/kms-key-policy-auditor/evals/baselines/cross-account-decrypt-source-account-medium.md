# Baseline (no-skill) response: cross-account-decrypt-source-account-medium

This file captures what a generic assistant produces WITHOUT the
kms-key-policy-auditor skill loaded.

---

This key policy grants kms:Decrypt to an external account
(222222222222), but it has an aws:SourceAccount condition that restricts
the request to that account. This is better than having no condition.

The access is scoped to the specific account, which provides some
protection. However, the external role can still decrypt any data under
this key as long as the request comes from that account.

Rotation is enabled. This seems reasonably secure if the cross-account
access is intentional.
