# Baseline (no-skill) response: overpermissive-ec2-role

This file captures what a generic assistant produces WITHOUT the
emr-cluster-auditor skill loaded.

---

The cluster has full encryption configured which is good. However, the EC2
instance profile role has an inline policy granting s3:* on all resources.
This is overly permissive and should be scoped down.

You should replace the wildcard S3 permissions with specific bucket-level
permissions for the buckets your EMR jobs actually need to access. For
example, grant s3:GetObject on your input bucket and s3:PutObject on your
output bucket.

The other roles appear to be using AWS managed default policies.
