# Eval prompt: cross-account-decrypt-no-condition

Audit the following KMS key configuration for security exposure. Emit the
standard VERDICT block (KEY, VERDICT, REASON, FINDINGS, REMEDIATION).

Key id: arn:aws:kms:us-east-1:111111111111:key/cross-account-decrypt-no-condition
Key metadata:
  KeyManager: CUSTOMER
  KeySpec: SYMMETRIC_DEFAULT
  Origin: AWS_KMS
  MultiRegion: false
  KeyState: Enabled
  EnableKeyRotation: true

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
      "Sid": "ExternalDecrypt",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/external-analyzer"},
      "Action": "kms:Decrypt",
      "Resource": "*"
    }
  ]
}
```
