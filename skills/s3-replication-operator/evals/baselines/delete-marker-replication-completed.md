# Baseline (no-skill) response: delete-marker-replication-completed

This file captures what a generic assistant produces WITHOUT the
s3-replication-operator skill loaded.

---

To enable delete-marker replication, update your replication rule to
include `DeleteMarkerReplication: {Status: Enabled}`:

```bash
aws s3api put-bucket-replication --bucket prod-logs-source-us-east-1 \
  --replication-configuration '{
    "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Rules": [{
      "ID": "dr-crr-rtc",
      "Status": "Enabled",
      "Filter": {"Prefix": "logs/"},
      "Destination": {"Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1"},
      "DeleteMarkerReplication": {"Status": "Enabled"}
    }]
  }'
```

After applying, delete a test object in the source and check that the
delete marker appears in the destination.
