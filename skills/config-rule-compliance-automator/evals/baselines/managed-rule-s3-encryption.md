# Baseline (no-skill) response: managed-rule-s3-encryption

This file captures what a generic assistant produces WITHOUT the
config-rule-compliance-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, managed rule selection,
StackSet deployment with CAPABILITY_IAM, remediation trigger semantics).

---

You can use the AWS-managed Config rule
s3-bucket-server-side-encryption-enabled to check that all S3 buckets
have encryption enabled. Deploy it with put-config-rule.

To remediate non-compliant buckets, you can set up SSM Automation with
the AWS-EnableS3BucketEncryption runbook. Set it to automatic so it
fixes buckets when Config marks them non-compliant.

You could also create a conformance pack for this and deploy it across
your accounts using CloudFormation StackSets.

```
aws configservice put-config-rule --config-rule '...'
```

I don't remember all the exact parameters but the general approach is
to create the managed rule, wire the SSM remediation, and deploy via
StackSets.
