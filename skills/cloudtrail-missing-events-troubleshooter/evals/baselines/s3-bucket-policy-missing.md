# Baseline (no-skill) response: s3-bucket-policy-missing

---

Your CloudTrail trail says it's logging but no new files are showing
up in S3. The bucket policy was recently updated — check that the
new policy still allows CloudTrail to write to the bucket. You may
need to add the `cloudtrail.amazonaws.com` service principal back
to the bucket policy with `s3:PutObject` permission.
