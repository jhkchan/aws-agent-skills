# Baseline (no-skill) response: getobject-arn-shape-wrong

This file captures what a generic assistant produces WITHOUT the
s3-access-troubleshooter skill loaded — the contrast that proves the
skill catches the ARN-shape trap (object ARN vs bucket ARN) that a
generic assistant misses.

---

It sounds like your Lambda doesn't have permission to read the object.
Check your Lambda role's policy and make sure it has `s3:GetObject` on
the bucket. You might also want to add a bucket policy allowing the
Lambda role.

If the bucket has KMS encryption, make sure the Lambda role has
`kms:Decrypt` on the key. KMS keys have their own policy — check the KMS
console.

Try adding `s3:*` temporarily to confirm whether IAM is the issue.
