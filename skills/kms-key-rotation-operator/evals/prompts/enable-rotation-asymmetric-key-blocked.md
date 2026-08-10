# Eval prompt: enable-rotation-asymmetric-key-blocked

Plan the following KMS key rotation enable attempt and emit the
standard VERDICT block.

Operation: enable-rotation
KeyId: arn:aws:kms:us-east-1:111111111111:key/rsa12345-...
Alias: alias/prod-signing-key

```json
{
  "KeyMetadata": {
    "KeyState": "Enabled",
    "KeyUsage": "SIGN_VERIFY",
    "KeySpec": "RSA_2048",
    "Origin": "AWS_KMS",
    "MultiRegionConfiguration": null,
    "DeletionDate": null
  },
  "CurrentRotationStatus": {
    "Enabled": false
  },
  "CallingIdentity": "Has kms:EnableKeyRotation via key policy"
}
```
