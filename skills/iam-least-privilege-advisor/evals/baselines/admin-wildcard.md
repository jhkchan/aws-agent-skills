# Baseline (no-skill) response: admin-wildcard

This file captures what a generic assistant produces WITHOUT the
iam-least-privilege-advisor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, RISK level, specific remediation).

---

This policy grants full administrative access. `Action: "*"` combined with
`Resource: "*"` means the principal can perform any action on any resource in
the account, which is equivalent to the AWS managed policy
`AdministratorAccess`.

This is generally considered too permissive for most use cases. You might want
to replace it with a more scoped policy that only grants the specific actions
your application needs. Consider using AWS IAM Access Analyzer to generate a
policy based on CloudTrail activity.

It's risky because someone with this policy could delete resources, modify
security settings, or access all your data.
