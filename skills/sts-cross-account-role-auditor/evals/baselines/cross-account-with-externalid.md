# Baseline (no-skill) response: cross-account-with-externalid

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded. Note: the baseline treats
the ExternalId as sufficient protection but does not distinguish the
CONDITIONAL verdict from a truly safe trust, and does not note that the
root ARN still expands to all principals in the account.

---

This trust policy allows account 999999999999 to assume the role, and it
has an ExternalId condition. That's good practice for cross-account access.

The ExternalId adds an extra layer of security because the assuming
principal needs to know the secret ID. This policy looks reasonably secure
for cross-account delegation.
