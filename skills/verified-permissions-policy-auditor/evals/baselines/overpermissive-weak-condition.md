# Baseline (no-skill) response: overpermissive-weak-condition

This file captures what a generic assistant produces WITHOUT the
verified-permissions-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, unscoped-action analysis,
weak-condition detection).

---

This policy scopes the principal to `PhotoApp::User` which is good, and it
has a condition checking that the user account is active. But the `action`
and `resource` don't have type annotations, so it applies to all actions and
all resources.

You should add type annotations to scope down which actions and resources
are covered:

```cedar
permit (
  principal: PhotoApp::User,
  action: PhotoApp::Action::"ViewPhoto",
  resource: PhotoApp::Photo
)
when { principal.accountStatus == "active" };
```

The condition itself might also be too broad since most users will have an
active account status.
