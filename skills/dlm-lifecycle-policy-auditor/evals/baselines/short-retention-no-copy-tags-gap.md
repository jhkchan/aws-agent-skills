# Baseline (no-skill) response: short-retention-no-copy-tags-gap

This file captures what a generic assistant produces WITHOUT the
dlm-lifecycle-policy-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, silent-failure reasoning).

---

This DLM policy is enabled and targets billing-app volumes, but the
retention is set to only 1 snapshot. That means if the latest snapshot is
corrupt, you have no earlier snapshot to recover from. You should increase
the retention count to at least 7 for daily snapshots.

Also, CopyTags is false, which means the volume tags are not copied to the
snapshot. This may break any automation that filters snapshots by tag.

There is also no cross-region copy.
