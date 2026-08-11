# Eval: lifecycle-outside-lock-window

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — DeleteAfterDays=7 with MinRetentionDays=90 violates the lock window; backup jobs would fail

## Prompt

Create an AWS Backup vault named locked-vault in us-east-1
account 123456789012. The vault will be locked in COMPLIANCE mode
with MinRetentionDays=90 and MaxRetentionDays=365. Create a
backup plan targeting this vault with lifecycle
DeleteAfterDays=7 and MoveToColdStorageAfterDays=3. The plan
should run daily. Tag-based selection.
