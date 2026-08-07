# Eval prompt: cross-account-copy-blocked-kms

Plan the following cross-account encrypted snapshot share and emit the
standard VERDICT block.

Operation: copy-snapshot (cross-account, encrypted)
Source: snap-0enc1234567890abc (in account 111111111111, us-east-1)
Recipient: account 222222222222
KMS key: arn:aws:kms:us-east-1:111111111111:key/abc

```json
{
  "Snapshot": {
    "SnapshotId": "snap-0enc1234567890abc",
    "State": "completed",
    "Encrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/abc",
    "VolumeId": "vol-0source",
    "Description": "prod-data-pre-share"
  },
  "SnapshotAttribute": {
    "createVolumePermission": ["222222222222"]
  },
  "SourceKMSKeyPolicy": {
    "Statement": {"AllowRecipient": "MISSING"},
    "Default": "root access only"
  },
  "DestinationRegion": {
    "Name": "us-west-2",
    "OptedIn": true
  }
}
```

If pre-checks fail, surface the specific remediation that allows the
recipient to actually create-volume from the snapshot.
