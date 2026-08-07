# Baseline (no-skill) response: cross-account-copy-blocked-kms

This file captures what a generic assistant produces WITHOUT the
ec2-backup-operator skill loaded.

---

To share the snapshot with account 222222222222:

```bash
aws ec2 modify-snapshot-attribute \
  --snapshot-id snap-0enc1234567890abc \
  --attribute createVolumePermission \
  --operation-type add \
  --user-ids 222222222222
```

The recipient can then copy the snapshot or create a volume from it.
