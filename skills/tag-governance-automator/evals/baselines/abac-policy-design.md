# Baseline (no-skill) response: abac-policy-design

This file captures what a generic assistant produces WITHOUT the
tag-governance-automator skill loaded.

---

For ABAC, you can use aws:ResourceTag and aws:PrincipalTag condition
keys in your IAM policy. The idea is to match the resource's Team tag
with the principal's Team tag.

Your policy would look something like:

```json
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:ResourceTag/Team": "${aws:PrincipalTag/Team}"
    }
  }
}
```

You need to make sure your IAM users and roles are tagged with Team,
and your S3 buckets and EC2 instances are also tagged with Team. Then
the policy will automatically grant access based on matching tags.

You should also add a condition on CreateBucket to require the
RequestTag Team.
