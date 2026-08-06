# Eval prompt: rotation-disabled-same-account-high

Audit the following KMS key configuration for security exposure. Emit the
standard VERDICT block (KEY, VERDICT, REASON, FINDINGS, REMEDIATION).

Key id: arn:aws:kms:us-east-1:111111111111:key/rotation-disabled-same-account-high
Key metadata:
  KeyManager: CUSTOMER
  KeySpec: SYMMETRIC_DEFAULT
  Origin: AWS_KMS
  MultiRegion: false
  KeyState: Enabled
  EnableKeyRotation: false

Key policy (default):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "kms:*",
      "Resource": "*"
    },
    {
      "Sid": "AppEncrypt",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-encryption-role"},
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*"
    }
  ]
}
```
