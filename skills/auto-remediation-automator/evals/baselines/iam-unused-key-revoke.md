# Baseline (no-skill) response: iam-unused-key-revoke

This file captures what a generic assistant produces WITHOUT the
auto-remediation-automator skill loaded.

---

For unused IAM access keys, you can set up a Config rule and remediate
with SSM. The runbook is something like AWS-IAMRevokeUnusedAccessKey.
Set it to fire automatically.

You should be careful because if the key is actually being used by
something you don't know about, revoking it could break things.
Maybe check your CloudTrail logs first.

The remediation configuration would use
`aws configservice put-remediation-configurations`. You can find
example syntax in the AWS docs.
