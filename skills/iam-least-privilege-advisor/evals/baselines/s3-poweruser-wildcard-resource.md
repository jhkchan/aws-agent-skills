# Baseline (no-skill) response: s3-poweruser-wildcard-resource

This file captures what a generic assistant produces WITHOUT the
iam-least-privilege-advisor skill loaded.

---

This policy uses `s3:*` which grants full access to all S3 operations,
including deletion and configuration changes. Combined with `Resource: "*"`,
it applies to every bucket in the account. This is broader than necessary for
most workloads.

I'd recommend scoping it down to just the actions you need. If the workload
only reads objects, you could use `s3:GetObject` instead of `s3:*`. You should
also restrict the resource to the specific bucket ARN rather than `"*"`.
