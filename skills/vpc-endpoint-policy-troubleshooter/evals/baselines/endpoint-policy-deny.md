# Baseline (no-skill) — endpoint-policy-deny

> This is the response a model produces **without** the skill
> definition. It focuses on IAM policy troubleshooting (bucket
> policy, role permissions) but misses that the endpoint policy is
> a SEPARATE IAM layer evaluated independently. It does not identify
> that the endpoint policy on vpce-s3policy789 only allows
> s3:GetObject and s3:ListBucket, denying s3:PutObject even though
> IAM allows it. Generated for with-skill-vs-baseline comparison.

---

Check the IAM policy for the role trying to upload. Verify the S3
bucket policy allows s3:PutObject from the calling principal.

```bash
aws iam get-role-policy --role-name MyAppRole --policy-name S3Access
aws s3api get-bucket-policy --bucket my-data-bucket
```

If IAM and bucket policy both allow s3:PutObject, the issue might
be a service control policy or VPC network configuration.
