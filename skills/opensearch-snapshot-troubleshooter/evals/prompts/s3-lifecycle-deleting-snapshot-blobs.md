# Eval prompt: s3-lifecycle-deleting-snapshot-blobs

Diagnose the OpenSearch snapshot restore failure. Walk the symptom-
driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: snapshots taken before 2026-07-05 fail to restore with
`SnapshotMissingException`. Recent snapshots (last 30 days) restore
fine. No IAM change, no cluster change.

```text
DomainName: prod-logs-cluster
EngineVersion: OpenSearch_2.13
Repository: manual-backups
Bucket: shared-os-backups-useast1
BucketRegion: us-east-1
Failing snapshot: snap-2026-06-15 (taken 51 days ago)
Working snapshot: snap-2026-08-01 (taken 4 days ago)

Bucket lifecycle configuration:
  {
    "Rules": [
      {
        "Id": "expire-all-30d",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Expiration": {"Days": 30}
      }
    ]
  }
Note: Filter Prefix is empty — the rule matches ALL objects in the
  bucket, including snapshot segment blobs.

_snapshot/manual-backups/snap-2026-06-15/_status response:
  "state": "SUCCESS" (the snapshot metadata is intact — the
  snap-*.dat manifest was written recently and is < 30 days old)

Restore failure:
  curl -X POST
    "$ENDPOINT/_snapshot/manual-backups/snap-2026-06-15/_restore"
  Response (500):
    {
      "error": {
        "type": "snapshot_restore_failure_exception",
        "reason": "SnapshotMissingException[snap-2026-06-15]
          snapshot does not exist"
      }
    }

s3 ls s3://shared-os-backups-useast1/manual-backups/indices/0/0/index-1
  returns NoSuchKey (the blob was expired).

CloudTrail DeleteObject events on the bucket: lifecycle actions on
  index-* objects within the last 7 days, source "s3.amazonaws.com".
```

The snapshot metadata is intact but the segment blobs are gone.
Identify the root-cause layer and recommend the lifecycle policy
fix.
