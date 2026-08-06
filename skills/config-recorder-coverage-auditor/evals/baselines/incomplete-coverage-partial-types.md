# Baseline (no-skill) response: incomplete-coverage-partial-types

---

The configuration recorder is running but it's only recording three
resource types (EC2 instances, security groups, and volumes). This means
other AWS resources like IAM roles, S3 buckets, and RDS instances are
not being tracked by Config.

The delivery channel is working and there are some rules and a
conformance pack deployed.

You might want to consider enabling allSupported to record all resource
types.
