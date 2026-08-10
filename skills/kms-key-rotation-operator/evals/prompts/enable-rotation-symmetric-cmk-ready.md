# Eval prompt: enable-rotation-symmetric-cmk-ready

Plan the following KMS key rotation enable operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: enable-rotation
KeyId: arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-...
Alias: alias/prod-app-encryption-key
Rotation period: 365 days (default)

```json
{
  "KeyMetadata": {
    "KeyId": "abcd1234-5678-90ef-...",
    "Arn": "arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-...",
    "KeyState": "Enabled",
    "Enabled": true,
    "KeyUsage": "ENCRYPT_DECRYPT",
    "KeySpec": "SYMMETRIC_DEFAULT",
    "Origin": "AWS_KMS",
    "MultiRegionConfiguration": null,
    "DeletionDate": null,
    "Description": "Production application encryption key"
  },
  "CurrentRotationStatus": {
    "Enabled": false
  },
  "KeyPolicy": {
    "Statement": [
      {"Sid":"Enable rotation IAM","Effect":"Allow",
       "Principal":{"AWS":"arn:aws:iam::111111111111:role/SecurityAdmin"},
       "Action":["kms:EnableKeyRotation","kms:GetKeyRotationStatus","kms:DisableKeyRotation"],
       "Resource":"*"}
    ]
  },
  "CallingIdentity": "arn:aws:iam::111111111111:role/SecurityAdmin"
}
```
