# Baseline (no-skill) response: s3-public-access-auto

This file captures what a generic assistant produces WITHOUT the
auto-remediation-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, workflow template,
safety gates, audit steps, expert Config+SSM knowledge).

---

You can use AWS Config to detect the public S3 bucket and SSM to fix
it. Set up a remediation configuration on the rule pointing to an SSM
document like AWS-DisableS3BucketPublicAccess. Set it to automatic so
it fixes the bucket when Config marks it non-compliant.

You'll need an IAM role for SSM to assume. Something like
AWS-SSM-AutomationExecutionRole with the AmazonSSMAutomationRole
policy.

To configure:

```
aws configservice put-remediation-configurations --remediation-configurations ...
```

I don't remember the exact parameters offhand. You might need to look
them up in the AWS Config docs.
