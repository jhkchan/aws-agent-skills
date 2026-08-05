# Baseline (no-skill) response: config-gap-invalid-analysis-template-sql

This file captures what a generic assistant produces WITHOUT the
cleanrooms-collaboration-auditor skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, enumerated
FINDINGS, specific remediation, multi-party reasoning).

---

The collaboration has two ACTIVE members, DP is enabled, and epsilon
spend is low. The configured table cr-events looks fine.

The analysis template tmpl-events-summary references a table called
`cr_legacy_events` in its SQL body, but the only configured table in
the collaboration is `cr-events`. This looks like a typo or a stale
reference. You should update the template to reference the correct
table name.
