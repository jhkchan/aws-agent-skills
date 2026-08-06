# Baseline (no-skill) response: empty-target-tags

This file captures what a generic assistant produces WITHOUT the
dlm-lifecycle-policy-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, silent-failure reasoning).

---

This DLM policy is enabled but has an empty TargetTags array. Without tag
targets, the policy does not know which volumes to snapshot. You should add
the appropriate tag filters so the policy matches the intended volumes.

The schedule and retention look fine. Once you add TargetTags, the policy
should start creating snapshots on the configured schedule.
