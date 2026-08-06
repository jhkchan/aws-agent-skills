# Baseline (no-skill) response: public-snapshot-block-exposure

This file captures what a generic assistant produces WITHOUT the
ebs-volume-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, block-data exposure reasoning).

---

This EBS snapshot has `CreateVolumePermissions` set to `Group: all`,
which means it is publicly accessible. Any AWS account can create a
volume from this snapshot.

You should remove the public permission unless this is intentional.
Use `aws ec2 reset-snapshot-attribute` to make it private.

The snapshot itself is encrypted which is good. Note that other accounts
cannot use it unless you also share the KMS key, so the practical exposure
may be limited.
