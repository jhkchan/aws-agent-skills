# Worked Examples — Backup Vault Compliance

Load-on-demand full output-contract walkthroughs. The primary AUTOMATION_DEPLOYED
example lives in SKILL.md.

### Worked example — REVIEW_REQUIRED, governance mode on compliance vault

```text
COMPLIANCE: compliance-vault-review
VAULT: compliance-vault
POLICY:
  - Vault policy: deny-non-encrypted (correct)
  - KMS enforcement: correct approved key
LOCK:
  - Mode: GOVERNANCE (WRONG — regulatory requirement is COMPLIANCE)
  - MinRetention: 30 days (WRONG — minimum should be 90 days)
  - MaxRetention: 365 days (WRONG — should be 2557 days for 7-year compliance)
  - CoolOff: lock removable by privileged principal
COVERAGE:
  - Total resources: 50
  - Covered: 50
  - Gap: 0
REPLICATION:
  - Cross-region: NOT CONFIGURED (required for DR)
VERDICT: REVIEW_REQUIRED
GAP: Vault is in GOVERNANCE mode but regulatory requirement (SEC 17a-4) demands COMPLIANCE mode. MinRetention is 30d but policy requires 90d minimum. Cross-region replication is not configured. These three issues must be resolved before the vault can be certified as compliant. Note: switching from GOVERNANCE to COMPLIANCE mode requires removing the current lock (possible in governance mode) and re-deploying in compliance mode with the correct retention parameters.
TEMPLATE: (deploy after mode and retention parameters are confirmed)
```
