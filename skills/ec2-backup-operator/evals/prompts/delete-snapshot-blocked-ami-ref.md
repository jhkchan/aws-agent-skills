# Eval prompt: delete-snapshot-blocked-ami-ref

Plan the following snapshot deletion and emit the standard VERDICT block.

Operation: delete-snapshot
Target: snap-0amibacking123

```json
{
  "Snapshot": {
    "SnapshotId": "snap-0amibacking123",
    "State": "completed",
    "VolumeId": "vol-0old",
    "Description": "AMI backing snapshot",
    "Encrypted": false
  },
  "AMIReferenceCheck": {
    "Command": "describe-images --owners self --filters BlockDeviceMapping.SnapshotId=snap-0amibacking123",
    "Result": [{"ImageId": "ami-0oldprod", "State": "available"}]
  },
  "FSRCheck": {
    "Command": "describe-fast-snapshot-restores --filters snapshot-id=snap-0amibacking123",
    "Result": "empty"
  }
}
```

If pre-checks fail, surface the specific cleanup sequence that allows
the snapshot to be safely deleted afterwards.
