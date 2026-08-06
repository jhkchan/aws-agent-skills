# Baseline (no-skill) response: overpermissive-bare-permit

This file captures what a generic assistant produces WITHOUT the
verified-permissions-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, bare-permit blast-radius reasoning).

---

This policy is very permissive. `permit (principal, action, resource);`
grants access to everything without any restrictions. There are no type
annotations on the scope variables and no `when` or `unless` conditions.

You should add scope constraints and conditions to limit who can do what.
For example:

```cedar
permit (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"ViewPhoto",
  resource: PhotoApp::Photo
)
when { principal.userId == resource.owner };
```

This limits access to photo owners only.
