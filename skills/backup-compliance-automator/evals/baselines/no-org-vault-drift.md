# Baseline (no-skill) response: no-org-vault-drift

This file captures what a generic assistant produces WITHOUT the
backup-compliance-automator skill loaded.

---

To get backup compliance across your 50-account org, you should deploy
your backup plans to all 50 accounts using CloudFormation StackSets
from your management account. This ensures consistent configuration
across the org.

You can also use AWS Organizations to delegate an administrator account
that can see all backups centrally. Schedule monthly compliance reports
in each account and aggregate them for the auditor.

Make sure each account has Vault Lock configured and test restores
regularly.

---

Notes on what the baseline misses:

- Treats per-account StackSet deployment as the primary path, missing
  that delegated admin + org-wide vault is the canonical centralization
  pattern (single audit view vs 50 manual aggregations).
- Does NOT flag that 12 of 50 accounts have ZERO backup coverage as a
  CRITICAL SOC2 finding.
- Does NOT flag the 6 accounts with stale recovery points as a gap
  (invisible without org view).
- Does NOT specify LOCK_MODE (compliance mode) for Vault Lock — the
  existing GOVERNANCE mode with variable retention fails SOC2 audit.
- Does NOT flag the 2/50 restore drill coverage as a major gap.
- Does NOT recommend the delegated admin + org-compliance-vault pattern
  as the centralization mechanism.
- Does NOT flag that legal hold has never been tested.
