# Baseline (no-skill) response: unencrypted-volume-compliance-violation

This file captures what a generic assistant produces WITHOUT the
ebs-volume-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, encryption-immutability reasoning).

---

This EBS volume has `Encrypted: false`, which means data at rest is not
encrypted. The volume is currently attached to an EC2 instance.

You should enable encryption. This may require creating a new encrypted
volume and migrating the data.

Also note the volume type is `gp2`, which is an older generation. Consider
upgrading to `gp3` for better performance and lower cost.
