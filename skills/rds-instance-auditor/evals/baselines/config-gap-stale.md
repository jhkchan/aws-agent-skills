# Baseline (no-skill) response: config-gap-stale

---

This MySQL instance is private, encrypted, Multi-AZ, and has deletion
protection on. However, automated backups are disabled
(`BackupRetentionPeriod: 0`), so there is no point-in-time recovery.
AutoMinorVersionUpgrade is also off, meaning patches will not be applied
automatically, and Enhanced Monitoring appears to be off. Consider enabling
backups and the other settings.
