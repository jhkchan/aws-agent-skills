# Baseline (no-skill) response: listbucket-arn-shape-wrong

This file captures what a generic assistant produces WITHOUT the
s3-access-troubleshooter skill loaded — the contrast that proves the
skill catches the ARN-shape trap (object ARN vs bucket ARN for
`s3:ListBucket`) that a generic assistant typically misses.

---

You're getting AccessDenied on `aws s3 ls`. Check your IAM policy and
make sure you have `s3:ListBucket` permission on the bucket.

Try adding `s3:*` on `arn:aws:s3:::internal-docs/*` to your user's
policy. If that works, narrow it down to the specific action.

Also check the bucket policy in case there's a Deny statement blocking
your user.
