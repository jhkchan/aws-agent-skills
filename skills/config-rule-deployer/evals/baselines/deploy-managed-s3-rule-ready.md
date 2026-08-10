# Baseline (no-skill) response: deploy-managed-s3-rule-ready

This file captures what a generic assistant produces WITHOUT the
config-rule-deployer skill loaded.

---

To create a Config rule to detect public S3 buckets, use:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    }
  }'
```

Make sure your Config recorder is running before creating the rule.
