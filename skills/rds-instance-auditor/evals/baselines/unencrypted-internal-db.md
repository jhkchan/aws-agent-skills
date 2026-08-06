# Baseline (no-skill) response: unencrypted-internal-db

---

This PostgreSQL instance is not public, which is good. However,
`StorageEncrypted: false` means the data at rest is not encrypted. You should
enable encryption. The rest of the configuration looks reasonable — Multi-AZ
is on, deletion protection is on, and backups are set to 7 days.
