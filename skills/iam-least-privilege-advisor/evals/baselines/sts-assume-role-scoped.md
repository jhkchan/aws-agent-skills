# Baseline (no-skill) response: sts-assume-role-scoped

This file captures what a generic assistant produces WITHOUT the
iam-least-privilege-advisor skill loaded. Note: the baseline does not
recognize that AssumeRole on a specific ARN is least-privilege (it flags
AssumeRole generically as risky), and omits the deterministic VERDICT.

---

`sts:AssumeRole` is a sensitive permission because it lets the principal
assume another role and inherit that role's permissions. You should be careful
with this one.

That said, it's scoped to a specific role ARN
(`arn:aws:iam::123456789012:role/cross-audit-role`), which limits the blast
radius compared to a wildcard resource. I'd recommend reviewing the trust
policy on the target role to make sure only the expected principal can assume
it. You might also want to add an MFA condition.
