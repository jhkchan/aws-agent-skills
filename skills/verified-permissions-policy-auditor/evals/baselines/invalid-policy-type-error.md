# Baseline (no-skill) response: invalid-policy-type-error

This file captures what a generic assistant produces WITHOUT the
verified-permissions-policy-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, Cedar type-system reasoning).

---

This Cedar policy compares `principal.age` (which is a Long in the schema)
with the string `"eighteen"`. That looks like a type mismatch — you're
comparing a number with a string using the `>=` operator.

You should fix the condition to compare with a number instead:

```cedar
when { principal.age >= 18 };
```

The rest of the policy looks reasonable — it scopes the principal, action,
and resource correctly.
