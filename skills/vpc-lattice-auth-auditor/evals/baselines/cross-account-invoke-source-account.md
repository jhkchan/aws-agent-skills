# Baseline (no-skill) response: cross-account-invoke-source-account

This file captures what a generic assistant produces WITHOUT the
vpc-lattice-auth-auditor skill loaded.

---

The auth policy allows cross-account Invoke for account 222222222222 but
restricts it with an aws:SourceAccount condition. This looks reasonably
scoped since the condition ensures requests come from the expected account.

The RAM share to the same account is consistent with the policy. Target
groups are in-VPC instance targets. This setup appears secure.
