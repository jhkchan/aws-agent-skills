# Baseline (no-skill) response: kms-key-policy-decrypt-missing

---

Your application role is getting Access Denied on S3. The IAM policy
allows s3:GetObject on the bucket, so the permission should be fine.
Check if the bucket policy has any Deny statements that might block
the role.

If the bucket policy looks okay, the issue might be with the KMS key.
Since the objects are encrypted with a customer-managed key, you might
need to add some KMS permissions. Try adding kms:Decrypt to the role.
