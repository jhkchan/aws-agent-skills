# Baseline (no-skill) response: six-key-custom-rule

This file captures what a generic assistant produces WITHOUT the
tag-compliance-automator skill loaded.

---

To enforce 6 tag keys, you can deploy the required-tags managed Config
rule with all 6 keys in the InputParameters:

```
aws configservice put-config-rule --config-rule '{
  "ConfigRuleName": "required-tags",
  "Source": {"Owner": "AWS", "SourceIdentifier": "REQUIRED_TAGS"},
  "InputParameters": "{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"CostCenter\",\"tag4Key\":\"Project\",\"tag5Key\":\"Application\",\"tag6Key\":\"ComplianceTier\"}"
}'
```

Then set up the auto-tagger Lambda and cost allocation tags as usual.
