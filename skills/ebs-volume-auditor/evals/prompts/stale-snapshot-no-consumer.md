# Eval prompt: stale-snapshot-no-consumer

Audit the following EBS snapshot configuration for security and cost
exposure. Emit the standard VERDICT block (RESOURCE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Resource type: snapshot
Resource id: snap-0ddd444stale-snapshot

Snapshot configuration (aws ec2 describe-snapshots --snapshot-ids ...):

```json
{
  "SnapshotId": "snap-0ddd444stale-snapshot",
  "OwnerId": "111111111111",
  "VolumeId": "vol-0oldvolume-deleted",
  "State": "completed",
  "StartTime": "2026-02-10T12:00:00Z",
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/abc-customer-managed"
}
```

AMI references (describe-images --filters BlockDeviceMapping.SnapshotId=...): []
Fast Snapshot Restore (describe-fast-snapshot-restores): []
Tier status (describe-snapshot-tier-status): STANDARD
Resource tags: []

Today: 2026-08-02
