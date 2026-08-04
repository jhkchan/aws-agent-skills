# Baseline (no-skill) response: s3-get-wildcard-scoped-resource

This file captures what a generic assistant produces WITHOUT the
iam-least-privilege-advisor skill loaded. Note: the baseline misses the
silent-expansion risk (`s3:Get*` auto-includes future Get* APIs) and the
AMBIGUOUS verdict the skill emits.

---

This policy looks pretty safe — it only grants read operations (`Get*` and
`List*`) on a specific bucket. The resource is scoped to `app-data-prod` and
its contents, so it's not a wildcard on all resources.

The `s3:Get*` wildcard is convenient and commonly used for read-only
workloads. I'd say this is acceptable as-is, though you could expand the
wildcards to explicit action names if you want to be extra careful.
