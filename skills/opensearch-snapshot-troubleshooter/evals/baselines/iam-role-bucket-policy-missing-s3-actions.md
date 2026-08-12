# Baseline (no-skill) response: iam-role-bucket-policy-missing-s3-actions

---

Your OpenSearch snapshot is failing with a verification exception.
Since the repository registered fine, the S3 bucket probably has a
permission issue. Check that the bucket policy allows OpenSearch to
write to it — you may need to add `s3:PutObject` for the
`opensearchservice.amazonaws.com` principal.

If the policy looks right, try re-registering the repository or
deleting it and creating it again. The IAM role should also have S3
permissions in its inline policy.
