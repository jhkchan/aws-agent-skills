# Eval prompt: enable-rotation-disabled-key-blocked

Plan the following KMS key rotation enable attempt and emit the
standard VERDICT block.

Operation: enable-rotation
KeyId: arn:aws:kms:us-east-1:111111111111:key/disabled123-...
Alias: alias/old-app-key

```json
{
  "KeyMetadata": {
    "KeyState": "Disabled",
    "Enabled": false,
    "KeyUsage": "ENCRYPT_DECRYPT",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "Origin": "AWS_KMS",
    "MultiRegionConfiguration": null,
    "DeletionDate": null
  },
  "CurrentRotationStatus": {
    "result": "AccessDeniedException (key disabled; non-root callers cannot fetch)"
  },
  "CallingIdentity": "Has kms:EnableKeyRotation via key policy (but key is Disabled, so all KMS state-changing operations fail except enable-key, schedule-key-deletion)"
}
```
