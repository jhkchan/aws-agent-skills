# Baseline (no-skill) response: create-task-nfs-to-s3-verify-ready

This file captures what a generic assistant produces WITHOUT the
datasync-task-operator skill loaded.

---

To create a DataSync task from your NFS share to S3, use:

```bash
aws datasync create-task \
  --source-location-arn arn:aws:datasync:us-east-1:111111111111:location/loc-001 \
  --destination-location-arn arn:aws:datasync:us-east-1:111111111111:location/loc-042 \
  --name nfs-to-s3-archive \
  --options '{"VerifyMode":"POINT_IN_TIME_CONSISTENT","PosixPermissions":"PRESERVE"}'
```

After creating the task, run it with:

```bash
aws datasync start-task-execution --task-arn <task-arn>
```

Both source and destination locations should already exist. Verify
with `describe-task` that the task status is AVAILABLE.
