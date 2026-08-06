# Eval prompt: wildcard-kms-all-no-condition

Audit the following KMS key configuration for security exposure. Emit the
standard VERDICT block (KEY, VERDICT, REASON, FINDINGS, REMEDIATION).

Key id: arn:aws:kms:us-east-1:111111111111:key/wildcard-kms-all-no-condition
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
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "kms:*",
      "Resource": "*"
    }
  ]
}
```
