# Baseline (no-skill) response: unencrypted-fs

This file captures what a generic assistant produces WITHOUT the
efs-filesystem-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, encryption-immutability reasoning).

---

This EFS filesystem has encryption disabled (Encrypted: false), which means
all data stored on it is plaintext at rest. You should consider enabling
encryption for security.

The filesystem has a lifecycle policy and an access point, which are good
practices. There is no filesystem policy attached, so access is governed by
IAM.

To fix the encryption issue, you should enable encryption on the filesystem.
