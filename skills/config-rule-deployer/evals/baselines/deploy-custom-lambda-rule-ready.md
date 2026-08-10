# Baseline (no-skill) response: deploy-custom-lambda-rule-ready

This file captures what a generic assistant produces WITHOUT the
config-rule-deployer skill loaded.

---

To create a custom Lambda Config rule for tag enforcement, use:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-required-tags",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags"
    }
  }'
```

You need a Lambda function that evaluates EC2 instance tags and reports
compliance to Config.
