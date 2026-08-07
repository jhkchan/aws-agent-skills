# Baseline (no-skill) response: create-ami-pre-migration-ready

This file captures what a generic assistant produces WITHOUT the
ec2-backup-operator skill loaded.

---

You can create an AMI from your running instance with:

```bash
aws ec2 create-image \
  --instance-id i-0prodapp123456789ab \
  --name "prod-webapp-pre-migration-2026-08-07"
```

Wait for the AMI to become available with
`aws ec2 wait image-available --image-ids <ami-id>`.
