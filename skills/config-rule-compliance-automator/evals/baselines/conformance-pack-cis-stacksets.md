# Baseline (no-skill) response: conformance-pack-cis-stacksets

This file captures what a generic assistant produces WITHOUT the
config-rule-compliance-automator skill loaded.

---

To deploy CIS compliance across your organization, you can create a
conformance pack with all the relevant Config rules and deploy it using
CloudFormation StackSets.

The conformance pack would include rules like root-account-mfa-enabled,
iam-root-access-key-check, cloudtrail-enabled, s3-bucket-logging-enabled,
and others from the CIS benchmark.

Use StackSets to deploy to all accounts in your OU. You'll need to set
the permission model and target the OU.

```
aws cloudformation create-stack-set --stack-set-name cis-baseline ...
aws cloudformation create-stack-instances --stack-set-name cis-baseline ...
```

Make sure you include the right capabilities for IAM roles. You might
also want to enable auto-deployment so new accounts get the rules
automatically.
