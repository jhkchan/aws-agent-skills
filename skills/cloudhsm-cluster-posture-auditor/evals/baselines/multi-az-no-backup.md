# Baseline (no-skill) response: multi-az-no-backup

This file captures what a generic assistant produces WITHOUT the
cloudhsm-cluster-posture-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, backup-retention reasoning).

---

The cluster has 3 HSMs spread across 3 AZs which is a good HA setup.
The cluster is initialized and the CO password has been changed.

However, the backup retention policy is set to 0 days and there are no
backups listed. This means if the cluster fails you cannot recover your
keys. You should set the backup retention to a higher value like 90 days
and create a backup.

The security group looks properly scoped.
