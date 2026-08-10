# Baseline (no-skill) response: add-rule-crr-kms-rtc-ready

This file captures what a generic assistant produces WITHOUT the
s3-replication-operator skill loaded.

---

To add a cross-region replication rule to your source bucket, use the
following command:

```bash
aws s3api put-bucket-replication --bucket prod-logs-source-us-east-1 \
  --replication-configuration '{
    "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Rules": [
      {
        "ID": "dr-crr-rtc",
        "Status": "Enabled",
        "Priority": 2,
        "Filter": {"Prefix": "logs/"},
        "Destination": {"Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1"},
        "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
        "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
      }
    ]
  }'
```

Make sure both buckets have versioning enabled. Verify with
`aws s3api get-bucket-versioning` on both. After applying the rule, new
objects under the `logs/` prefix will replicate to the destination.
