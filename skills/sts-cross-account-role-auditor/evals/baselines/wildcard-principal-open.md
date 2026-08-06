# Baseline (no-skill) response: wildcard-principal-open

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, RISK level, confused-deputy
reasoning, specific remediation).

---

This trust policy has `Principal: "*"` which means anyone can assume the
role. That's very dangerous because it lets any AWS user take on this role's
permissions.

You should probably restrict the Principal to only the accounts or services
that need access. Using a wildcard in a trust policy is generally not
recommended.
