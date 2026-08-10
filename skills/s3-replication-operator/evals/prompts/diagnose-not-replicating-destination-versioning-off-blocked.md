# Eval prompt: diagnose-not-replicating-destination-versioning-off-blocked

Diagnose the following S3 cross-region replication failure and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: diagnose-not-replicating
Source: prod-logs-source-us-east-1 (us-east-1)
Destination: prod-logs-dr-eu-west-1 (eu-west-1)

```json
{
  "SourceVersioning": {"Status": "Enabled"},
  "DestinationVersioning": {"Status": "(empty — versioning OFF)"},
  "ReplicationConfig": {
    "Role": "arn:aws:iam::111111111111:role/s3-repl-role",
    "Rules": [
      {
        "ID": "dr-crr-rtc",
        "Status": "Enabled",
        "Priority": 1,
        "Filter": {"Prefix": "logs/"},
        "Destination": {"Bucket": "arn:aws:s3:::prod-logs-dr-eu-west-1"},
        "ReplicationTime": {"Status": "Enabled", "Time": {"Minutes": 15}},
        "Metrics": {"Status": "Enabled", "EventThreshold": {"Minutes": 15}}
      }
    ]
  },
  "IamRolePermissions": "verified complete (s3:ReplicateObject, s3:ReplicateDelete, kms:Decrypt, kms:Encrypt)",
  "CloudWatchPendingReplication": {
    "Trend": "rising over last 24h, never drains below 5,000",
    "Interpretation": "objects are enqueued for replication but never delivered"
  },
  "DestinationServerAccessLogs": {
    "ReplicationOperations": 0,
    "Window": "last 24 hours"
  }
}
```
