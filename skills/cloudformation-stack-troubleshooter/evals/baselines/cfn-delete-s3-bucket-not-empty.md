# Baseline (no-skill) response: cfn-delete-s3-bucket-not-empty

This file captures what a generic assistant produces WITHOUT the
cloudformation-stack-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT,
category-aware walk, specific remediation).

---

Your stack delete failed because the S3 bucket isn't empty. You need
to empty the bucket before CloudFormation can delete it.

Run something like:
```
aws s3 rm s3://bucket-name --recursive
```

Then retry the stack delete. If the bucket has versioning on, you
might also need to delete old versions.
