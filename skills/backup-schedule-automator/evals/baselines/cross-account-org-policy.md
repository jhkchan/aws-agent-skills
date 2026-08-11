# Baseline (no-skill) response: cross-account-org-policy

This file captures what a generic assistant produces WITHOUT the
backup-schedule-automator skill loaded.

---

For cross-account backup using Organizations, you can create a backup
policy at the OU level. This will apply to all member accounts
automatically.

The policy would specify the backup plan, schedule, and copy actions.
Each member account will inherit the plan.

```
aws organizations create-policy --type BACKUP_POLICY --name org-backup ...
```

You need to make sure the DR region vault exists and has the right
permissions for cross-account access. Also check that the KMS keys are
shared properly.
