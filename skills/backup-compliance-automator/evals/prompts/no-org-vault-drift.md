# Eval prompt: no-org-vault-drift

Validate this existing AWS Backup compliance posture for our 50-account
org aligned to SOC2. Emit the standard Backup block (FRAMEWORK,
REPORTING, LEGAL_HOLD, CROSS_ACCOUNT, SEARCH, VERIFICATION, VERDICT,
FINDINGS, REMEDIATION).

Current state:
- 50 member accounts in AWS Organizations
- Compliance framework: SOC2 (claimed)
- Resources in scope: EC2, RDS
- Existing posture:
  - No delegated administrator for backup.amazonaws.com
  - No org-wide backup vault (each account has its own)
  - Per-account backup plans deployed in 38 of 50 accounts via
    CloudFormation StackSets (manual rollout, no central tracking)
  - 12 of 50 accounts have NO backup plan at all
  - Of the 38 covered accounts, the latest recovery point in 6 accounts
    is older than 7 days (stale — undetected centrally)
  - Audit Manager: framework exists in only 5 of 50 accounts; no
    centralized view of compliance across the org
  - Vault Lock: configured per-account in GOVERNANCE mode with variable
    retention days (some accounts 30d, some 90d, some 365d)
  - Legal hold: never tested in any account
  - Reports: per-account monthly, no aggregation — an auditor would
    need to log into 50 accounts to see evidence
  - Restore drill: only 2 of 50 accounts have tested restores within
    the last 90 days

Expected: MANUAL_STEP_REQUIRED. The skill must flag:
1. No delegated admin or org-wide vault — no central audit view across
   50 accounts. Recommend enabling backup delegated admin to a central
   audit account and creating an org-compliance-vault.
2. 12 accounts have zero backup coverage — major SOC2 finding. The
   StackSet rollout did not reach all accounts.
3. 6 accounts have stale recovery points (no central detection without
   org view).
4. Vault Lock in GOVERNANCE mode with variable retention — not SOC2-
   grade; switch to LOCK_MODE with consistent retention.
5. Legal hold never tested.
6. Restore drill coverage is 2/50 — far below the 90-day SOC2 bar.
