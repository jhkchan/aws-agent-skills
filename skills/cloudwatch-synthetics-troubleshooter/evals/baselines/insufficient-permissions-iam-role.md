# Baseline (no-skill) response: insufficient-permissions-iam-role

This file captures what a generic assistant produces WITHOUT the
cloudwatch-synthetics-troubleshooter skill loaded.

---

Your canary is getting an AccessDenied error on S3. This means the IAM
role doesn't have permission to read from the artifact bucket.

You should add the S3 permissions to the canary role. Try updating the
IAM policy:

```bash
aws iam put-role-policy --role-name synthetics-canary-role \
  --policy-name canary-s3-access \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::cw-synthetics-artifacts-prod","arn:aws:s3:::cw-synthetics-artifacts-prod/*"]}]}'
```

This should fix the AccessDenied error. Also check if the S3 bucket
policy is restricting access.
