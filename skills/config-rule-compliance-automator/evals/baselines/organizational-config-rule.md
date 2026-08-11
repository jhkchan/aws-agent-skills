# Baseline (no-skill) response: organizational-config-rule

This file captures what a generic assistant produces WITHOUT the
config-rule-compliance-automator skill loaded.

---

To deploy an S3 encryption rule across your organization, you can use
organizational config rules. This automatically deploys the rule to all
member accounts.

First, make sure Config multi-account setup is enabled via Organizations.
Then deploy the org rule:

```
aws configservice put-organization-config-rule --organization-config-rule-name org-s3-encryption --organization-managed-rule-metadata '{"Identifier":"S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"}'
```

For remediation, you'd use put-organization-remediation-configuration to
set up the SSM document. The org rule should auto-propagate to all
accounts.

You might need the AWSServiceRoleForConfig role in the management
account for this to work.
