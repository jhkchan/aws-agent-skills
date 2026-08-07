# Baseline (no-skill) response: insufficient-context-need-more-info

This file captures what a generic assistant produces WITHOUT the
iam-permission-troubleshooter skill loaded.

---

Your Lambda is getting AccessDenied trying to read from the bucket.
Make sure the Lambda's execution role has a policy that allows
`s3:GetObject` on `arn:aws:s3:::my-prod-bucket/*`. The bucket policy
may also need to allow the Lambda role.

If the bucket is in another account, both the Lambda role's policy AND
the bucket policy need to allow access. Also check whether the object
is encrypted with KMS — if so, the Lambda role needs `kms:Decrypt` on
the key, and the key policy needs to allow the Lambda role.

You can try adding the `AmazonS3ReadOnlyAccess` managed policy to the
Lambda role to test whether IAM is the issue.
