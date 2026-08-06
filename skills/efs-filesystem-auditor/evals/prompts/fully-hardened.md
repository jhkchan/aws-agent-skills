# Eval prompt: fully-hardened

Audit the following EFS filesystem configuration for security exposure.
Emit the standard VERDICT block (FILESYSTEM, VERDICT, REASON, FINDINGS,
REMEDIATION).

Filesystem id: fs-4abc56789012 (fully-hardened)
Filesystem ARN: arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-4abc56789012
Filesystem metadata:
  Encrypted: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/jkl-345-678
  PerformanceMode: generalPurpose
  LifecyclePolicies:
    - TransitionToIA: AFTER_30_DAYS
  Access points: 2 (fsap-ddd — root directory /prod/app, fsap-eee — root directory /prod/shared)

Filesystem policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AppAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-efs-role"},
      "Action": [
        "elasticfilesystem:ClientMount",
        "elasticfilesystem:ClientWrite"
      ],
      "Resource": "*",
      "Condition": {
        "Bool": {"aws:SecureTransport": "true"}
      }
    }
  ]
}
```
