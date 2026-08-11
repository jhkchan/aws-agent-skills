# Baseline (no-skill) response: vault-lock-worm-compliance

This file captures what a generic assistant produces WITHOUT the
backup-schedule-automator skill loaded.

---

For SOX compliance with 7-year retention, you need to create a backup
vault and enable vault lock in COMPLIANCE mode. Set the minimum
retention to 365 days and maximum to 2555 days.

```
aws backup put-backup-vault-lock-configuration --backup-vault-name compliance-vault --mode COMPLIANCE ...
```

Then create a backup plan with daily backups and the right retention.
Make sure RDS instances are tagged so they get picked up.

You should probably test that the vault lock works before going live.
