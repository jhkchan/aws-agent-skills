# Baseline (no-skill) response: storage-lens-gap

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-automator skill loaded.

---

Storage Lens shows 15 buckets without lifecycle policies. You can deploy
lifecycle configurations to each one using the CLI. A standard policy
would transition objects from Standard to IA after 30 days and Glacier
after 90 days.

You can loop through the bucket list and apply the same policy to each:

```bash
for bucket in logs-prod-1 logs-prod-2 backups-daily ...; do
  aws s3api put-bucket-lifecycle-configuration --bucket $bucket --lifecycle-configuration file://policy.json
done
```

This should cover all 15 buckets with the same lifecycle policy. Make
sure to use the same transition days for all buckets.
