# Baseline (no-skill) response: schema-mismatch-action-not-declared

This file captures what a generic assistant produces WITHOUT the
verified-permissions-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, schema-retroactive-validation knowledge).

---

The policy references `PhotoApp::Action::"DeletePhoto"` but looking at the
schema, the actions map only has `ViewPhoto` and `UploadPhoto`. So
`DeletePhoto` is not declared.

This might have happened if the action was removed from the schema at some
point. You should either add `DeletePhoto` back to the schema or update the
policy to use one of the existing actions.

The rest of the policy looks fine — it requires `principal.role == "admin"`
which is a reasonable condition.
