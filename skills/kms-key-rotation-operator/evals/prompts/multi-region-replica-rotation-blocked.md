# Eval prompt: multi-region-replica-rotation-blocked

Plan the following KMS key rotation enable attempt on a Multi-Region
replica key and emit the standard VERDICT block.

Operation: enable-rotation
KeyId: arn:aws:kms:us-east-1:111111111111:key/multi-replica-...
Alias: alias/prod-dr-key

```json
{
  "KeyMetadata": {
    "KeyState": "Enabled",
    "KeyUsage": "ENCRYPT_DECRYPT",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "Origin": "AWS_KMS",
    "MultiRegionConfiguration": {
      "MultiRegionKeyType": "REPLICA",
      "PrimaryKey": {
        "Arn": "arn:aws:kms:eu-west-1:111111111111:key/multi-primary-...",
        "Region": "eu-west-1"
      },
      "ReplicaKeys": [
        {"Region":"us-east-1","Arn":"arn:aws:kms:us-east-1:111111111111:key/multi-replica-..."}
      ]
    },
    "DeletionDate": null
  },
  "CurrentRotationStatus": {
    "result": "AccessDeniedException (replica — operator is in us-east-1, primary rotation is managed in eu-west-1)"
  }
}
```
