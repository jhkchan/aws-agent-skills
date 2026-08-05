# Baseline (no-skill) response: public-and-unencrypted

This file captures what a generic assistant produces WITHOUT the
rds-instance-auditor skill loaded — the contrast that proves the skill adds
structure (deterministic VERDICT, enumerated FINDINGS, per-dimension
reasoning, immutability-aware remediation).

---

This MySQL instance has a public IP (`PubliclyAccessible: true`) which means
it can be reached from the internet. You should turn that off unless it is
intentionally public. Encryption is also off, so the data on disk is not
encrypted. Deletion protection is off too.

To fix, you can modify the instance to remove the public IP and enable
encryption. Backups look fine at 7 days.
