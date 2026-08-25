# Diagnostic Commands — Backup Compliance Automator

## Live-account pre-flight checks
**Live-account pre-flight checks (skip for offline authoring):**
1. Verify AWS Backup is enabled: `aws backup list-backup-plans`.
2. Verify Audit Manager is enabled: `aws backup audit-manager list-frameworks`.
3. For org: verify backup delegated admin: `aws organizations list-delegated-administrators --service-principal backup.amazonaws.com`.
4. Verify backup vault: `aws backup list-backup-vaults`.
5. Verify Backup Search (if applicable): `aws backup search list-backup-plans` (available in supported regions).
