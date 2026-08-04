# Eval prompt: same-account-via-service-ok

Audit the following KMS key configuration for security exposure. Emit the
standard VERDICT block (KEY, VERDICT, REASON, FINDINGS, REMEDIATION).

Key id: arn:aws:kms:us-east-1:111111111111:key/same-account-via-service-ok
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
      "Sid": "S3ViaService",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-s3-role"},
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```
