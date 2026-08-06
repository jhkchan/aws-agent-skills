# Baseline (no-skill) response: coverage-gap-empty-selection

This file captures what a generic assistant produces WITHOUT the
backup-plan-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, coverage-gap reasoning).

---

This backup plan has a daily schedule with 30-day retention, a vault with
compliance-mode lock, and customer-managed KMS encryption. The vault
configuration looks good.

However, the resource selection is empty — the Resources list is empty
and there are no tags or conditions defined. This means the plan is not
actually backing up any resources.

You should add resources to the selection, either by specifying explicit
ARNs or by using tag-based selection. Otherwise the plan runs on schedule
but produces no backups.
