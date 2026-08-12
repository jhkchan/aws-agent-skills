# Eval prompt: concurrent-snapshot-automated-manual-collision

Diagnose the OpenSearch snapshot failure. Walk the symptom-driven
diagnostic tree and emit the standard diagnostic block (TARGET,
VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: the nightly manual snapshot job fails immediately with
`ConcurrentSnapshotExecutionException` at exactly 03:00 UTC every
night. During other hours, manual snapshots succeed.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
AutomatedSnapshotStartHour: 3 (03:00 UTC)
Manual repository: manual-backups
Manual repository base_path: cs-automated (NOTE: same prefix as the
  automated repository)
Bucket: prod-os-snapshots-us-east-1

_snapshot/_status at the time of the manual snapshot attempt:
  {
    "snapshots": [
      {
        "repository": "cs-automated",
        "snapshot": "2026-08-05-03",
        "state": "IN_PROGRESS",
        "shards_stats": {"INIT": 0, "STARTED": 12, "FINALIZE": 0}
      }
    ]
  }

Manual snapshot attempt:
  curl -X PUT
    "$ENDPOINT/_snapshot/manual-backups/snap-manual-2026-08-05"
  Response (500):
    {
      "error": {
        "type": "concurrent_snapshot_execution_exception",
        "reason": "Cannot execute snapshot while another snapshot
          is in progress"
      }
    }

Manual snapshot succeeds when re-tried at 04:30 UTC.

Bucket policy, IAM role, repository registration: all CORRECT.
No verification issues, no lifecycle rules on the bucket.
```

The failure happens only at the automated-snapshot hour. Identify
the root-cause layer and recommend the scheduling fix.
