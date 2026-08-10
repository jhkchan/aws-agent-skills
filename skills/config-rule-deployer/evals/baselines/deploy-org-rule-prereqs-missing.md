# Baseline (no-skill) response: deploy-org-rule-prereqs-missing

This file captures what a generic assistant produces WITHOUT the
config-rule-deployer skill loaded.

---

To create an organization config rule, use:

```bash
aws configservice put-organization-config-rule \
  --organization-config-rule '{
    "OrganizationConfigRuleName": "org-s3-public-read-prohibited",
    "OrganizationManagedRuleMetadata": {
      "RuleIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED",
      "ResourceTypesScope": ["AWS::S3::Bucket"]
    }
  }'
```

You need to run this from the management account.
