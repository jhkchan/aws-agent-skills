# Eval prompt: verify-rotation-enabled-completed

Verify the following KMS key rotation state and emit the standard
VERDICT block (post-verification form).

Operation: verify-rotation
KeyId: arn:aws:kms:us-east-1:111111111111:key/abcd1234-...
Alias: alias/prod-app-encryption-key

```json
{
  "KeyMetadata": {
    "KeyState": "Enabled",
    "KeyUsage": "ENCRYPT_DECRYPT",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "Origin": "AWS_KMS"
  },
  "RotationStatus": {
    "Enabled": true,
    "RotationPeriodInSeconds": 31536000,
    "NextRotationDate": "2027-02-08T00:00:00Z"
  },
  "CloudTrail": {
    "EventName": "EnableKeyRotation",
    "EventTime": "2026-08-05T14:32:11Z",
    "Username": "arn:aws:iam::111111111111:role/SecurityAdmin",
    "Resources": [{"ResourceType":"AWS::KMS::Key",
                   "ResourceName":"arn:aws:kms:us-east-1:111111111111:key/abcd1234-..."}]
  },
  "KeyPolicyDiff": "Unchanged from pre-rotation snapshot",
  "Grants": "3 grants, all Active, none Retiring",
  "ApplicationSpotCheck": {
    "encrypt": "OK (CiphertextBlob returned)",
    "decrypt": "OK (Plaintext returned)"
  }
}
```
