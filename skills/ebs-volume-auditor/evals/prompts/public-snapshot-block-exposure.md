# Eval prompt: public-snapshot-block-exposure

Audit the following EBS snapshot configuration for security and cost
exposure. Emit the standard VERDICT block (RESOURCE, VERDICT, REASON,
FINDINGS, REMEDIATION).

Resource type: snapshot
Resource id: snap-0aaa111profile-public-exposure

Snapshot configuration (aws ec2 describe-snapshots --snapshot-ids ...):

```json
{
  "SnapshotId": "snap-0aaa111profile-public-exposure",
  "OwnerId": "111111111111",
  "VolumeId": "vol-0abcdef",
  "State": "completed",
  "StartTime": "2026-06-15T10:30:00Z",
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/abc-customer-managed"
}
```

CreateVolumePermissions (aws ec2 describe-snapshot-attribute ...):

```json
[
  {"Group": "all", "UserId": ""}
]
```
