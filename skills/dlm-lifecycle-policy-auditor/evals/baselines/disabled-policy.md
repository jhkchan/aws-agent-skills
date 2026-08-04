# Baseline (no-skill) response: disabled-policy

This file captures what a generic assistant produces WITHOUT the
dlm-lifecycle-policy-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, silent-failure reasoning).

---

This DLM lifecycle policy is currently disabled. Even though the schedule
and retention settings look reasonable, a disabled policy does not create
any snapshots. You should re-enable it if backups are expected.

The policy also lacks a cross-region copy target, which means your backups
are only in one region.

To fix: enable the policy in the console or via
`aws dlm update-lifecycle-policy --policy-id <id> --state ENABLED`.
