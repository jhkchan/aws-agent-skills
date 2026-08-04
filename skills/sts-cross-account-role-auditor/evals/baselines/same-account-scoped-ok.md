# Baseline (no-skill) response: same-account-scoped-ok

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded. Note: the baseline reaches
the right conclusion (the trust is fine) but does not emit a deterministic
VERDICT block or cite the specific classification rule.

---

This trust policy allows a role in the same account (123456789012) to
assume this role. The Principal is a specific role ARN, not a wildcard,
so it's scoped to just that one role.

This looks like a safe configuration. The trust is within the same account
and scoped to a specific role, which is a good least-privilege pattern.
