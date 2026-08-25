# Backup Schedule Automator — secondary worked examples

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Worked example — REVIEW_REQUIRED, missing vault lock (moved verbatim from SKILL.md)

```text
BACKUP: compliance-backup-gaps
PLAN: daily-7d (exists but no lifecycle tiering)
VAULT: Default (NO access policy, NO vault lock)
LIFECYCLE: NONE — all backups in hot storage indefinitely
TRIGGER: SCHEDULED
RESTORE_TEST: NONE — no restore testing configured
TAG_SCOPE: backup-plan=daily (but 0 resources match)
CROSS_ACCOUNT: NONE
CROSS_REGION: NONE
VERDICT: REVIEW_REQUIRED
GAP: Three critical gaps: (1) Default vault has no access policy or lock — move to named vault with GOVERNANCE lock for compliance; (2) No lifecycle tiering — hot storage cost for 365-day retention is 5x a tiered plan; (3) Zero resources match the tag scope — verify tag inventory or the plan backs up nothing. Additionally, no restore testing exists, so RTO/RPO is unvalidated.
TEMPLATE: (see Steps 2, 3, 6, 7, 8 for remediation)
```

