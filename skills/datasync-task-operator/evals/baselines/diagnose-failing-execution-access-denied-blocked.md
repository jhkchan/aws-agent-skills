# Baseline (no-skill) response: diagnose-failing-execution-access-denied-blocked

This file captures what a generic assistant produces WITHOUT the
datasync-task-operator skill loaded.

---

The DataSync execution failed with AccessDenied on s3:PutObject.
This is an IAM permission issue. Add s3:PutObject to your task role
and retry:

```bash
aws iam attach-role-policy \
  --role-name datasync-task-role \
  --policy-arn arn:aws:iam::111111111111:policy/AmazonS3FullAccess
```

Then re-run the task:

```bash
aws datasync start-task-execution \
  --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001
```

You may also want to clean up the partial destination data first.
