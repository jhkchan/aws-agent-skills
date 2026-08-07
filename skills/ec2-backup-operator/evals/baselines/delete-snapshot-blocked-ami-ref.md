# Baseline (no-skill) response: delete-snapshot-blocked-ami-ref

This file captures what a generic assistant produces WITHOUT the
ec2-backup-operator skill loaded.

---

You can delete the snapshot with:

```bash
aws ec2 delete-snapshot --snapshot-id snap-0amibacking123
```

This will free up the storage cost. If you no longer need the AMI
`ami-0oldprod` either, you can deregister it separately.
