# Baseline (no-skill) response: cross-account-root-no-externalid

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded. Note: the baseline does not
recognize the root-ARN expansion rule (grants to ALL principals in the
account, not just root) and does not identify the missing ExternalId guard.

---

This trust policy allows account 999999999999 to assume the role. The
Principal is set to the root ARN of that account.

Cross-account access can be risky. You should make sure you trust account
999999999999 before keeping this policy. You might want to add an ExternalId
to make it more secure, but it's not strictly required.

The action `sts:AssumeRole` is the standard one for role assumption, so
that looks fine.
