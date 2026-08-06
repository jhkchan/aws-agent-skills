# Baseline (no-skill) response: config-gap-impossible-lifecycle

This file captures what a generic assistant produces WITHOUT the
backup-plan-auditor skill loaded.

---

This backup plan backs up an EFS file system daily with a lifecycle that
moves to cold storage after 90 days and deletes after 30 days. The vault
has compliance-mode lock and customer-managed encryption.

Wait — the lifecycle configuration seems off. The backup is set to be
deleted after 30 days, but the cold storage transition is set for 90
days. Since deletion happens before the cold storage transition, the
backup will never actually reach cold storage.

You should fix this by making the cold storage transition happen before
the deletion, for example moving to cold at 30 days and deleting at 90.
